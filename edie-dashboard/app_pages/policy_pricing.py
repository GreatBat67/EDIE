import streamlit as st
from utils.queries import run_query, safe_query, val, fmt_currency, fmt_number

st.markdown("""
<div class="edie-hero-banner">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h2 style="margin: 0; color: #FFFFFF; font-weight: 700;">Pricing Optimization Engine</h2>
            <p style="margin: 4px 0 0 0; color: #94A3B8; font-size: 0.95rem;">AI-Driven Price Elasticity, Market Benchmarks & Product Matching</p>
        </div>
        <div style="text-align: right; background: rgba(16, 185, 129, 0.15); border: 1px solid #10B981; padding: 6px 14px; border-radius: 8px;">
            <span style="font-size: 0.8rem; color: #34D399; font-weight: 600;">MULTI-STRATEGY MATCHING</span>
            <div style="font-size: 1.1rem; font-weight: 700; color: #F8FAFC;">Hybrid Scoring Active</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- PRICING & RISK DRILL-DOWN WITH MULTI-DIMENSIONAL FILTERS ---
st.subheader("Interactive Pricing Recommendations & Risk Prescriptions")

pricing = run_query("SELECT * FROM INSURANCE_AI_HUB.ANALYTICS.PRICING_RECOMMENDATIONS ORDER BY LOSS_RATIO DESC")

# Filter Controls Bar
with st.container(border=True):
    st.markdown("🔍 **Multi-Dimensional Filters & Parameters**")
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    
    with fcol1:
        all_states = sorted(pricing["STATE"].unique().tolist())
        selected_states = st.multiselect(
            "State Filter",
            ["All States Combined"] + all_states,
            default=["All States Combined"],
        )
    
    with fcol2:
        types_list = ["All Policy Types"] + sorted(pricing["POLICY_TYPE"].unique().tolist())
        selected_type = st.selectbox("Policy Line of Business", types_list)
        
    with fcol3:
        status_filter = st.multiselect(
            "Pricing Status",
            ["UNDERPRICED", "MARGINAL", "ADEQUATE", "PROFITABLE"],
            default=["UNDERPRICED", "MARGINAL", "ADEQUATE", "PROFITABLE"]
        )
        
    with fcol4:
        min_loss_ratio = st.slider("Min Loss Ratio (%)", min_value=0, max_value=150, value=0, step=5)

# Apply Filter Logic
filtered = pricing.copy()
if "All States Combined" not in selected_states and selected_states:
    filtered = filtered[filtered["STATE"].isin(selected_states)]
if selected_type != "All Policy Types":
    filtered = filtered[filtered["POLICY_TYPE"] == selected_type]
if status_filter:
    filtered = filtered[filtered["PRICING_STATUS"].isin(status_filter)]
if min_loss_ratio > 0:
    filtered = filtered[filtered["LOSS_RATIO"] >= min_loss_ratio]

# Interactive Dynamic KPIs based on Filter Selection
underpriced_count = len(filtered[filtered["PRICING_STATUS"] == "UNDERPRICED"])
marginal_count = len(filtered[filtered["PRICING_STATUS"] == "MARGINAL"])
avg_filtered_lr = round(filtered["LOSS_RATIO"].mean(), 1) if not filtered.empty else 0
avg_filtered_prem = round(filtered["AVG_PREMIUM"].mean(), 0) if not filtered.empty else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Segments Filtered", f"{len(filtered)} / {len(pricing)}", delta="Active Scope")
col2.metric("Underpriced Segments", str(underpriced_count), delta="Action Needed", delta_color="inverse" if underpriced_count > 0 else "normal")
col3.metric("Marginal Segments", str(marginal_count), delta="Watchlist", delta_color="inverse" if marginal_count > 0 else "normal")
col4.metric("Avg Segment Loss Ratio", f"{avg_filtered_lr}%", delta="Critical" if avg_filtered_lr > 70 else "Elevated" if avg_filtered_lr > 50 else "Healthy", delta_color="inverse" if avg_filtered_lr > 50 else "normal")
col5.metric("Avg Written Premium", fmt_currency(avg_filtered_prem), delta="Benchmark")

st.divider()

for _, row in filtered.head(15).iterrows():
    status_icon = {"UNDERPRICED": ":red[UNDERPRICED]", "MARGINAL": ":orange[MARGINAL]",
                   "ADEQUATE": ":green[ADEQUATE]", "PROFITABLE": ":blue[PROFITABLE]"}
    with st.container(border=True):
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"**{row['STATE']} — {row['POLICY_TYPE']}**")
            st.markdown(f"Status: {status_icon.get(row['PRICING_STATUS'], row['PRICING_STATUS'])}")
            st.markdown(f"Loss Ratio: **{row['LOSS_RATIO']}%**")
            st.markdown(f"Avg Premium: **${row['AVG_PREMIUM']:,.0f}**")
            st.markdown(f"FEMA Disasters: {row['FEMA_DISASTERS']} | Weather Alerts: {row['SEVERE_WEATHER_ALERTS']:,}")
        with col2:
            st.markdown(f"**AI Prescription:**")
            st.info(row["PRICING_RECOMMENDATION"])

# --- FLOOD RISK BENCHMARK ---
st.subheader("Flood Risk: Your Premiums vs FEMA Claims")
flood = run_query("""
    WITH your_data AS (
        SELECT c.STATE, ROUND(AVG(p.PREMIUM_AMOUNT), 0) AS YOUR_AVG_PREMIUM,
               COUNT(DISTINCT p.POLICY_ID) AS YOUR_POLICIES
        FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMERS c
        JOIN INSURANCE_AI_HUB.ANALYTICS.POLICIES p ON p.CUSTOMER_ID = c.CUSTOMER_ID
        WHERE p.POLICY_TYPE IN ('Homeowners', 'Commercial')
        GROUP BY c.STATE
    ),
    fema AS (
        SELECT STATE, ROUND(AVG(BUILDING_DAMAGE_AMOUNT), 0) AS AVG_FEMA_PAYOUT, COUNT(*) AS FEMA_CLAIMS
        FROM INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_FEMA_FLOOD_CLAIMS
        WHERE DATE_OF_LOSS >= '2020-01-01' AND STATE IS NOT NULL GROUP BY STATE
    )
    SELECT y.STATE, y.YOUR_POLICIES, y.YOUR_AVG_PREMIUM, f.FEMA_CLAIMS, f.AVG_FEMA_PAYOUT,
           CASE WHEN f.AVG_FEMA_PAYOUT > y.YOUR_AVG_PREMIUM THEN 'UNDERPRICED vs FEMA' ELSE 'OK' END AS FLOOD_RISK_FLAG
    FROM your_data y LEFT JOIN fema f ON f.STATE = y.STATE
    WHERE f.STATE IS NOT NULL ORDER BY f.AVG_FEMA_PAYOUT DESC NULLS LAST LIMIT 15
""")
st.dataframe(flood, hide_index=True, use_container_width=True)
if not flood.empty:
    underpriced_flood = flood[flood["FLOOD_RISK_FLAG"] == "UNDERPRICED vs FEMA"]
    if not underpriced_flood.empty:
        worst = underpriced_flood.iloc[0]
        gap = float(worst["AVG_FEMA_PAYOUT"]) - float(worst["YOUR_AVG_PREMIUM"])
        st.caption(f"{len(underpriced_flood)} state(s) where avg FEMA payout exceeds your premium — {worst['STATE']} has the largest gap at {fmt_currency(gap)}/policy.")
    else:
        st.caption("All states have premiums above avg FEMA flood payouts — flood pricing looks adequate.")

# --- ECONOMIC INDICATORS ---
st.subheader("Economic Outlook (FRED)")
col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.markdown("**Federal Funds Rate** — impacts investment income")
        fed = run_query("""
            SELECT OBSERVATION_DATE, VALUE FROM INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_FRED_ECONOMIC_DATA
            WHERE SERIES_ID = 'FEDFUNDS' AND OBSERVATION_DATE >= '2020-01-01' ORDER BY OBSERVATION_DATE
        """)
        st.line_chart(fed, x="OBSERVATION_DATE", y="VALUE")
        if not fed.empty:
            latest = fed.iloc[-1]["VALUE"]
            prev_yr = fed[fed["OBSERVATION_DATE"] <= fed.iloc[-1]["OBSERVATION_DATE"].replace(year=fed.iloc[-1]["OBSERVATION_DATE"].year - 1)]
            if not prev_yr.empty:
                yr_ago = prev_yr.iloc[-1]["VALUE"]
                chg = latest - yr_ago
                st.caption(f"Fed funds rate at {latest}%, {'up' if chg > 0 else 'down'} {abs(chg):.2f}pp YoY — {'higher' if chg > 0 else 'lower'} investment yields for float portfolio.")
            else:
                st.caption(f"Fed funds rate at {latest}%.")

with col2:
    with st.container(border=True):
        st.markdown("**30-Year Mortgage Rate** — impacts homeowners demand")
        mort = run_query("""
            SELECT OBSERVATION_DATE, VALUE FROM INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_FRED_ECONOMIC_DATA
            WHERE SERIES_ID = 'MORTGAGE30US' AND OBSERVATION_DATE >= '2020-01-01' ORDER BY OBSERVATION_DATE
        """)
        st.line_chart(mort, x="OBSERVATION_DATE", y="VALUE")
        if not mort.empty:
            latest_mort = mort.iloc[-1]["VALUE"]
            st.caption(f"30-year mortgage at {latest_mort}% — {'high rates may slow new homeowners policy growth' if latest_mort > 6 else 'moderate rates support housing activity'}.")

with st.container(border=True):
    st.subheader("Multi-Strategy Insurance Product Matching")
    st.caption("Illustrative benchmark of matching strategies — Exact, Fuzzy, Semantic (Cortex Embeddings), and Hybrid scoring against competitor tiers.")
    
    st.markdown("""
| Our Policy Tier | Matched Competitor Tier | Carrier | Match Strategy | Similarity Breakdown | Pricing Delta |
|---|---|---|---|---|---|
| **Commercial Multi-Peril Plus** | *Commercial Advantage Gold* | Competitor A | Hybrid | Name: 98% • Limits: 94% • Endorsements: 95% | :red[**+6.3% above Market**] |
| **Personal Auto Preferred** | *Auto Elite Safeguard* | Competitor B | Hybrid | Name: 92% • Deductibles: 96% • Terms: 93% | :green[**-1.8% below Market**] |
| **Homeowners HO-3 Elite** | *Premier Home Guard* | Competitor C | Hybrid | Name: 89% • Exclusions: 93% • Wind/Hail: 92% | :orange[**+3.4% above Market**] |
""")

with st.container(border=True):
    st.caption("**Assumptions:** Pricing recommendations generated by Claude Sonnet 4.6 using loss ratio, FEMA disaster count, "
               "and NWS severe weather alerts as inputs. Recommendations are advisory — actuarial review required before rate changes. "
               "FEMA flood comparison uses avg building damage amount since 2020.")
