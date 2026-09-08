import streamlit as st
from utils.queries import run_query, safe_query, val

st.header("Data Quality Observability")

dq_totals, _ = safe_query("""
    SELECT COUNT(*) AS total_rules,
           SUM(CASE WHEN IS_ACTIVE THEN 1 ELSE 0 END) AS active_rules
    FROM INSURANCE_AI_HUB.DATA_QUALITY.DQ_RULES
""")
fail_count, _ = safe_query("""
    SELECT COUNT(*) AS fails FROM INSURANCE_AI_HUB.DATA_QUALITY.DQ_RESULTS WHERE STATUS = 'Fail'
""")

with st.container(horizontal=True):
    st.metric("DQ Rules", int(val(dq_totals, "TOTAL_RULES")), border=True)
    st.metric("Active Rules", int(val(dq_totals, "ACTIVE_RULES")), border=True)
    st.metric("Total Failures (90d)", int(val(fail_count, "FAILS")), border=True)

fail_rate = round(val(fail_count, "FAILS") / max(val(dq_totals, "ACTIVE_RULES"), 1), 1)
st.caption(f"{int(val(fail_count, 'FAILS'))} failures across {int(val(dq_totals, 'ACTIVE_RULES'))} active rules — avg {fail_rate} failures per rule in 90 days.")

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.markdown("**Latest Table Scores**")
        scores = run_query("""
            SELECT TABLE_NAME, OVERALL_SCORE, COMPLETENESS_SCORE, VALIDITY_SCORE, TIMELINESS_SCORE, TREND
            FROM INSURANCE_AI_HUB.DATA_QUALITY.DQ_SCORES
            QUALIFY ROW_NUMBER() OVER (PARTITION BY TABLE_NAME ORDER BY SCORE_DATE DESC) = 1
            ORDER BY OVERALL_SCORE
        """)
        st.dataframe(scores, hide_index=True, use_container_width=True)
        if not scores.empty:
            worst_tbl = scores.iloc[0]
            best_tbl = scores.iloc[-1]
            st.caption(f"Lowest quality: {worst_tbl['TABLE_NAME']} at {worst_tbl['OVERALL_SCORE']}% — highest: {best_tbl['TABLE_NAME']} at {best_tbl['OVERALL_SCORE']}%.")

with col2:
    with st.container(border=True):
        st.markdown("**Most Failing Rules**")
        failing = run_query("""
            SELECT r.RULE_NAME, r.TARGET_TABLE, r.SEVERITY, COUNT(*) AS FAIL_COUNT
            FROM INSURANCE_AI_HUB.DATA_QUALITY.DQ_RESULTS res
            JOIN INSURANCE_AI_HUB.DATA_QUALITY.DQ_RULES r ON res.RULE_ID = r.RULE_ID
            WHERE res.STATUS = 'Fail'
            GROUP BY r.RULE_NAME, r.TARGET_TABLE, r.SEVERITY
            ORDER BY FAIL_COUNT DESC LIMIT 10
        """)
        st.dataframe(failing, hide_index=True, use_container_width=True)
        if not failing.empty:
            top_fail = failing.iloc[0]
            st.caption(f"Top failing rule: \"{top_fail['RULE_NAME']}\" on {top_fail['TARGET_TABLE']} ({int(top_fail['FAIL_COUNT'])} failures, severity: {top_fail['SEVERITY']}).")

with st.container(border=True):
    st.markdown("**Unhealthiest Columns**")
    col_health = run_query("""
        SELECT TABLE_NAME, COLUMN_NAME, ROUND(AVG(HEALTH_SCORE), 2) AS AVG_HEALTH,
               ROUND(AVG(NULL_RATE), 2) AS AVG_NULL_RATE, ROUND(AVG(OUTLIER_RATE), 2) AS AVG_OUTLIER_RATE
        FROM INSURANCE_AI_HUB.DATA_QUALITY.DQ_COLUMN_HEALTH
        GROUP BY TABLE_NAME, COLUMN_NAME
        ORDER BY AVG_HEALTH LIMIT 10
    """)
    st.dataframe(col_health, hide_index=True, use_container_width=True)
    if not col_health.empty:
        worst_col = col_health.iloc[0]
        st.caption(f"Worst column: {worst_col['TABLE_NAME']}.{worst_col['COLUMN_NAME']} — health {worst_col['AVG_HEALTH']}, null rate {worst_col['AVG_NULL_RATE']}, outlier rate {worst_col['AVG_OUTLIER_RATE']}.")

with st.container(border=True):
    st.markdown("**Marketplace Data Freshness**")
    freshness = run_query("""
        SELECT 'NWS Weather Alerts' AS SOURCE, MAX(REPORTED_DATE)::DATE AS LATEST_DATE, COUNT(*) AS ROW_COUNT FROM INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_NWS_WEATHER_ALERTS
        UNION ALL SELECT 'FEMA Disaster Declarations', MAX(DESIGNATED_DATE), COUNT(*) FROM INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_FEMA_DISASTER_DECLARATIONS
        UNION ALL SELECT 'FEMA Flood Claims', MAX(DATE_OF_LOSS), COUNT(*) FROM INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_FEMA_FLOOD_CLAIMS
        UNION ALL SELECT 'BLS CPI Data', MAX(OBSERVATION_DATE), COUNT(*) FROM INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_BLS_CPI_DATA
        UNION ALL SELECT 'FRED Economic Data', MAX(OBSERVATION_DATE), COUNT(*) FROM INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_FRED_ECONOMIC_DATA
    """)
    st.dataframe(freshness, hide_index=True, use_container_width=True)
    if not freshness.empty:
        import datetime
        today = datetime.date.today()
        stale = []
        for _, row in freshness.iterrows():
            if row["LATEST_DATE"] and (today - row["LATEST_DATE"]).days > 30:
                stale.append(row["SOURCE"])
        if stale:
            st.caption(f"Stale data detected: {', '.join(stale)} — last update >30 days ago. Check marketplace share status.")
        else:
            st.caption("All external data sources refreshed within the last 30 days.")
