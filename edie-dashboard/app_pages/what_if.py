import streamlit as st
from utils.queries import run_query

st.markdown("""
<div class="edie-hero-banner">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h2 style="margin: 0; color: #FFFFFF; font-weight: 700;">What-If Scenario Analysis</h2>
            <p style="margin: 4px 0 0 0; color: #94A3B8; font-size: 0.95rem;">Adjust internal levers and external macro factors to model real-time financial impact</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

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

if st.button("Run What-If", type="primary", icon=":material/calculate:"):
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
        investment_income = base_prem * (interest_rate / 100) * 0.3

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
            combined_ratio = adj_lr + 30
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
            ai_text = whatif_result["R"].iloc[0].replace("$", "\\$")
            st.info(ai_text)
