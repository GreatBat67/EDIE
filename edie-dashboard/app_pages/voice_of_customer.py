import streamlit as st
import pandas as pd
from utils.queries import run_query, safe_query, val

st.header("Voice of Customer")
st.caption("AI-powered sentiment analysis and theme classification on claims notes, survey comments, and friction reasons.")

conn = st.session_state.conn

# --- TOP METRICS ---
sentiment_summary, _ = safe_query("""
    SELECT
        COUNT(*) AS TOTAL_SURVEYS,
        ROUND(AVG(SATISFACTION_SCORE), 1) AS AVG_SATISFACTION,
        ROUND(AVG(NPS_RATING), 1) AS AVG_NPS,
        SUM(CASE WHEN PROMOTER_CATEGORY = 'Promoter' THEN 1 ELSE 0 END) AS PROMOTERS,
        SUM(CASE WHEN PROMOTER_CATEGORY = 'Detractor' THEN 1 ELSE 0 END) AS DETRACTORS,
        SUM(CASE WHEN PROMOTER_CATEGORY = 'Passive' THEN 1 ELSE 0 END) AS PASSIVES
    FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMER_SURVEYS
""")

with st.container(horizontal=True):
    st.metric("Total Surveys", f"{int(val(sentiment_summary, 'TOTAL_SURVEYS')):,}", border=True)
    st.metric("Avg NPS", str(val(sentiment_summary, "AVG_NPS", 0)), border=True)
    st.metric("Avg Satisfaction", str(val(sentiment_summary, "AVG_SATISFACTION", 0)), border=True)
    st.metric("Promoters", f"{int(val(sentiment_summary, 'PROMOTERS')):,}", border=True)
    st.metric("Detractors", f"{int(val(sentiment_summary, 'DETRACTORS')):,}", border=True)

nps = int(val(sentiment_summary, "PROMOTERS")) - int(val(sentiment_summary, "DETRACTORS"))
total = int(val(sentiment_summary, "TOTAL_SURVEYS", 1))
nps_score = round(nps / max(total, 1) * 100, 1)
st.caption(f"Net Promoter Score: {nps_score} — {'strong' if nps_score > 50 else 'needs improvement' if nps_score > 0 else 'critical'} ({int(val(sentiment_summary, 'PROMOTERS'))} promoters vs {int(val(sentiment_summary, 'DETRACTORS'))} detractors).")

tab1, tab2, tab3 = st.tabs([
    ":material/sentiment_satisfied: Sentiment Analysis",
    ":material/category: Theme Classification",
    ":material/summarize: AI Insights"
])

