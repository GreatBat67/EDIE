import streamlit as st
from utils.queries import run_query, safe_query, val, fmt_currency, fmt_number

st.header("Geographic Risk Intelligence")
st.caption("Interactive map overlaying claims density, weather severity, FEMA disasters, and flood exposure by state.")

# --- STATE-LEVEL RISK DATA ---
with st.spinner("Building geographic risk profile..."):
    geo_risk = run_query("""
        WITH claims_by_state AS (
            SELECT c.STATE, COUNT(DISTINCT cl.CLAIM_ID) AS CLAIMS,
                   ROUND(SUM(cl.CLAIM_AMOUNT), 0) AS TOTAL_INCURRED,
                   COUNT(DISTINCT p.POLICY_ID) AS POLICIES,
                   ROUND(SUM(p.PREMIUM_AMOUNT), 0) AS TOTAL_PREMIUM,
                   ROUND(SUM(cl.CLAIM_AMOUNT) / NULLIF(SUM(p.PREMIUM_AMOUNT), 0) * 100, 1) AS LOSS_RATIO
            FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMERS c
            JOIN INSURANCE_AI_HUB.ANALYTICS.POLICIES p ON p.CUSTOMER_ID = c.CUSTOMER_ID
            LEFT JOIN INSURANCE_AI_HUB.ANALYTICS.CLAIMS cl ON cl.POLICY_ID = p.POLICY_ID
            WHERE c.STATE IS NOT NULL
            GROUP BY c.STATE
        ),
        weather_by_state AS (
            SELECT STATE, COUNT(*) AS SEVERE_ALERTS
            FROM INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_NWS_WEATHER_ALERTS
            WHERE EVENT_SEVERITY IN ('Severe', 'Extreme')
              AND REPORTED_DATE >= DATEADD('year', -1, CURRENT_DATE())
            GROUP BY STATE
        ),
        fema_by_state AS (
            SELECT STATE, COUNT(*) AS FEMA_DISASTERS,
                   MAX(DESIGNATED_DATE)::DATE AS LAST_DISASTER
            FROM INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_FEMA_DISASTER_DECLARATIONS
            WHERE DESIGNATED_DATE >= '2020-01-01'
            GROUP BY STATE
        ),
        flood_by_state AS (
            SELECT STATE, COUNT(*) AS FLOOD_CLAIMS,
                   ROUND(AVG(BUILDING_DAMAGE_AMOUNT), 0) AS AVG_FLOOD_PAYOUT
            FROM INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_FEMA_FLOOD_CLAIMS
            WHERE DATE_OF_LOSS >= '2020-01-01' AND STATE IS NOT NULL
            GROUP BY STATE
        )
        SELECT cs.STATE, cs.POLICIES, cs.CLAIMS, cs.TOTAL_PREMIUM, cs.TOTAL_INCURRED, cs.LOSS_RATIO,
               COALESCE(ws.SEVERE_ALERTS, 0) AS SEVERE_WEATHER,
               COALESCE(fs.FEMA_DISASTERS, 0) AS FEMA_DISASTERS,
               fs.LAST_DISASTER,
               COALESCE(fl.FLOOD_CLAIMS, 0) AS FLOOD_CLAIMS,
               COALESCE(fl.AVG_FLOOD_PAYOUT, 0) AS AVG_FLOOD_PAYOUT,
               CASE
                   WHEN cs.LOSS_RATIO > 70 AND COALESCE(ws.SEVERE_ALERTS, 0) > 1000 THEN 'CRITICAL'
                   WHEN cs.LOSS_RATIO > 50 OR COALESCE(ws.SEVERE_ALERTS, 0) > 5000 THEN 'HIGH'
                   WHEN COALESCE(ws.SEVERE_ALERTS, 0) > 1000 OR COALESCE(fs.FEMA_DISASTERS, 0) > 10 THEN 'ELEVATED'
                   ELSE 'NORMAL'
               END AS RISK_LEVEL
        FROM claims_by_state cs
        LEFT JOIN weather_by_state ws ON ws.STATE = cs.STATE
        LEFT JOIN fema_by_state fs ON fs.STATE = cs.STATE
        LEFT JOIN flood_by_state fl ON fl.STATE = cs.STATE
        ORDER BY cs.TOTAL_INCURRED DESC
    """)

