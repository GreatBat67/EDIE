import streamlit as st
from utils.queries import run_query, safe_query, val, fmt_currency, fmt_number

st.header("Pricing & Risk Prescriptions")
st.caption("AI-generated pricing recommendations using internal loss data + FEMA disasters + NWS weather alerts")

# --- PRICING RECOMMENDATIONS ---
st.subheader("Pricing Recommendations by State & Policy Type")

pricing = run_query("SELECT * FROM INSURANCE_AI_HUB.ANALYTICS.PRICING_RECOMMENDATIONS ORDER BY LOSS_RATIO DESC")

status_filter = st.multiselect("Filter by Status", ["UNDERPRICED", "MARGINAL", "ADEQUATE", "PROFITABLE"],
                                default=["UNDERPRICED", "MARGINAL"])
filtered = pricing[pricing["PRICING_STATUS"].isin(status_filter)] if status_filter else pricing

underpriced_count = len(filtered[filtered["PRICING_STATUS"] == "UNDERPRICED"])
marginal_count = len(filtered[filtered["PRICING_STATUS"] == "MARGINAL"])

with st.container(horizontal=True):
    st.metric("Underpriced", str(underpriced_count), border=True)
    st.metric("Marginal", str(marginal_count), border=True)
    st.metric("States Analyzed", str(len(pricing["STATE"].unique())), border=True)
    st.metric("Policy Types", str(len(pricing["POLICY_TYPE"].unique())), border=True)

total_underpriced = len(pricing[pricing["PRICING_STATUS"] == "UNDERPRICED"])
total_marginal = len(pricing[pricing["PRICING_STATUS"] == "MARGINAL"])
st.caption(f"{total_underpriced} underpriced and {total_marginal} marginal segments across {len(pricing)} state-type combos — these need rate review before next renewal cycle.")

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
        gap = worst["AVG_FEMA_PAYOUT"] - worst["YOUR_AVG_PREMIUM"]
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
    st.caption("**Assumptions:** Pricing recommendations generated by Claude Sonnet 4.6 using loss ratio, FEMA disaster count, "
               "and NWS severe weather alerts as inputs. Recommendations are advisory — actuarial review required before rate changes. "
               "FEMA flood comparison uses avg building damage amount since 2020.")
