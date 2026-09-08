import streamlit as st
from utils.queries import run_query, safe_query, val

st.header("Research & Predict")
st.caption("Profile any table, ask AI for insights, and run on-the-fly forecasts with Snowflake ML.")

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


@st.cache_data(ttl=300)
def profile_table(schema, table):
    return run_query(
        f"SELECT COUNT(*) AS ROW_COUNT, COUNT(*) AS TOTAL FROM INSURANCE_AI_HUB.{schema}.{table}"
    )


@st.cache_data(ttl=300)
def profile_columns(schema, table, columns):
    parts = []
    for col in columns[:10]:
        parts.append(
            f'SELECT \'{col}\' AS COL, COUNT(*) AS TOTAL, '
            f'SUM(CASE WHEN "{col}" IS NULL THEN 1 ELSE 0 END) AS NULLS, '
            f'COUNT(DISTINCT "{col}") AS DISTINCT_VALS '
            f'FROM INSURANCE_AI_HUB.{schema}.{table}'
        )
    sql = " UNION ALL ".join(parts)
    return run_query(sql)


tab1, tab2, tab3 = st.tabs(["Data Profile", "AI Research", "Predict & Forecast"])

# ============================================================
# TAB 1: DATA PROFILE
# ============================================================
with tab1:
    st.subheader("Table Profiler")

    col1, col2 = st.columns(2)
    with col1:
        schema = st.selectbox("Schema", list(ALLOWED_TABLES.keys()), key="prof_schema")
    with col2:
        table = st.selectbox("Table", ALLOWED_TABLES.get(schema, []), key="prof_table")

    if schema and table:
        col_df = get_columns(schema, table)
        all_cols = col_df["COLUMN_NAME"].tolist()
        col_types = dict(zip(col_df["COLUMN_NAME"], col_df["DATA_TYPE"]))

        with st.container(border=True):
            st.markdown(f"**{schema}.{table}** — {len(all_cols)} columns")
            st.dataframe(col_df, hide_index=True, use_container_width=True)

        if st.button("Run Column Profile", icon=":material/query_stats:"):
            with st.spinner("Profiling columns..."):
                prof = profile_columns(schema, table, all_cols)
            st.dataframe(prof, hide_index=True, use_container_width=True)

        with st.container(border=True):
            st.markdown("**Sample Data (first 50 rows)**")
            sample = run_query(f"SELECT * FROM INSURANCE_AI_HUB.{schema}.{table} LIMIT 50")
            st.dataframe(sample, hide_index=True, use_container_width=True)

# ============================================================
# TAB 2: AI RESEARCH
# ============================================================
with tab2:
    st.subheader("AI-Powered Research")
    st.caption("Ask a question about any table — the AI gets the data context and generates insights.")

    col1, col2 = st.columns(2)
    with col1:
        r_schema = st.selectbox("Schema", list(ALLOWED_TABLES.keys()), key="res_schema")
    with col2:
        r_table = st.selectbox("Table", ALLOWED_TABLES.get(r_schema, []), key="res_table")

    research_q = st.text_area(
        "Research question",
        placeholder="e.g., What patterns exist in claim amounts by policy type? Are there any outliers?",
        height=80,
    )

    if st.button("Run Research", type="primary", icon=":material/science:") and research_q:
        with st.spinner("Analyzing data..."):
            sample_data = run_query(f"SELECT * FROM INSURANCE_AI_HUB.{r_schema}.{r_table} LIMIT 200")
            data_summary = sample_data.describe(include="all").to_string()
            col_info = get_columns(r_schema, r_table).to_string(index=False)

            conn = st.session_state.conn
            prompt = (
                f"You are a senior insurance data analyst. The user is researching the table {r_schema}.{r_table}.\n\n"
                f"Columns:\n{col_info}\n\n"
                f"Data summary statistics:\n{data_summary}\n\n"
                f"Sample data (first few rows):\n{sample_data.head(10).to_string(index=False)}\n\n"
                f"User's question: {research_q}\n\n"
                f"Provide a thorough analysis with: (1) Direct answer to the question, "
                f"(2) Key patterns or anomalies found, (3) Actionable recommendations for an insurance professional. "
                f"Use specific numbers from the data."
            )
            result = conn.query(
                "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESPONSE",
                params=["claude-sonnet-4-6", prompt],
            )
            st.markdown(result["RESPONSE"].iloc[0])

        with st.expander("View raw data sample"):
            st.dataframe(sample_data.head(50), hide_index=True, use_container_width=True)