# --- TOP METRICS ---
if not geo_risk.empty:
    critical = geo_risk[geo_risk["RISK_LEVEL"] == "CRITICAL"]
    high = geo_risk[geo_risk["RISK_LEVEL"] == "HIGH"]
    total_exposure = geo_risk["TOTAL_INCURRED"].sum()

    with st.container(horizontal=True):
        st.metric("States Tracked", str(len(geo_risk)), border=True)
        st.metric("Critical Risk", str(len(critical)), border=True)
        st.metric("High Risk", str(len(high)), border=True)
        st.metric("Total Exposure", fmt_currency(total_exposure), border=True)

    if not critical.empty:
        crit_states = ", ".join(critical["STATE"].tolist())
        st.caption(f"CRITICAL states ({crit_states}): loss ratio >70% AND >1,000 severe weather alerts — immediate pricing review required.")
    else:
        st.caption(f"{len(high)} states at HIGH risk — monitor closely for emerging catastrophe patterns.")

# --- MAP VIEW ---
st.subheader("State Risk Map")

# State coordinates for mapping
STATE_COORDS = {
    "AL": (32.8, -86.8), "AK": (64.2, -152.5), "AZ": (34.0, -111.1), "AR": (35.2, -91.8),
    "CA": (36.8, -119.4), "CO": (39.1, -105.4), "CT": (41.6, -72.7), "DE": (38.9, -75.5),
    "FL": (27.7, -81.5), "GA": (32.2, -83.6), "HI": (19.9, -155.6), "ID": (44.1, -114.7),
    "IL": (40.6, -89.4), "IN": (40.3, -86.1), "IA": (42.0, -93.2), "KS": (39.0, -98.5),
    "KY": (37.7, -84.3), "LA": (30.5, -91.2), "ME": (45.4, -69.4), "MD": (39.0, -76.6),
    "MA": (42.4, -71.4), "MI": (44.3, -85.6), "MN": (46.7, -94.7), "MS": (32.4, -89.7),
    "MO": (37.9, -91.8), "MT": (46.9, -110.4), "NE": (41.1, -98.3), "NV": (38.8, -116.4),
    "NH": (43.2, -71.6), "NJ": (40.1, -74.5), "NM": (34.5, -105.9), "NY": (43.0, -75.5),
    "NC": (35.8, -79.0), "ND": (47.5, -100.5), "OH": (40.4, -82.9), "OK": (35.0, -97.1),
    "OR": (43.8, -120.6), "PA": (41.2, -77.2), "RI": (41.6, -71.5), "SC": (33.8, -81.2),
    "SD": (43.9, -99.4), "TN": (35.5, -86.0), "TX": (31.1, -97.6), "UT": (39.3, -111.1),
    "VT": (44.0, -72.7), "VA": (37.4, -78.7), "WA": (47.8, -120.7), "WV": (38.6, -80.4),
    "WI": (43.8, -88.8), "WY": (43.1, -107.6), "DC": (38.9, -77.0)
}

if not geo_risk.empty:
    import pandas as pd
    map_data = []
    for _, row in geo_risk.iterrows():
        state = row["STATE"]
        if state in STATE_COORDS:
            lat, lon = STATE_COORDS[state]
            map_data.append({
                "lat": lat,
                "lon": lon,
                "state": state,
                "risk": row["RISK_LEVEL"],
                "claims": row["CLAIMS"],
                "incurred": row["TOTAL_INCURRED"],
            })

    if map_data:
        map_df = pd.DataFrame(map_data)
        st.map(map_df, latitude="lat", longitude="lon", size="claims")
        st.caption("Bubble size = number of claims. Larger bubbles indicate higher claims concentration.")

# --- RISK MATRIX ---
st.subheader("Risk Matrix: Weather × Loss Ratio")

risk_filter = st.multiselect("Filter by Risk Level", ["CRITICAL", "HIGH", "ELEVATED", "NORMAL"],
                              default=["CRITICAL", "HIGH", "ELEVATED"])
filtered = geo_risk[geo_risk["RISK_LEVEL"].isin(risk_filter)] if risk_filter else geo_risk

