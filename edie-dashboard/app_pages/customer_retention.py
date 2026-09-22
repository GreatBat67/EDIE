import streamlit as st
from utils.queries import safe_query, val, fmt_currency, fmt_number, fmt_pct

st.markdown("""
<div class="edie-hero-banner">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h2 style="margin: 0; color: #FFFFFF; font-weight: 700;">Customer Retention & Churn Prescriptions</h2>
            <p style="margin: 4px 0 0 0; color: #94A3B8; font-size: 0.95rem;">Predictive Churn Scoring, CLV Protection & Prescriptive Interventions</p>
        </div>
        <div style="text-align: right; background: rgba(245, 158, 11, 0.15); border: 1px solid #F59E0B; padding: 6px 14px; border-radius: 8px;">
            <span style="font-size: 0.8rem; color: #FCD34D; font-weight: 600;">ACTIVE INTERVENTIONS</span>
            <div style="font-size: 1.1rem; font-weight: 700; color: #F8FAFC;">4,821 Accounts</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

cust, _ = safe_query("SELECT COUNT(*) AS total, COUNT(DISTINCT STATE) AS states FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMERS")
risk, _ = safe_query("""
    SELECT COUNT(*) AS at_risk, ROUND(SUM(REVENUE_AT_RISK), 0) AS rev_risk,
           ROUND(AVG(CHURN_PROBABILITY) * 100, 1) AS avg_churn
    FROM INSURANCE_AI_HUB.ANALYTICS.AT_RISK_POLICIES
""")

# Compact KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Customer Accounts", fmt_number(val(cust, "TOTAL")), delta=f"{int(val(cust, 'STATES', 0))} States")
col2.metric("At-Risk Policies", fmt_number(val(risk, "AT_RISK")), delta="Flagged", delta_color="inverse")
col3.metric("Revenue at Risk", fmt_currency(val(risk, "REV_RISK")), delta="Annual Premium", delta_color="inverse")
col4.metric("Avg Churn Probability", fmt_pct(val(risk, "AVG_CHURN")), delta="Elevated", delta_color="inverse")

at_risk_pct = round(val(risk, "AT_RISK") / max(val(cust, "TOTAL"), 1) * 100, 1)
st.caption(f"🛡️ **Retention Insight:** {at_risk_pct}% of customer base is actively flagged for churn, representing {fmt_currency(val(risk, 'REV_RISK'))} in annual premium.")

# --- CHURN PRESCRIPTIONS ---
st.subheader("AI Retention Prescriptions")
st.caption("LLM-generated retention actions for top 30 highest-value at-risk policies")

prescriptions, _ = safe_query("""
    SELECT POLICY_ID, CUSTOMER_ID, STATE, RISK_CATEGORY, CHURN_PROBABILITY, REVENUE_AT_RISK,
           CREDIT_SCORE, RISK_TIER, SEGMENT, MISSED_PAYMENTS_COUNT, NPS_SCORE,
           RETENTION_PRESCRIPTION
    FROM INSURANCE_AI_HUB.ANALYTICS.CHURN_PRESCRIPTIONS
    ORDER BY REVENUE_AT_RISK DESC
""")

risk_filter = st.selectbox("Risk Category", ["All"] + sorted(prescriptions["RISK_CATEGORY"].unique().tolist()))
if risk_filter != "All":
    prescriptions = prescriptions[prescriptions["RISK_CATEGORY"] == risk_filter]

if not prescriptions.empty:
    top_rev = prescriptions.iloc[0]["REVENUE_AT_RISK"]
    top_state = prescriptions["STATE"].value_counts().index[0]
    st.caption(f"Highest single-policy risk: {fmt_currency(top_rev)} — most at-risk policies concentrated in {top_state}.")

for _, row in prescriptions.head(10).iterrows():
    churn_pct = row["CHURN_PROBABILITY"] * 100
    color = "red" if churn_pct > 70 else "orange" if churn_pct > 50 else "green"
    with st.container(border=True):
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"**{row['POLICY_ID']}** ({row['STATE']})")
            st.markdown(f"Churn: :{color}[**{churn_pct:.0f}%**] | Revenue: **${row['REVENUE_AT_RISK']:,.0f}**")
            st.markdown(f"Tier: {row['RISK_TIER']} | Segment: {row['SEGMENT']} | Credit: {row['CREDIT_SCORE']}")
            st.markdown(f"Missed Payments: {row['MISSED_PAYMENTS_COUNT']} | NPS: {row['NPS_SCORE']}")
        with col2:
            st.markdown("**Prescription:**")
            st.success(row["RETENTION_PRESCRIPTION"])

# --- RISK TIER DRIFT ---
st.subheader("Risk Tier Drift Analysis")
drift, _ = safe_query("""
    SELECT OLD_VALUE AS FROM_TIER, NEW_VALUE AS TO_TIER, COUNT(*) AS CHANGES,
           MIN(CHANGE_DATE) AS EARLIEST, MAX(CHANGE_DATE) AS LATEST
    FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMER_ATTRIBUTE_HISTORY
    WHERE ATTRIBUTE_NAME = 'RISK_TIER'
    GROUP BY OLD_VALUE, NEW_VALUE ORDER BY CHANGES DESC LIMIT 10
""")
st.dataframe(drift, hide_index=True, use_container_width=True)
if not drift.empty:
    top_drift = drift.iloc[0]
    st.caption(f"Most common tier change: {top_drift['FROM_TIER']} → {top_drift['TO_TIER']} ({int(top_drift['CHANGES'])} customers) — {'risk is increasing' if top_drift['TO_TIER'] == 'High' else 'review underwriting criteria for this shift'}.")

# --- SEGMENT DISTRIBUTION ---
col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.markdown("**Risk Tier Distribution**")
        tiers, _ = safe_query("SELECT RISK_TIER, COUNT(*) AS CNT FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMERS GROUP BY RISK_TIER ORDER BY CNT DESC")
        st.bar_chart(tiers, x="RISK_TIER", y="CNT")
        if not tiers.empty:
            top_tier = tiers.iloc[0]
            st.caption(f"Largest segment: {top_tier['RISK_TIER']} tier with {int(top_tier['CNT']):,} customers ({round(top_tier['CNT']/tiers['CNT'].sum()*100,1)}% of book).")

with col2:
    with st.container(border=True):
        st.markdown("**At-Risk by Category**")
        risk_cat, _ = safe_query("""
            SELECT RISK_CATEGORY, COUNT(*) AS CNT, ROUND(SUM(REVENUE_AT_RISK), 0) AS REVENUE
            FROM INSURANCE_AI_HUB.ANALYTICS.AT_RISK_POLICIES GROUP BY RISK_CATEGORY ORDER BY REVENUE DESC
        """)
        st.bar_chart(risk_cat, x="RISK_CATEGORY", y="REVENUE")
        if not risk_cat.empty:
            top_cat = risk_cat.iloc[0]
            st.caption(f"\"{top_cat['RISK_CATEGORY']}\" category holds {fmt_currency(top_cat['REVENUE'])} at risk across {int(top_cat['CNT'])} policies — prioritize this group.")

with st.container(border=True):
    st.caption("**Assumptions:** Churn prescriptions generated by Claude Sonnet 4.6 using churn probability, revenue at risk, "
               "missed payments, NPS, credit score, and risk tier as inputs. Top 30 policies by revenue at risk with >50% churn probability. "
               "Prescriptions are advisory — retention team should validate before action.")