# ============================================================
# TAB 3: PREDICT & FORECAST
# ============================================================
with tab3:
    st.subheader("On-the-Fly Forecasting")
    st.caption("Pick a time series from any table and generate predictions using Snowflake ML.")

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
                            f'CREATE OR REPLACE TEMPORARY TABLE {ts_view} AS '
                            f'SELECT DATE_TRUNC(\'month\', "{ts_col}")::TIMESTAMP_NTZ AS DS, '
                            f'{agg_method}("{target_col}")::FLOAT AS Y '
                            f'FROM {fqn} WHERE "{ts_col}" IS NOT NULL AND "{target_col}" IS NOT NULL '
                            f'GROUP BY DS ORDER BY DS'
                        ).collect()

                        session.sql(
                            f'CREATE OR REPLACE SNOWFLAKE.ML.FORECAST {model_name}('
                            f'INPUT_DATA => TABLE({ts_view}), '
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

                        import pandas as pd
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
                                st.info(interp["R"].iloc[0])

                    except Exception as e:
                        st.error(f"Forecast error: {str(e)}")

    # --- WHAT-IF SCENARIOS ---
    st.divider()
    st.subheader("What-If Scenario Analysis")
    st.caption("Adjust assumptions — including external macro factors from Marketplace data — and see real-time impact on key metrics.")

    st.markdown("##### Internal Levers")
    col1, col2, col3 = st.columns(3)
    with col1:
        claims_change = st.slider("Claims volume change (%)", -30, 50, 0, step=5)
    with col2:
        premium_change = st.slider("Premium rate change (%)", -20, 30, 0, step=5)
    with col3:
        churn_change = st.slider("Churn rate change (%)", -20, 30, 0, step=5)

    st.markdown("##### External / Macro Factors (from Marketplace Data)")
    col4, col5, col6 = st.columns(3)
    with col4:
        inflation = st.slider("CPI inflation (%)", 0.0, 10.0, 3.0, step=0.5)
    with col5:
        cat_multiplier = st.slider("Catastrophe severity (1x = normal)", 0.5, 3.0, 1.0, step=0.25)
    with col6:
        interest_rate = st.slider("Interest rate (%)", 0.0, 8.0, 5.0, step=0.25)

    if st.button("Run What-If", icon=":material/calculate:"):
        with st.spinner("Calculating scenario..."):
            baseline = run_query("""
                SELECT ROUND(SUM(p.PREMIUM_AMOUNT), 0) AS TOTAL_PREMIUM,
                       ROUND(SUM(cl.CLAIM_AMOUNT), 0) AS TOTAL_INCURRED,
                       COUNT(DISTINCT cl.CLAIM_ID) AS TOTAL_CLAIMS,
                       ROUND(SUM(cl.CLAIM_AMOUNT) / NULLIF(SUM(p.PREMIUM_AMOUNT), 0) * 100, 1) AS LOSS_RATIO
                FROM INSURANCE_AI_HUB.ANALYTICS.POLICIES p
                LEFT JOIN INSURANCE_AI_HUB.ANALYTICS.CLAIMS cl ON cl.POLICY_ID = p.POLICY_ID
            """)

            base_prem = float(baseline["TOTAL_PREMIUM"].iloc[0])
            base_inc = float(baseline["TOTAL_INCURRED"].iloc[0])
            base_claims = int(baseline["TOTAL_CLAIMS"].iloc[0])
            base_lr = float(baseline["LOSS_RATIO"].iloc[0])

            adj_prem = base_prem * (1 + premium_change / 100) * (1 - churn_change / 100)
            adj_inc = base_inc * (1 + claims_change / 100) * (1 + inflation / 100) * cat_multiplier
            adj_claims = int(base_claims * (1 + claims_change / 100) * cat_multiplier)
            adj_lr = round(adj_inc / max(adj_prem, 1) * 100, 1)
            investment_income = base_prem * (interest_rate / 100) * 0.3  # ~30% of premium invested

            col1, col2, col3 = st.columns(3)
            with col1:
                with st.container(border=True):
                    st.markdown("**Baseline (Current)**")
                    st.metric("Premium", f"${base_prem:,.0f}")
                    st.metric("Incurred", f"${base_inc:,.0f}")
                    st.metric("Claims", f"{base_claims:,}")
                    st.metric("Loss Ratio", f"{base_lr}%")

            with col2:
                lr_delta = adj_lr - base_lr
                with st.container(border=True):
                    st.markdown("**Adjusted Scenario**")
                    st.metric("Premium", f"${adj_prem:,.0f}", f"{premium_change - churn_change:+.0f}%")
                    st.metric("Incurred", f"${adj_inc:,.0f}", f"x{cat_multiplier}")
                    st.metric("Claims", f"{adj_claims:,}", f"{claims_change:+d}%")
                    st.metric("Loss Ratio", f"{adj_lr}%", f"{lr_delta:+.1f}pp")

            with col3:
                combined_ratio = adj_lr + 30  # ~30% expense ratio
                with st.container(border=True):
                    st.markdown("**Financial Impact**")
                    st.metric("Est. Investment Income", f"${investment_income:,.0f}")
                    st.metric("Combined Ratio", f"{combined_ratio:.1f}%")
                    st.metric("Underwriting Result", f"${adj_prem - adj_inc:,.0f}")
                    profit = adj_prem - adj_inc + investment_income
                    st.metric("Net Result", f"${profit:,.0f}")

            conn = st.session_state.conn
            whatif_prompt = (
                f"You are an insurance CFO advisor. Analyze this scenario:\n\n"
                f"Baseline: Premium=${base_prem:,.0f}, Incurred=${base_inc:,.0f}, Loss Ratio={base_lr}%\n"
                f"Scenario: claims {claims_change:+d}%, premium {premium_change:+d}%, churn {churn_change:+d}%, "
                f"inflation {inflation}%, catastrophe multiplier {cat_multiplier}x, interest rate {interest_rate}%\n"
                f"Adjusted: Premium=${adj_prem:,.0f}, Incurred=${adj_inc:,.0f}, Loss Ratio={adj_lr}%, "
                f"Combined Ratio={combined_ratio:.1f}%, Investment Income=${investment_income:,.0f}, "
                f"Net Result=${profit:,.0f}\n\n"
                f"Provide: (1) Is this sustainable? (2) Reserve impact, (3) Impact of the catastrophe and macro assumptions, "
                f"(4) Two specific actions. Be concise and use the numbers."
            )
            whatif_result = conn.query(
                "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS R",
                params=["claude-sonnet-4-6", whatif_prompt],
            )
            with st.container(border=True):
                st.markdown("**AI Scenario Assessment**")
                st.info(whatif_result["R"].iloc[0])
