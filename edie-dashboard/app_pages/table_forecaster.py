import streamlit as st
import pandas as pd
from utils.queries import run_query

st.markdown("""
<div class="edie-hero-banner">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h2 style="margin: 0; color: #FFFFFF; font-weight: 700;">Table Forecaster</h2>
            <p style="margin: 4px 0 0 0; color: #94A3B8; font-size: 0.95rem;">Pick any time series and generate predictions with Snowflake ML</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

ALLOWED_TABLES = {
    "ANALYTICS": [
        "AGENTS", "APPLICATIONS", "AT_RISK_POLICIES", "BILLING", "CLAIMS",
        "CLAIM_ACTIVITY_LOG", "CUSTOMERS", "CUSTOMER_ATTRIBUTE_HISTORY",
        "CUSTOMER_SURVEYS", "FINANCIAL_LEDGER", "POLICIES", "POLICY_CHANGE_LOG",
        "PROPERTY_CHARACTERISTICS", "REINSURANCE_RECOVERIES", "REINSURANCE_TREATIES",
        "VEHICLE_DETAILS",
    ],
    "EXTERNAL_DATA": [
        "LIVE_NWS_WEATHER_ALERTS", "LIVE_FEMA_DISASTER_DECLARATIONS",
        "LIVE_FEMA_FLOOD_CLAIMS", "LIVE_BLS_CPI_DATA", "LIVE_FRED_ECONOMIC_DATA",
        "LIVE_HOSPITAL_PRICE_TRANSPARENCY", "NAIC_STATUTORY_GUIDELINES",
    ],
}


@st.cache_data(ttl=600)
def get_columns(schema, table):
    return run_query(
        f"SELECT COLUMN_NAME, DATA_TYPE FROM INSURANCE_AI_HUB.INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}' ORDER BY ORDINAL_POSITION"
    )


col1, col2 = st.columns(2)
with col1:
    f_schema = st.selectbox("Schema", list(ALLOWED_TABLES.keys()), key="fc_schema")
with col2:
    f_table = st.selectbox("Table", ALLOWED_TABLES.get(f_schema, []), key="fc_table")

if f_schema and f_table:
    fc_col_df = get_columns(f_schema, f_table)
    fc_cols = fc_col_df["COLUMN_NAME"].tolist()
    fc_types = dict(zip(fc_col_df["COLUMN_NAME"], fc_col_df["DATA_TYPE"]))

    date_cols = [c for c in fc_cols if "DATE" in fc_types.get(c, "") or "TIMESTAMP" in fc_types.get(c, "")]
    num_cols = [c for c in fc_cols if fc_types.get(c, "") in ("NUMBER", "FLOAT", "DECIMAL")]

    if not date_cols:
        st.warning("This table has no date/timestamp columns. Select a table with time-series data.")
    elif not num_cols:
        st.warning("This table has no numeric columns to forecast.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            ts_col = st.selectbox("Time Column", date_cols)
        with col2:
            target_col = st.selectbox("Value to Forecast", num_cols)
        with col3:
            periods = st.slider("Forecast Periods", 3, 12, 6)

        agg_method = st.selectbox("Aggregation", ["SUM", "AVG", "COUNT"])

        if st.button("Generate Forecast", type="primary", icon=":material/trending_up:"):
            fqn = f"INSURANCE_AI_HUB.{f_schema}.{f_table}"
            model_name = f"INSURANCE_AI_HUB.ANALYTICS._USER_FORECAST_{f_table}_{target_col}"
            ts_view = f"INSURANCE_AI_HUB.ANALYTICS._USER_FC_VIEW"

            with st.spinner("Training forecast model (this may take 30-60 seconds)..."):
                try:
                    conn = st.session_state.conn
                    session = conn.session()

                    session.sql(
                        f'CREATE OR REPLACE TABLE {ts_view} AS '
                        f'SELECT DATE_TRUNC(\'month\', "{ts_col}")::TIMESTAMP_NTZ AS DS, '
                        f'{agg_method}("{target_col}")::FLOAT AS Y '
                        f'FROM {fqn} WHERE "{ts_col}" IS NOT NULL AND "{target_col}" IS NOT NULL '
                        f'GROUP BY DS ORDER BY DS'
                    ).collect()

                    session.sql(
                        f'CREATE OR REPLACE SNOWFLAKE.ML.FORECAST {model_name}('
                        f'INPUT_DATA => SYSTEM$REFERENCE(\'TABLE\', \'{ts_view}\'), '
                        f'TIMESTAMP_COLNAME => \'DS\', '
                        f'TARGET_COLNAME => \'Y\')'
                    ).collect()

                    forecast_df = run_query(
                        f'SELECT * FROM TABLE({model_name}!FORECAST(FORECASTING_PERIODS => {int(periods)}))'
                    )

                    historical = run_query(
                        f'SELECT DS::DATE AS MONTH, Y AS VALUE, \'Historical\' AS TYPE FROM {ts_view}'
                    )

                    pred = forecast_df.copy()
                    pred["MONTH"] = pred["TS"].apply(lambda x: str(x)[:10])
                    pred["VALUE"] = pred["FORECAST"]
                    pred["TYPE"] = "Forecast"

                    st.success(f"Forecast generated for {target_col} ({agg_method}) — {periods} months ahead")

                    st.markdown(f"**{agg_method}({target_col}) — Historical + Forecast**")

                    historical["MONTH"] = pd.to_datetime(historical["MONTH"])
                    pred["MONTH"] = pd.to_datetime(pred["MONTH"])
                    chart_data = pd.concat([
                        historical[["MONTH", "VALUE", "TYPE"]],
                        pred[["MONTH", "VALUE", "TYPE"]]
                    ])
                    st.line_chart(chart_data, x="MONTH", y="VALUE", color="TYPE")

                    with st.container(border=True):
                        st.markdown("**Forecast Details (with confidence intervals)**")
                        display_fc = forecast_df[["TS", "FORECAST", "LOWER_BOUND", "UPPER_BOUND"]].copy()
                        display_fc.columns = ["Date", "Predicted", "Lower Bound", "Upper Bound"]
                        st.dataframe(display_fc, hide_index=True, use_container_width=True)

                    with st.spinner("Generating AI interpretation..."):
                        fc_summary = display_fc.to_string(index=False)
                        hist_summary = historical.describe().to_string()
                        interp_prompt = (
                            f"You are an insurance forecasting analyst. A user just ran a forecast on "
                            f"{f_schema}.{f_table}, column {target_col} ({agg_method} monthly).\n\n"
                            f"Historical stats:\n{hist_summary}\n\n"
                            f"Forecast:\n{fc_summary}\n\n"
                            f"Give: (1) The trend direction and magnitude, (2) Business implications for an insurer, "
                            f"(3) What assumptions this forecast relies on, (4) One recommended action. Be concise."
                        )
                        interp = conn.query(
                            "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS R",
                            params=["claude-sonnet-4-6", interp_prompt],
                        )
                        with st.container(border=True):
                            st.markdown("**AI Interpretation**")
                            st.info(interp["R"].iloc[0].replace("$", "\\$"))

                except Exception as e:
                    st.error(f"Forecast error: {str(e)}")
                finally:
                    try:
                        session.sql(f'DROP TABLE IF EXISTS {ts_view}').collect()
                    except Exception:
                        pass
