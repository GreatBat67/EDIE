import streamlit as st
from utils.queries import run_query, fmt_currency, fmt_pct, fmt_number

st.header("Executive KPI Dashboard")

# --- TOP KPIs ---
kpis = run_query("""
    SELECT
        COUNT(DISTINCT p.POLICY_ID) AS total_policies,
        ROUND(SUM(p.PREMIUM_AMOUNT), 0) AS total_premium,
        COUNT(DISTINCT cl.CLAIM_ID) AS total_claims,
        ROUND(SUM(cl.CLAIM_AMOUNT), 0) AS total_incurred,
        ROUND(SUM(cl.CLAIM_AMOUNT) / NULLIF(SUM(p.PREMIUM_AMOUNT), 0) * 100, 1) AS loss_ratio,
        ROUND(AVG(cl.RESOLUTION_DAYS), 1) AS avg_resolution_days,
        COUNT(DISTINCT c.CUSTOMER_ID) AS total_customers,
        ROUND(AVG(cl.FRAUD_SCORE), 1) AS avg_fraud_score
    FROM INSURANCE_AI_HUB.ANALYTICS.POLICIES p
    LEFT JOIN INSURANCE_AI_HUB.ANALYTICS.CLAIMS cl ON cl.POLICY_ID = p.POLICY_ID
    LEFT JOIN INSURANCE_AI_HUB.ANALYTICS.CUSTOMERS c ON c.CUSTOMER_ID = p.CUSTOMER_ID
""")
retention = run_query("""
    SELECT COUNT(*) AS at_risk, ROUND(SUM(REVENUE_AT_RISK), 0) AS rev_risk,
           ROUND(AVG(CHURN_PROBABILITY) * 100, 1) AS avg_churn
    FROM INSURANCE_AI_HUB.ANALYTICS.AT_RISK_POLICIES
""")

lr_val = kpis["LOSS_RATIO"].iloc[0] if not kpis.empty else 0
lr_status = "red" if lr_val > 70 else "orange" if lr_val > 50 else "green"

with st.container(horizontal=True):
    st.metric("Total Premium", fmt_currency(kpis["TOTAL_PREMIUM"].iloc[0]), border=True)
    st.metric("Total Incurred", fmt_currency(kpis["TOTAL_INCURRED"].iloc[0]), border=True)
    st.metric("Loss Ratio", f":{lr_status}[**{fmt_pct(lr_val)}**]", border=True)
    st.metric("Active Policies", fmt_number(kpis["TOTAL_POLICIES"].iloc[0]), border=True)
    st.metric("Customers", fmt_number(kpis["TOTAL_CUSTOMERS"].iloc[0]), border=True)

with st.container(horizontal=True):
    st.metric("Total Claims", fmt_number(kpis["TOTAL_CLAIMS"].iloc[0]), border=True)
    st.metric("Avg Resolution", f"{kpis['AVG_RESOLUTION_DAYS'].iloc[0]} days", border=True)
    st.metric("Avg Fraud Score", str(kpis["AVG_FRAUD_SCORE"].iloc[0]), border=True)
    st.metric("At-Risk Policies", fmt_number(retention["AT_RISK"].iloc[0]), border=True)
    st.metric("Revenue at Risk", fmt_currency(retention["REV_RISK"].iloc[0]), border=True)

lr_label = "critical" if lr_val > 70 else "elevated" if lr_val > 50 else "healthy"
st.caption(f"Loss ratio is {lr_label} at {lr_val}% — {fmt_currency(retention['REV_RISK'].iloc[0])} in premium revenue is at risk from {fmt_number(retention['AT_RISK'].iloc[0])} policies flagged for churn.")

# --- FORECASTS ---
st.subheader("6-Month Forecasts")

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.markdown("**Premium Revenue — Actual vs Forecast**")
        pf = run_query("""
            SELECT DATE_TRUNC('month', EFFECTIVE_DATE)::DATE AS MONTH,
                   ROUND(SUM(PREMIUM_AMOUNT), 0)::FLOAT AS ACTUAL, NULL::FLOAT AS FORECAST
            FROM INSURANCE_AI_HUB.ANALYTICS.POLICIES
            WHERE EFFECTIVE_DATE >= '2025-01-01'
            GROUP BY MONTH
            UNION ALL
            SELECT FORECAST_DATE, NULL, PREDICTED_PREMIUM
            FROM INSURANCE_AI_HUB.ANALYTICS.PREMIUM_FORECAST
            ORDER BY MONTH
        """)
        if not pf.empty:
            st.line_chart(pf, x="MONTH", y=["ACTUAL", "FORECAST"])
            fc_prem = pf[pf["FORECAST"].notna()]
            if not fc_prem.empty:
                fc_avg = fc_prem["FORECAST"].mean()
                act_avg = pf[pf["ACTUAL"].notna()]["ACTUAL"].mean()
                direction = "up" if fc_avg > act_avg else "down"
                st.caption(f"Forecast trends {direction} — avg predicted monthly premium is {fmt_currency(fc_avg)} vs historical avg {fmt_currency(act_avg)}.")

