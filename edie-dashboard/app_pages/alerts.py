import streamlit as st
from utils.queries import run_query, safe_query, val, fmt_number

st.header("Alerts & Monitoring")
st.caption("Threshold alerts + forecast-based early warnings")

# --- PREDICTIVE ALERTS ---
st.subheader("Forecast-Based Alerts")

claims_fc = run_query("""
    SELECT POLICY_TYPE, FORECAST_DATE, PREDICTED_CLAIMS, UPPER_BOUND
    FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS_FORECAST ORDER BY FORECAST_DATE LIMIT 10
""")
cost_fc = run_query("SELECT * FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS_COST_FORECAST ORDER BY FORECAST_DATE LIMIT 3")
prem_fc = run_query("SELECT * FROM INSURANCE_AI_HUB.ANALYTICS.PREMIUM_FORECAST ORDER BY FORECAST_DATE LIMIT 3")
anomalies = run_query("SELECT * FROM INSURANCE_AI_HUB.ANALYTICS.LOSS_RATIO_ANOMALIES WHERE IS_ANOMALY = TRUE")

col1, col2, col3 = st.columns(3)
with col1:
    with st.container(border=True):
        if not cost_fc.empty:
            next_cost = cost_fc["PREDICTED_COST"].iloc[0]
            next_prem = prem_fc["PREDICTED_PREMIUM"].iloc[0] if not prem_fc.empty else 0
            pred_lr = round(next_cost / max(next_prem, 1) * 100, 1)
            if pred_lr > 70:
                st.error(f"**Predicted Loss Ratio: {pred_lr}%** — next month exceeds 70% threshold")
                st.caption(f"Predicted cost {next_cost:,.0f} vs premium {next_prem:,.0f} — consider rate action or reserve increase.")
            elif pred_lr > 50:
                st.warning(f"**Predicted Loss Ratio: {pred_lr}%** — elevated but within range")
                st.caption("Monitor closely — if claims spike, this could breach the 70% threshold.")
            else:
                st.success(f"**Predicted Loss Ratio: {pred_lr}%** — healthy")
                st.caption("Loss ratio is well-controlled — continue current underwriting posture.")

with col2:
    with st.container(border=True):
        if not anomalies.empty:
            st.error(f"**{len(anomalies)} Loss Ratio Anomaly(s)** detected by ML model")
            latest_anom = anomalies.iloc[-1]
            st.caption(f"Most recent: {latest_anom['MONTH']} — actual {latest_anom['ACTUAL_LOSS_RATIO']}% vs expected {latest_anom['EXPECTED_LOSS_RATIO']}%.")
        else:
            st.success("No loss ratio anomalies detected")
            st.caption("All months within expected statistical bounds.")

with col3:
    with st.container(border=True):
        underpriced = run_query("""
            SELECT COUNT(*) AS CNT FROM INSURANCE_AI_HUB.ANALYTICS.PRICING_RECOMMENDATIONS
            WHERE PRICING_STATUS = 'UNDERPRICED'
        """)
        cnt = int(underpriced["CNT"].iloc[0])
        if cnt > 0:
            st.warning(f"**{cnt} state/type combos** flagged as UNDERPRICED")
            st.caption("Visit Pricing & Risk page for specific rate adjustment recommendations.")
        else:
            st.success("No underpriced segments")
            st.caption("All segments are adequately priced or profitable.")

# --- THRESHOLD ALERTS ---
st.subheader("Operational Alerts")

high_fraud = run_query("SELECT COUNT(*) AS CNT FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS WHERE FRAUD_SCORE > 80")
overdue = run_query("""
    SELECT COUNT(*) AS CNT, ROUND(SUM(OUTSTANDING_BALANCE), 0) AS BAL
    FROM INSURANCE_AI_HUB.ANALYTICS.BILLING WHERE PAYMENT_STATUS = 'Overdue'
""")
high_churn = run_query("SELECT COUNT(*) AS CNT FROM INSURANCE_AI_HUB.ANALYTICS.AT_RISK_POLICIES WHERE CHURN_PROBABILITY > 0.7")