# ============================================================
# TAB 1: SENTIMENT SCORING
# ============================================================
with tab1:
    st.subheader("Sentiment on Survey Comments")

    # NPS distribution (no AI needed)
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**NPS Category Distribution**")
            nps_dist = run_query("""
                SELECT PROMOTER_CATEGORY, COUNT(*) AS CNT
                FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMER_SURVEYS
                GROUP BY PROMOTER_CATEGORY ORDER BY CNT DESC
            """)
            if not nps_dist.empty:
                st.bar_chart(nps_dist, x="PROMOTER_CATEGORY", y="CNT")
                st.caption(f"Promoters: {int(sentiment_summary['PROMOTERS'].iloc[0]):,}, Detractors: {int(sentiment_summary['DETRACTORS'].iloc[0]):,}, Passives: {int(sentiment_summary['PASSIVES'].iloc[0]):,}.")

    with col2:
        with st.container(border=True):
            st.markdown("**Avg Satisfaction by Survey Type**")
            by_type = run_query("""
                SELECT SURVEY_TYPE, ROUND(AVG(SATISFACTION_SCORE), 1) AS AVG_SCORE, COUNT(*) AS CNT
                FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMER_SURVEYS
                GROUP BY SURVEY_TYPE ORDER BY AVG_SCORE
            """)
            if not by_type.empty:
                st.bar_chart(by_type, x="SURVEY_TYPE", y="AVG_SCORE", horizontal=True)
                worst = by_type.iloc[0]
                st.caption(f"Lowest satisfaction: {worst['SURVEY_TYPE']} ({worst['AVG_SCORE']}/10) — investigate process gaps.")

    # AI Sentiment — button triggered
    st.divider()
    st.markdown("**AI Sentiment Scoring** — runs `AI_SENTIMENT` on recent comments")
    if st.button("Run AI Sentiment Analysis", type="primary", icon=":material/psychology:", key="run_sentiment"):
        with st.spinner("Running AI_SENTIMENT on 50 recent comments..."):
            try:
                sentiment_data = run_query("""
                    SELECT CUSTOMER_ID, SURVEY_TYPE, SURVEY_DATE, COMMENTS, NPS_RATING,
                           AI_SENTIMENT(COMMENTS)::FLOAT AS SENTIMENT_SCORE
                    FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMER_SURVEYS
                    WHERE COMMENTS IS NOT NULL AND TRIM(COMMENTS) != ''
                    ORDER BY SURVEY_DATE DESC
                    LIMIT 50
                """)

                if not sentiment_data.empty:
                    sentiment_data["SENTIMENT_BAND"] = pd.cut(
                        sentiment_data["SENTIMENT_SCORE"],
                        bins=[-1.01, -0.3, 0.3, 1.01],
                        labels=["Negative", "Neutral", "Positive"]
                    )
                    dist = sentiment_data["SENTIMENT_BAND"].value_counts().reset_index()
                    dist.columns = ["Sentiment", "Count"]
                    st.bar_chart(dist, x="Sentiment", y="Count")
                    neg_pct = round(len(sentiment_data[sentiment_data["SENTIMENT_SCORE"] < -0.3]) / len(sentiment_data) * 100, 1)
                    st.caption(f"{neg_pct}% of recent comments are negative — review these for service recovery opportunities.")

                    with st.container(border=True):
                        st.markdown("**Most Negative Comments**")
                        neg = sentiment_data.nsmallest(10, "SENTIMENT_SCORE")[["CUSTOMER_ID", "SURVEY_TYPE", "SURVEY_DATE", "COMMENTS", "SENTIMENT_SCORE", "NPS_RATING"]]
                        st.dataframe(neg, hide_index=True, use_container_width=True)
                else:
                    st.info("No comments found to analyze.")
            except Exception as e:
                st.error(f"AI_SENTIMENT error: {str(e)}")

    # Friction reasons (no AI needed)
    st.divider()
    st.subheader("Claims Friction Reasons")
    friction_sent = run_query("""
        SELECT FRICTION_REASON, COUNT(*) AS CLAIM_COUNT,
               ROUND(AVG(CLAIM_AMOUNT), 0) AS AVG_CLAIM,
               ROUND(AVG(RESOLUTION_DAYS), 1) AS AVG_RESOLUTION
        FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS
        WHERE FRICTION_REASON IS NOT NULL
        GROUP BY FRICTION_REASON ORDER BY CLAIM_COUNT DESC
    """)
    if not friction_sent.empty:
        st.bar_chart(friction_sent, x="FRICTION_REASON", y="CLAIM_COUNT")
        top = friction_sent.iloc[0]
        st.caption(f"Top friction: \"{top['FRICTION_REASON']}\" ({int(top['CLAIM_COUNT'])} claims, avg ${int(top['AVG_CLAIM']):,}, {top['AVG_RESOLUTION']} day resolution).")
        st.dataframe(friction_sent, hide_index=True, use_container_width=True)