with col2:
    with st.container(border=True):
        st.markdown("**Claims Cost — Actual vs Forecast**")
        cf = run_query("""
            SELECT DATE_TRUNC('month', CLAIM_DATE)::DATE AS MONTH,
                   ROUND(SUM(CLAIM_AMOUNT), 0)::FLOAT AS ACTUAL, NULL::FLOAT AS FORECAST
            FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS
            WHERE CLAIM_DATE >= '2025-01-01'
            GROUP BY MONTH
            UNION ALL
            SELECT FORECAST_DATE, NULL, PREDICTED_COST
            FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS_COST_FORECAST
            ORDER BY MONTH
        """)
        if not cf.empty:
            st.line_chart(cf, x="MONTH", y=["ACTUAL", "FORECAST"])
            fc_cost = cf[cf["FORECAST"].notna()]
            if not fc_cost.empty:
                peak_month = fc_cost.loc[fc_cost["FORECAST"].idxmax()]
                st.caption(f"Highest predicted claims cost: {fmt_currency(peak_month['FORECAST'])} in {peak_month['MONTH']}.")

# Predicted loss ratio
with st.container(border=True):
    st.markdown("**Predicted Loss Ratio (Next 6 Months)**")
    pred_lr = run_query("""
        SELECT f.FORECAST_DATE AS MONTH,
               f.PREDICTED_PREMIUM, c.PREDICTED_COST,
               ROUND(c.PREDICTED_COST / NULLIF(f.PREDICTED_PREMIUM, 0) * 100, 1) AS PREDICTED_LOSS_RATIO,
               c.LOWER_BOUND AS COST_LOWER, c.UPPER_BOUND AS COST_UPPER
        FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS_COST_FORECAST c
        JOIN INSURANCE_AI_HUB.ANALYTICS.PREMIUM_FORECAST f ON f.FORECAST_DATE = c.FORECAST_DATE
    """)
    if not pred_lr.empty:
        st.dataframe(pred_lr, hide_index=True, use_container_width=True)
        worst = pred_lr.loc[pred_lr["PREDICTED_LOSS_RATIO"].idxmax()]
        st.caption(f"Worst predicted month: {worst['MONTH']} at {worst['PREDICTED_LOSS_RATIO']}% loss ratio — monitor for reserve adequacy.")

# --- ANOMALIES ---
anomalies = run_query("SELECT * FROM INSURANCE_AI_HUB.ANALYTICS.LOSS_RATIO_ANOMALIES ORDER BY MONTH")
if not anomalies.empty:
    anom_count = int(anomalies["IS_ANOMALY"].sum())
    if anom_count > 0:
        st.error(f"**{anom_count} loss ratio anomaly(s) detected** — actual deviated from expected pattern")
    st.dataframe(anomalies[["MONTH", "ACTUAL_LOSS_RATIO", "EXPECTED_LOSS_RATIO", "IS_ANOMALY"]],
                 hide_index=True, use_container_width=True)
    anom_rows = anomalies[anomalies["IS_ANOMALY"] == True]
    if not anom_rows.empty:
        worst_anom = anom_rows.loc[(anom_rows["ACTUAL_LOSS_RATIO"] - anom_rows["EXPECTED_LOSS_RATIO"]).abs().idxmax()]
        st.caption(f"Largest deviation: {worst_anom['MONTH']} — actual {worst_anom['ACTUAL_LOSS_RATIO']}% vs expected {worst_anom['EXPECTED_LOSS_RATIO']}%.")
    else:
        st.caption("No anomalies detected — loss ratios are tracking within expected bounds.")

# --- EXTERNAL SIGNALS ---
st.subheader("External Risk Signals")
col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.markdown("**Top 10 States by Severe Weather (2026)**")
        weather = run_query("""
            SELECT STATE, COUNT(*) AS ALERTS
            FROM INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_NWS_WEATHER_ALERTS
            WHERE EVENT_SEVERITY IN ('Severe', 'Extreme')
              AND REPORTED_DATE >= '2026-01-01'
              AND STATE IS NOT NULL
            GROUP BY STATE ORDER BY ALERTS DESC LIMIT 10
        """)
        if not weather.empty:
            st.bar_chart(weather, x="STATE", y="ALERTS", horizontal=True)
            top_state = weather.iloc[0]
            st.caption(f"{top_state['STATE']} leads with {int(top_state['ALERTS']):,} severe/extreme alerts in 2026 — review exposure in this state.")