if not filtered.empty:
    display_cols = ["STATE", "RISK_LEVEL", "POLICIES", "CLAIMS", "TOTAL_PREMIUM", "TOTAL_INCURRED",
                    "LOSS_RATIO", "SEVERE_WEATHER", "FEMA_DISASTERS", "FLOOD_CLAIMS", "AVG_FLOOD_PAYOUT"]
    st.dataframe(filtered[display_cols], hide_index=True, use_container_width=True)

    worst = filtered.iloc[0]
    st.caption(f"Highest exposure: {worst['STATE']} with {fmt_currency(worst['TOTAL_INCURRED'])} incurred, {int(worst['SEVERE_WEATHER']):,} weather alerts, {int(worst['FEMA_DISASTERS'])} FEMA disasters.")

# --- DRILL-DOWN ---
st.subheader("State Drill-Down")
if not geo_risk.empty:
    selected_state = st.selectbox("Select a state to drill into:", geo_risk["STATE"].tolist())

    if selected_state:
        state_row = geo_risk[geo_risk["STATE"] == selected_state].iloc[0]

        col1, col2, col3 = st.columns(3)
        with col1:
            with st.container(border=True):
                st.markdown(f"**{selected_state} — Portfolio**")
                st.metric("Policies", fmt_number(state_row["POLICIES"]))
                st.metric("Total Premium", fmt_currency(state_row["TOTAL_PREMIUM"]))
                st.metric("Loss Ratio", f"{state_row['LOSS_RATIO']}%")
        with col2:
            with st.container(border=True):
                st.markdown(f"**{selected_state} — Claims**")
                st.metric("Total Claims", fmt_number(state_row["CLAIMS"]))
                st.metric("Total Incurred", fmt_currency(state_row["TOTAL_INCURRED"]))
                st.metric("Risk Level", state_row["RISK_LEVEL"])
        with col3:
            with st.container(border=True):
                st.markdown(f"**{selected_state} — External Risk**")
                st.metric("Severe Weather Alerts", fmt_number(state_row["SEVERE_WEATHER"]))
                st.metric("FEMA Disasters", str(int(state_row["FEMA_DISASTERS"])))
                st.metric("Avg Flood Payout", fmt_currency(state_row["AVG_FLOOD_PAYOUT"]))

        # Agents in this state
        with st.container(border=True):
            st.markdown(f"**Agents in {selected_state}**")
            agents = run_query(f"""
                SELECT AGENT_NAME, AGENCY_NAME, SPECIALIZATION, PERFORMANCE_RATING,
                       ACTIVE_POLICIES_COUNT, RETENTION_RATE
                FROM INSURANCE_AI_HUB.ANALYTICS.AGENTS
                WHERE STATE = '{selected_state}' AND STATUS = 'Active'
                ORDER BY ACTIVE_POLICIES_COUNT DESC LIMIT 10
            """)
            if not agents.empty:
                st.dataframe(agents, hide_index=True, use_container_width=True)
                st.caption(f"{len(agents)} active agents in {selected_state} — top agent: {agents.iloc[0]['AGENT_NAME']} ({int(agents.iloc[0]['ACTIVE_POLICIES_COUNT'])} policies).")
            else:
                st.info(f"No active agents found in {selected_state}.")

        # Coverage gaps
        with st.container(border=True):
            st.markdown(f"**Coverage Gap Analysis — {selected_state}**")
            gaps = run_query(f"""
                SELECT p.POLICY_TYPE, COUNT(DISTINCT p.POLICY_ID) AS POLICIES,
                       ROUND(AVG(p.PREMIUM_AMOUNT), 0) AS AVG_PREMIUM,
                       ROUND(AVG(p.COVERAGE_AMOUNT), 0) AS AVG_COVERAGE,
                       ROUND(AVG(p.DEDUCTIBLE), 0) AS AVG_DEDUCTIBLE
                FROM INSURANCE_AI_HUB.ANALYTICS.POLICIES p
                JOIN INSURANCE_AI_HUB.ANALYTICS.CUSTOMERS c ON p.CUSTOMER_ID = c.CUSTOMER_ID
                WHERE c.STATE = '{selected_state}'
                GROUP BY p.POLICY_TYPE ORDER BY POLICIES DESC
            """)
            if not gaps.empty:
                st.dataframe(gaps, hide_index=True, use_container_width=True)
                st.caption(f"Primary line: {gaps.iloc[0]['POLICY_TYPE']} ({int(gaps.iloc[0]['POLICIES'])} policies, avg premium ${int(gaps.iloc[0]['AVG_PREMIUM']):,}).")
