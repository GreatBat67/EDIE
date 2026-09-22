import streamlit as st
from utils.queries import safe_query, val, fmt_currency, fmt_number

st.markdown("""
<div class="edie-hero-banner">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h2 style="margin: 0; color: #FFFFFF; font-weight: 700;">Claims Forecasting & Intelligence</h2>
            <p style="margin: 4px 0 0 0; color: #94A3B8; font-size: 0.95rem;">Severity Surges, Fraud Scoring, FNOL Bottlenecks & Weather Impact</p>
        </div>
        <div style="text-align: right; background: rgba(16, 185, 129, 0.15); border: 1px solid #10B981; padding: 6px 14px; border-radius: 8px;">
            <span style="font-size: 0.8rem; color: #10B981; font-weight: 600;">ACTIVE CLAIMS OPS</span>
            <div style="font-size: 1.1rem; font-weight: 700; color: #F8FAFC;">Active Claims Operations</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

cl_totals, err = safe_query("""
    SELECT COUNT(*) AS total_claims, ROUND(SUM(CLAIM_AMOUNT), 0) AS total_claimed,
           ROUND(AVG(FRAUD_SCORE), 1) AS avg_fraud, ROUND(AVG(RESOLUTION_DAYS), 1) AS avg_resolution
    FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS
""")
if err:
    st.error(f"Failed to load claims data: {err}")
    st.stop()

_fraud_score = float(val(cl_totals, 'AVG_FRAUD', 0))
_fraud_label = "Critical" if _fraud_score > 60 else "Elevated" if _fraud_score > 40 else "Normal"
_resolution = float(val(cl_totals, 'AVG_RESOLUTION', 0))

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Claims Processed", fmt_number(val(cl_totals, "TOTAL_CLAIMS")))
col2.metric("Total Incurred Losses", fmt_currency(val(cl_totals, "TOTAL_CLAIMED")), delta_color="inverse")
col3.metric("Avg Fraud Score", f"{_fraud_score} / 100", delta=_fraud_label, delta_color="normal" if _fraud_label == "Normal" else "inverse")
col4.metric("Avg Resolution Cycle", f"{_resolution} days")

avg_claim = val(cl_totals, "TOTAL_CLAIMED") / max(val(cl_totals, "TOTAL_CLAIMS"), 1)
st.caption(f"Average claim size is {fmt_currency(avg_claim)} with {val(cl_totals, 'AVG_RESOLUTION', 0)}-day avg resolution — fraud scores average {val(cl_totals, 'AVG_FRAUD', 0)}/100.")

# --- CLAIMS VOLUME FORECAST ---
st.subheader("Claims Volume Forecast (6 Months)")
import altair as alt

forecast, _ = safe_query("""
    WITH historical AS (
        SELECT p.POLICY_TYPE, DATE_TRUNC('month', cl.CLAIM_DATE)::DATE AS MONTH,
               COUNT(*) AS CLAIM_COUNT, 'Historical' AS TYPE
        FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS cl
        JOIN INSURANCE_AI_HUB.ANALYTICS.POLICIES p ON p.POLICY_ID = cl.POLICY_ID
        GROUP BY p.POLICY_TYPE, MONTH
    ),
    predicted AS (
        SELECT POLICY_TYPE, FORECAST_DATE AS MONTH, PREDICTED_CLAIMS AS CLAIM_COUNT, 'Forecast' AS TYPE
        FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS_FORECAST
    )
    SELECT * FROM historical UNION ALL SELECT * FROM predicted
    ORDER BY POLICY_TYPE, MONTH
""")

if not forecast.empty:
    selected_type = st.selectbox("Policy Type", sorted(forecast["POLICY_TYPE"].unique()))
    filtered = forecast[forecast["POLICY_TYPE"] == selected_type]
    
    chart_vol = (
        alt.Chart(filtered)
        .mark_line(point=True)
        .encode(
            x=alt.X("MONTH:T", title="Month"),
            y=alt.Y("CLAIM_COUNT:Q", scale=alt.Scale(zero=False), title="Claims Count"),
            color=alt.Color("TYPE:N", scale=alt.Scale(domain=["Historical", "Forecast"], range=["#10B981", "#F59E0B"])),
            tooltip=["MONTH:T", "TYPE:N", "CLAIM_COUNT:Q"]
        )
        .properties(height=280)
    )
    st.altair_chart(chart_vol, use_container_width=True)

    fc_only = filtered[filtered["TYPE"] == "Forecast"]
    hist_only = filtered[filtered["TYPE"] == "Historical"]
    if not fc_only.empty and not hist_only.empty:
        fc_avg = fc_only["CLAIM_COUNT"].mean()
        hist_avg = hist_only["CLAIM_COUNT"].tail(6).mean()
        pct = round((fc_avg - hist_avg) / max(hist_avg, 1) * 100, 1)
        direction = "increase" if pct > 0 else "decrease"
        st.caption(f"{selected_type}: forecast shows {abs(pct)}% {direction} in avg monthly claims vs last 6 months.")

    with st.container(border=True):
        st.markdown("**Forecast Details with Confidence Intervals**")
        fc_detail, _ = safe_query("SELECT * FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS_FORECAST ORDER BY POLICY_TYPE, FORECAST_DATE")
        if not fc_detail.empty:
            st.dataframe(fc_detail, hide_index=True, use_container_width=True)
            widest = fc_detail.copy()
            widest["CI_WIDTH"] = widest["UPPER_BOUND"] - widest["LOWER_BOUND"]
            widest_row = widest.loc[widest["CI_WIDTH"].idxmax()]
            st.caption(f"Widest confidence interval: {widest_row['POLICY_TYPE']} in {widest_row['FORECAST_DATE']} (range: {widest_row['LOWER_BOUND']:.0f}–{widest_row['UPPER_BOUND']:.0f}).")
else:
    st.info("No claims forecast data available.")

# --- CLAIMS COST FORECAST ---
st.subheader("Claims Cost Forecast")
cost_fc, _ = safe_query("""
    SELECT 'Historical' AS TYPE, DATE_TRUNC('month', CLAIM_DATE)::DATE AS MONTH,
           ROUND(SUM(CLAIM_AMOUNT), 0)::FLOAT AS COST
    FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS GROUP BY MONTH
    UNION ALL
    SELECT 'Forecast', FORECAST_DATE, PREDICTED_COST
    FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS_COST_FORECAST
    ORDER BY MONTH
""")
if not cost_fc.empty:
    chart_cost = (
        alt.Chart(cost_fc)
        .mark_line(point=True)
        .encode(
            x=alt.X("MONTH:T", title="Month"),
            y=alt.Y("COST:Q", scale=alt.Scale(zero=False), title="Incurred Claims Amount ($)"),
            color=alt.Color("TYPE:N", scale=alt.Scale(domain=["Historical", "Forecast"], range=["#10B981", "#F59E0B"])),
            tooltip=["MONTH:T", "TYPE:N", alt.Tooltip("COST:Q", format="$,.0f")]
        )
        .properties(height=300)
    )
    st.altair_chart(chart_cost, use_container_width=True)
    fc_costs = cost_fc[cost_fc["TYPE"] == "Forecast"]
    if not fc_costs.empty:
        total_fc = fc_costs["COST"].sum()
        st.caption(f"Total forecasted claims cost over next 6 months: {fmt_currency(total_fc)} — budget reserves accordingly.")

# --- WEATHER CORRELATION ---
st.subheader("Weather-Correlated Claims Risk")
weather_claims, _ = safe_query("""
    WITH state_claims AS (
        SELECT c.STATE, COUNT(*) AS CLAIMS, ROUND(SUM(cl.CLAIM_AMOUNT), 0) AS TOTAL_CLAIMED
        FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMERS c
        JOIN INSURANCE_AI_HUB.ANALYTICS.CLAIMS cl ON cl.CUSTOMER_ID = c.CUSTOMER_ID
        GROUP BY c.STATE
    ),
    state_weather AS (
        SELECT STATE, COUNT(*) AS SEVERE_ALERTS
        FROM INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_NWS_WEATHER_ALERTS
        WHERE EVENT_SEVERITY IN ('Severe', 'Extreme') AND REPORTED_DATE >= DATEADD('year', -1, CURRENT_DATE())
        GROUP BY STATE
    )
    SELECT sc.STATE, sc.CLAIMS, sc.TOTAL_CLAIMED, COALESCE(sw.SEVERE_ALERTS, 0) AS SEVERE_WEATHER_ALERTS,
           CASE WHEN COALESCE(sw.SEVERE_ALERTS, 0) > 5000 AND sc.CLAIMS > 100 THEN 'HIGH RISK'
                WHEN COALESCE(sw.SEVERE_ALERTS, 0) > 1000 THEN 'ELEVATED' ELSE 'NORMAL' END AS RISK_LEVEL
    FROM state_claims sc
    LEFT JOIN state_weather sw ON sw.STATE = sc.STATE
    ORDER BY SEVERE_WEATHER_ALERTS DESC LIMIT 15
""")
if not weather_claims.empty:
    st.dataframe(weather_claims, hide_index=True, use_container_width=True)
    high_risk = weather_claims[weather_claims["RISK_LEVEL"] == "HIGH RISK"]
    if not high_risk.empty:
        total_exposed = high_risk["TOTAL_CLAIMED"].sum()
        st.caption(f"{len(high_risk)} state(s) at HIGH RISK with {fmt_currency(total_exposed)} in total claims exposure.")
    else:
        st.caption("No states currently at HIGH RISK — weather-to-claims correlation is manageable.")

# --- FRAUD ANALYSIS ---
st.subheader("Fraud Analysis")
col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.markdown("**Fraud Score Distribution**")
        fraud, _ = safe_query("""
            SELECT CASE WHEN FRAUD_SCORE < 20 THEN '0-20 Low' WHEN FRAUD_SCORE < 40 THEN '20-40 Normal'
                        WHEN FRAUD_SCORE < 60 THEN '40-60 Elevated' WHEN FRAUD_SCORE < 80 THEN '60-80 High'
                        ELSE '80-100 Critical' END AS FRAUD_BAND, COUNT(*) AS CNT
            FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS GROUP BY FRAUD_BAND ORDER BY FRAUD_BAND
        """)
        if not fraud.empty:
            st.bar_chart(fraud, x="FRAUD_BAND", y="CNT")
            critical = fraud[fraud["FRAUD_BAND"] == "80-100 Critical"]
            critical_cnt = int(critical["CNT"].iloc[0]) if not critical.empty else 0
            total_cnt = int(fraud["CNT"].sum())
            st.caption(f"{critical_cnt} claims ({round(critical_cnt/max(total_cnt,1)*100,1)}%) in critical fraud band — these need SIU review.")

with col2:
    with st.container(border=True):
        st.markdown("**Friction Reasons**")
        friction, _ = safe_query("""
            SELECT FRICTION_REASON, COUNT(*) AS CNT FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS
            WHERE FRICTION_REASON IS NOT NULL GROUP BY FRICTION_REASON ORDER BY CNT DESC
        """)
        if not friction.empty:
            st.bar_chart(friction, x="FRICTION_REASON", y="CNT")
            top_friction = friction.iloc[0]
            st.caption(f"Top friction reason: \"{top_friction['FRICTION_REASON']}\" ({int(top_friction['CNT'])} claims) — address to improve resolution time.")

with st.container(border=True):
    st.caption("**Assumptions:** Claims forecast is based on monthly claim counts per policy type (Jan 2024 — Aug 2026). "
               "Confidence intervals reflect model uncertainty. Weather correlation is observational, not causal.")