with col2:
    with st.container(border=True):
        st.markdown("**CPI Inflation Trend (2022–Present)**")
        cpi = run_query("""
            SELECT OBSERVATION_DATE, VALUE
            FROM INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_BLS_CPI_DATA
            WHERE SERIES_NAME ILIKE '%All items, Not seasonally adjusted, Monthly%'
              AND SERIES_NAME NOT ILIKE '%less%'
              AND OBSERVATION_DATE >= '2022-01-01'
            ORDER BY OBSERVATION_DATE
        """)
        if not cpi.empty:
            st.area_chart(cpi, x="OBSERVATION_DATE", y="VALUE")
            latest_cpi = cpi.iloc[-1]["VALUE"]
            earliest_cpi = cpi.iloc[0]["VALUE"]
            pct_change = round((latest_cpi - earliest_cpi) / earliest_cpi * 100, 1)
            st.caption(f"CPI index is {latest_cpi:.1f}, up {pct_change}% since {cpi.iloc[0]['OBSERVATION_DATE']} — factor into reserve and pricing models.")

# --- LOSS RATIO BY TYPE ---
with st.container(border=True):
    st.markdown("**Loss Ratio by Policy Type**")
    lr_by_type = run_query("""
        SELECT p.POLICY_TYPE, COUNT(DISTINCT cl.CLAIM_ID) AS CLAIMS,
               ROUND(SUM(p.PREMIUM_AMOUNT), 0) AS PREMIUM,
               ROUND(SUM(cl.CLAIM_AMOUNT), 0) AS INCURRED,
               ROUND(SUM(cl.CLAIM_AMOUNT) / NULLIF(SUM(p.PREMIUM_AMOUNT), 0) * 100, 1) AS LOSS_RATIO
        FROM INSURANCE_AI_HUB.ANALYTICS.POLICIES p
        LEFT JOIN INSURANCE_AI_HUB.ANALYTICS.CLAIMS cl ON cl.POLICY_ID = p.POLICY_ID
        GROUP BY p.POLICY_TYPE ORDER BY LOSS_RATIO DESC
    """)
    if not lr_by_type.empty:
        st.dataframe(lr_by_type, hide_index=True, use_container_width=True)
        worst_type = lr_by_type.iloc[0]
        best_type = lr_by_type.iloc[-1]
        st.caption(f"{worst_type['POLICY_TYPE']} has the highest loss ratio at {worst_type['LOSS_RATIO']}%; {best_type['POLICY_TYPE']} is most profitable at {best_type['LOSS_RATIO']}%.")

st.caption("Forecasts trained by Snowflake ML. External signals from NWS, BLS, FRED (auto-refreshing). Models retrained nightly at 2 AM UTC.")

# --- ONE-CLICK EXECUTIVE BRIEF ---
st.divider()
if st.button("Generate Executive Summary", icon=":material/auto_awesome:", type="secondary"):
    with st.spinner("AI is generating your executive summary..."):
        conn = st.session_state.conn
        brief_prompt = (
            f"You are an insurance company CEO's briefing assistant. Generate a concise executive summary based on these KPIs:\n\n"
            f"- Total Premium: ${kpis['TOTAL_PREMIUM'].iloc[0]:,.0f}\n"
            f"- Total Incurred: ${kpis['TOTAL_INCURRED'].iloc[0]:,.0f}\n"
            f"- Loss Ratio: {lr_val}%\n"
            f"- Total Policies: {kpis['TOTAL_POLICIES'].iloc[0]:,}\n"
            f"- Total Claims: {kpis['TOTAL_CLAIMS'].iloc[0]:,}\n"
            f"- Avg Resolution: {kpis['AVG_RESOLUTION_DAYS'].iloc[0]} days\n"
            f"- Avg Fraud Score: {kpis['AVG_FRAUD_SCORE'].iloc[0]}\n"
            f"- At-Risk Policies: {retention['AT_RISK'].iloc[0]:,}\n"
            f"- Revenue at Risk: ${retention['REV_RISK'].iloc[0]:,.0f}\n\n"
            f"Write a 4-5 paragraph executive summary covering: (1) Financial health assessment, "
            f"(2) Claims and risk posture, (3) Customer retention outlook, (4) Key actions needed this week. "
            f"Be direct and specific with numbers. This is for a board-ready briefing."
        )
        result = conn.query(
            "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESPONSE",
            params=["claude-sonnet-4-6", brief_prompt],
        )
        with st.container(border=True):
            st.markdown("### Executive Summary")
            st.markdown(result["RESPONSE"].iloc[0])