col1, col2, col3 = st.columns(3)
with col1:
    with st.container(border=True):
        fraud_cnt = int(high_fraud["CNT"].iloc[0])
        if fraud_cnt > 0:
            st.error(f"**{fraud_cnt} High-Fraud Claims** (Score > 80)")
            st.caption("Route to SIU for investigation — high-fraud claims have 3x avg payout.")
        else:
            st.success("No high-fraud claims")
            st.caption("All claims below fraud threshold.")

with col2:
    with st.container(border=True):
        overdue_cnt = int(overdue["CNT"].iloc[0])
        if overdue_cnt > 0:
            st.warning(f"**{overdue_cnt} Overdue Invoices** (${overdue['BAL'].iloc[0]:,.0f})")
            st.caption(f"Avg overdue balance: ${overdue['BAL'].iloc[0]/max(overdue_cnt,1):,.0f}/invoice — trigger collection workflow.")
        else:
            st.success("No overdue invoices")
            st.caption("All billing current.")

with col3:
    with st.container(border=True):
        churn_cnt = int(high_churn["CNT"].iloc[0])
        if churn_cnt > 0:
            st.warning(f"**{churn_cnt} High-Churn Policies** (>70%)")
            st.caption("Visit Retention Rx for AI-generated save actions on these policies.")
        else:
            st.success("No high-churn policies")
            st.caption("Retention risk is low across the book.")

# --- WEATHER WARNINGS ---
st.subheader("Severe Weather (Last 7 Days)")
with st.container(border=True):
    recent = run_query("""
        SELECT STATE, EVENT_TYPE, EVENT_SEVERITY, ALERT_TITLE, REPORTED_DATE::DATE AS ALERT_DATE
        FROM INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_NWS_WEATHER_ALERTS
        WHERE REPORTED_DATE >= DATEADD('day', -7, CURRENT_DATE())
          AND EVENT_SEVERITY IN ('Severe', 'Extreme')
        ORDER BY REPORTED_DATE DESC LIMIT 25
    """)
    if recent.empty:
        st.info("No severe/extreme weather alerts in the last 7 days.")
        st.caption("Clear weather window — good time for field inspections or renewals outreach.")
    else:
        st.dataframe(recent, hide_index=True, use_container_width=True)
        top_event = recent["EVENT_TYPE"].value_counts()
        st.caption(f"{len(recent)} alerts in 7 days — most common: {top_event.index[0]} ({top_event.iloc[0]} alerts). Expect related claims within 30 days.")

st.subheader("Daily Enrichment Tasks")
with st.container(border=True):
    st.markdown("""
    | Task | Schedule | Refreshes |
    |---|---|---|
    | `DAILY_ENRICHMENT_ROOT` | 2:00 AM UTC | Triggers all child tasks |
    | `DAILY_REFRESH_VEHICLE_DETAILS` | After root | New auto policy vehicles |
    | `DAILY_REFRESH_CUSTOMER_ATTR_HISTORY` | After root | ~50 attribute changes/day |
    | `DAILY_REFRESH_CLAIM_ACTIVITY_LOG` | After root | ~200 adjuster activities/day |
    | `DAILY_UPDATE_FRICTION_REASON` | After root | New claims friction reasons |
    """)
    st.caption("All tasks run sequentially after the root task at 2 AM UTC. Check TASK_HISTORY() for recent run status.")

# ============================================================
# AI-POWERED WEEKLY BRIEF GENERATOR
# ============================================================
st.divider()
st.subheader("AI Executive Brief Generator")
st.caption("One-click AI summary of the week's key events using AI_SUMMARIZE_AGG and AI_AGG.")

conn = st.session_state.conn