# ============================================================
# TAB 2: THEME CLASSIFICATION
# ============================================================
with tab2:
    st.subheader("AI Theme Classification")
    st.caption("Click below to run AI_CLASSIFY on recent survey comments — categorizes into 8 insurance themes.")

    if st.button("Run AI Theme Classification", type="primary", icon=":material/category:", key="run_classify"):
        with st.spinner("Running AI_CLASSIFY on 50 recent comments..."):
            try:
                classified = run_query("""
                    WITH raw AS (
                        SELECT
                            CUSTOMER_ID, SURVEY_DATE, COMMENTS, NPS_RATING,
                            AI_CLASSIFY(
                                COMMENTS,
                                ['Claims Speed', 'Premium Pricing', 'Coverage Gaps', 'Agent Service', 'Billing Issues', 'Policy Renewal', 'Communication', 'General Satisfaction']
                            ) AS RESULT
                        FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMER_SURVEYS
                        WHERE COMMENTS IS NOT NULL AND TRIM(COMMENTS) != ''
                        ORDER BY SURVEY_DATE DESC
                        LIMIT 50
                    )
                    SELECT CUSTOMER_ID, SURVEY_DATE, COMMENTS, NPS_RATING,
                           RESULT:label::VARCHAR AS THEME,
                           ROUND(RESULT:score::FLOAT, 2) AS CONFIDENCE
                    FROM raw
                    WHERE RESULT:label IS NOT NULL
                """)

                if not classified.empty and classified["THEME"].notna().any():
                    valid = classified[classified["THEME"].notna()].copy()
                    col1, col2 = st.columns(2)
                    with col1:
                        with st.container(border=True):
                            st.markdown("**Theme Distribution**")
                            theme_dist = valid["THEME"].value_counts().reset_index()
                            theme_dist.columns = ["Theme", "Count"]
                            st.bar_chart(theme_dist, x="Theme", y="Count")
                            if len(theme_dist) > 0:
                                top_theme = theme_dist.iloc[0]
                                st.caption(f"Most common: \"{top_theme['Theme']}\" ({int(top_theme['Count'])} comments).")

                    with col2:
                        with st.container(border=True):
                            st.markdown("**Avg NPS by Theme**")
                            theme_nps = valid.groupby("THEME")["NPS_RATING"].mean().reset_index()
                            theme_nps.columns = ["Theme", "Avg NPS"]
                            theme_nps["Avg NPS"] = theme_nps["Avg NPS"].round(1)
                            theme_nps = theme_nps.sort_values("Avg NPS")
                            st.bar_chart(theme_nps, x="Theme", y="Avg NPS", horizontal=True)
                            if len(theme_nps) > 0:
                                worst_theme = theme_nps.iloc[0]
                                st.caption(f"Lowest NPS: \"{worst_theme['Theme']}\" (avg {worst_theme['Avg NPS']}) — address this first.")

                    with st.container(border=True):
                        st.markdown("**Classified Comments**")
                        st.dataframe(valid, hide_index=True, use_container_width=True)
                else:
                    st.info("No comments could be classified. AI_CLASSIFY returned no results.")
            except Exception as e:
                st.error(f"AI_CLASSIFY error: {str(e)}")

# ============================================================
# TAB 3: AI AGGREGATED INSIGHTS
# ============================================================
with tab3:
    st.subheader("AI-Generated Insights")
    st.caption("Uses AI_AGG to summarize patterns across all survey feedback.")

    insight_type = st.selectbox("Generate insight for:", [
        "All recent survey comments",
        "Negative feedback only (Detractors)",
        "Claims friction reasons",
        "High-value customer feedback",
    ])

    if st.button("Generate AI Insight", type="primary", icon=":material/auto_awesome:"):
        with st.spinner("AI is analyzing patterns across all rows..."):
            try:
                if insight_type == "All recent survey comments":
                    insight = run_query("""
                        SELECT AI_AGG(COMMENTS,
                            'Summarize the top 5 themes and actionable insights from these insurance customer survey comments. Highlight the most critical issues and recommend specific improvements.'
                        ) AS INSIGHT
                        FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMER_SURVEYS
                        WHERE COMMENTS IS NOT NULL AND TRIM(COMMENTS) != ''
                    """)
                elif insight_type == "Negative feedback only (Detractors)":
                    insight = run_query("""
                        SELECT AI_AGG(COMMENTS,
                            'Analyze these insurance customer complaints from detractors. What are the root causes of dissatisfaction? Recommend 3 specific operational changes to improve retention.'
                        ) AS INSIGHT
                        FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMER_SURVEYS
                        WHERE PROMOTER_CATEGORY = 'Detractor' AND COMMENTS IS NOT NULL
                    """)
                elif insight_type == "Claims friction reasons":
                    insight = run_query("""
                        SELECT AI_AGG(FRICTION_REASON,
                            'Analyze these insurance claims friction reasons. Identify the top 3 systemic issues causing delays and recommend process improvements for each.'
                        ) AS INSIGHT
                        FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS
                        WHERE FRICTION_REASON IS NOT NULL
                    """)
                else:
                    insight = run_query("""
                        SELECT AI_AGG(cs.COMMENTS,
                            'Analyze survey feedback from high-value insurance customers (Preferred/HighNetWorth). What matters most to them? How can we improve their experience to prevent churn?'
                        ) AS INSIGHT
                        FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMER_SURVEYS cs
                        JOIN INSURANCE_AI_HUB.ANALYTICS.CUSTOMERS c ON cs.CUSTOMER_ID = c.CUSTOMER_ID
                        WHERE c.SEGMENT IN ('Preferred', 'HighNetWorth') AND cs.COMMENTS IS NOT NULL
                    """)

                if not insight.empty and insight["INSIGHT"].iloc[0]:
                    with st.container(border=True):
                        st.markdown("**AI Analysis**")
                        st.info(insight["INSIGHT"].iloc[0])
                else:
                    st.warning("No data available for this insight type.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
