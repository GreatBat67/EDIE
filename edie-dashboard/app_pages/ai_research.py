import streamlit as st
from utils.queries import run_query

st.markdown("""
<div class="edie-hero-banner">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h2 style="margin: 0; color: #FFFFFF; font-weight: 700;">AI Research & Data Profiler</h2>
            <p style="margin: 4px 0 0 0; color: #94A3B8; font-size: 0.95rem;">Profile any table, explore schema quality, and ask AI for data-driven insights</p>
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


tab1, tab2 = st.tabs(["Data Profiler", "AI Research"])

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
            st.download_button(
                "Download CSV",
                data=sample.to_csv(index=False),
                file_name=f"{schema}_{table}_sample.csv",
                mime="text/csv",
                icon=":material/download:",
            )

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
            st.markdown(result["RESPONSE"].iloc[0].replace("$", "\\$"))

        with st.expander("View raw data sample"):
            st.dataframe(sample_data.head(50), hide_index=True, use_container_width=True)