brief_period = st.selectbox("Report period:", ["Last 7 days", "Last 14 days", "Last 30 days"], key="brief_period")
days = {"Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30}[brief_period]

if st.button("Generate Executive Brief", type="primary", icon=":material/auto_awesome:", key="gen_brief"):
    with st.spinner("AI is analyzing all data from the past week... this may take a moment."):
        sections = []

        # Section 1: Claims summary
        try:
            claims_brief = run_query(f"""
                SELECT AI_AGG(
                    CLAIM_TYPE || ' claim ($' || CLAIM_AMOUNT || ') - ' || CAUSE_OF_LOSS || ' - Status: ' || STATUS,
                    'Summarize these insurance claims from the past {days} days. Highlight: (1) total count and dollar amount, (2) most common claim types, (3) any concerning patterns like fraud or litigation. Keep it to 3-4 sentences.'
                ) AS BRIEF
                FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS
                WHERE CLAIM_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
            """)
            if not claims_brief.empty and claims_brief["BRIEF"].iloc[0]:
                sections.append(("Claims Activity", claims_brief["BRIEF"].iloc[0]))
        except Exception:
            pass

        # Section 2: Customer feedback
        try:
            feedback_brief = run_query(f"""
                SELECT AI_SUMMARIZE_AGG(COMMENTS,
                    'What are the main themes in these customer comments?'
                ) AS BRIEF
                FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMER_SURVEYS
                WHERE SURVEY_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
                  AND COMMENTS IS NOT NULL AND COMMENTS != ''
            """)
            if not feedback_brief.empty and feedback_brief["BRIEF"].iloc[0]:
                sections.append(("Customer Feedback", feedback_brief["BRIEF"].iloc[0]))
        except Exception:
            pass

        # Section 3: Key metrics snapshot
        try:
            metrics = run_query(f"""
                SELECT COUNT(DISTINCT cl.CLAIM_ID) AS NEW_CLAIMS,
                       ROUND(SUM(cl.CLAIM_AMOUNT), 0) AS TOTAL_INCURRED,
                       COUNT(DISTINCT p.POLICY_ID) AS NEW_POLICIES,
                       ROUND(SUM(p.PREMIUM_AMOUNT), 0) AS NEW_PREMIUM,
                       (SELECT COUNT(*) FROM INSURANCE_AI_HUB.ANALYTICS.AT_RISK_POLICIES WHERE CHURN_PROBABILITY > 0.7) AS HIGH_CHURN,
                       (SELECT COUNT(*) FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS WHERE FRAUD_SCORE > 80 AND CLAIM_DATE >= DATEADD('day', -{days}, CURRENT_DATE())) AS HIGH_FRAUD
                FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS cl
                FULL OUTER JOIN INSURANCE_AI_HUB.ANALYTICS.POLICIES p
                    ON cl.CLAIM_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
                    AND p.CREATED_AT >= DATEADD('day', -{days}, CURRENT_DATE())
                WHERE cl.CLAIM_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
                   OR p.CREATED_AT >= DATEADD('day', -{days}, CURRENT_DATE())
            """)
            if not metrics.empty:
                m = metrics.iloc[0]
                sections.append(("Key Metrics", f"New claims: {int(m['NEW_CLAIMS']):,} (${int(m['TOTAL_INCURRED']):,} incurred). High-fraud claims: {int(m['HIGH_FRAUD'])}. High-churn policies: {int(m['HIGH_CHURN'])}."))
        except Exception:
            pass

        # Section 4: Weather alerts
        try:
            weather_brief = run_query(f"""
                SELECT AI_AGG(
                    STATE || ': ' || EVENT_TYPE || ' (' || EVENT_SEVERITY || ')',
                    'Summarize severe weather activity in the past {days} days. Which states were most impacted? What types of events dominated? Keep to 2-3 sentences.'
                ) AS BRIEF
                FROM INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_NWS_WEATHER_ALERTS
                WHERE REPORTED_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
                  AND EVENT_SEVERITY IN ('Severe', 'Extreme')
            """)
            if not weather_brief.empty and weather_brief["BRIEF"].iloc[0]:
                sections.append(("Weather & Catastrophe", weather_brief["BRIEF"].iloc[0]))
        except Exception:
            pass

        # Display brief
        if sections:
            with st.container(border=True):
                st.markdown(f"### Executive Brief — {brief_period}")
                st.markdown(f"*Generated {st.session_state.conn.query('SELECT CURRENT_TIMESTAMP()::VARCHAR AS TS').iloc[0]['TS'][:19]}*")
                st.divider()
                for title, content in sections:
                    st.markdown(f"**{title}**")
                    st.info(content)
                st.divider()
                st.caption("Brief generated by AI_AGG and AI_SUMMARIZE_AGG — review for accuracy before distribution.")
        else:
            st.warning("Unable to generate brief — no recent data found for the selected period.")
