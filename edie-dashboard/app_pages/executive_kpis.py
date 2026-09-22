import streamlit as st
import altair as alt
import pandas as pd
import datetime
from utils.queries import run_query, fmt_currency, fmt_pct, fmt_number

st.markdown("""
<div class="edie-hero-banner">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h2 style="margin: 0; color: #FFFFFF; font-weight: 700;">Executive Performance Cockpit</h2>
            <p style="margin: 4px 0 0 0; color: #94A3B8; font-size: 0.95rem;">Apex National P&C — Portfolio & Underwriting Performance at a Glance</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- GLOBAL TIME PERIOD FILTER ---
time_period = st.pills("Time Period", ["YTD", "QTD", "MTD"], default="YTD", key="exec_time_period")

now = datetime.date.today()
if time_period == "MTD":
    period_start = now.replace(day=1)
elif time_period == "QTD":
    q_month = ((now.month - 1) // 3) * 3 + 1
    period_start = now.replace(month=q_month, day=1)
else:
    period_start = now.replace(month=1, day=1)

period_label = f"{period_start.strftime('%b %d')} — {now.strftime('%b %d, %Y')}"
st.caption(f"Showing: **{time_period}** ({period_label})")

# --- TOP KPIs (5 strict) ---
kpis = run_query(f"""
    SELECT
        COUNT(DISTINCT p.POLICY_ID) AS TOTAL_POLICIES,
        ROUND(SUM(p.PREMIUM_AMOUNT), 0) AS WRITTEN_PREMIUM,
        ROUND(SUM(p.PREMIUM_AMOUNT) * 0.92, 0) AS EARNED_PREMIUM,
        ROUND(SUM(cl.CLAIM_AMOUNT), 0) AS INCURRED_CLAIMS,
        ROUND(SUM(cl.CLAIM_AMOUNT) / NULLIF(SUM(p.PREMIUM_AMOUNT) * 0.92, 0) * 100, 1) AS LOSS_RATIO
    FROM INSURANCE_AI_HUB.ANALYTICS.POLICIES p
    LEFT JOIN INSURANCE_AI_HUB.ANALYTICS.CLAIMS cl
        ON cl.POLICY_ID = p.POLICY_ID
        AND cl.CLAIM_DATE >= '{period_start}'
    WHERE p.EFFECTIVE_DATE <= '{now}'
""")

import pandas as _pd
def _safe(df, col, default=0):
    if df.empty or col not in df.columns or _pd.isna(df[col].iloc[0]):
        return default
    return df[col].iloc[0]

_policies = int(_safe(kpis, "TOTAL_POLICIES"))
_written = float(_safe(kpis, "WRITTEN_PREMIUM"))
_earned = float(_safe(kpis, "EARNED_PREMIUM"))
_incurred = float(_safe(kpis, "INCURRED_CLAIMS"))
_lr = float(_safe(kpis, "LOSS_RATIO"))

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Active Policies", fmt_number(_policies), delta=time_period)
col2.metric("Written Premium", fmt_currency(_written), delta=time_period)
col3.metric("Earned Premium", fmt_currency(_earned), delta="92% earn rate")
col4.metric("Incurred Claims", fmt_currency(_incurred), delta=f"{time_period} period")
col5.metric("Loss Ratio", fmt_pct(_lr),
            delta="Healthy" if _lr < 60 else "Elevated" if _lr < 75 else "Critical",
            delta_color="normal" if _lr < 60 else "off" if _lr < 75 else "inverse")

st.divider()

# --- CHART ROW 1: Premium vs Claims Trend + Actual vs Expected Loss Ratio ---
c1, c2 = st.columns(2)

with c1:
    with st.container(border=True):
        st.markdown("**Monthly Premium vs Incurred Claims**")
        trend = run_query(f"""
            SELECT DATE_TRUNC('month', p.EFFECTIVE_DATE)::DATE AS MONTH,
                   ROUND(SUM(p.PREMIUM_AMOUNT), 0) AS WRITTEN_PREMIUM,
                   ROUND(SUM(cl.CLAIM_AMOUNT), 0) AS INCURRED_CLAIMS
            FROM INSURANCE_AI_HUB.ANALYTICS.POLICIES p
            LEFT JOIN INSURANCE_AI_HUB.ANALYTICS.CLAIMS cl
                ON cl.POLICY_ID = p.POLICY_ID
                AND DATE_TRUNC('month', cl.CLAIM_DATE) = DATE_TRUNC('month', p.EFFECTIVE_DATE)
            WHERE p.EFFECTIVE_DATE >= DATEADD('month', -12, CURRENT_DATE())
            GROUP BY 1 ORDER BY 1
        """)
        if not trend.empty:
            trend_melted = trend.melt(id_vars=["MONTH"], value_vars=["WRITTEN_PREMIUM", "INCURRED_CLAIMS"],
                                      var_name="Metric", value_name="Amount")
            trend_melted["Metric"] = trend_melted["Metric"].replace({
                "WRITTEN_PREMIUM": "Written Premium",
                "INCURRED_CLAIMS": "Incurred Claims"
            })
            chart = (
                alt.Chart(trend_melted)
                .mark_line(strokeWidth=2.5, point=alt.OverlayMarkDef(size=40))
                .encode(
                    x=alt.X("MONTH:T", title="Month", axis=alt.Axis(format="%b %y")),
                    y=alt.Y("Amount:Q", title="Amount ($)", axis=alt.Axis(format="$,.0f")),
                    color=alt.Color("Metric:N", scale=alt.Scale(
                        domain=["Written Premium", "Incurred Claims"],
                        range=["#10B981", "#F87171"]
                    )),
                    tooltip=[
                        alt.Tooltip("MONTH:T", title="Month", format="%B %Y"),
                        alt.Tooltip("Metric:N", title="Metric"),
                        alt.Tooltip("Amount:Q", title="Amount", format="$,.0f")
                    ]
                )
                .properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)

with c2:
    with st.container(border=True):
        st.markdown("**Actual vs Expected Loss Ratio**")
        anomalies = run_query("SELECT MONTH, ACTUAL_LOSS_RATIO, EXPECTED_LOSS_RATIO, IS_ANOMALY FROM INSURANCE_AI_HUB.ANALYTICS.LOSS_RATIO_ANOMALIES ORDER BY MONTH")
        if not anomalies.empty:
            anom_melted = anomalies.melt(id_vars=["MONTH", "IS_ANOMALY"],
                                         value_vars=["ACTUAL_LOSS_RATIO", "EXPECTED_LOSS_RATIO"],
                                         var_name="Type", value_name="Loss Ratio")
            anom_melted["Type"] = anom_melted["Type"].replace({
                "ACTUAL_LOSS_RATIO": "Actual",
                "EXPECTED_LOSS_RATIO": "Expected"
            })
            lines = (
                alt.Chart(anom_melted)
                .mark_line(strokeWidth=2.5, point=alt.OverlayMarkDef(size=40))
                .encode(
                    x=alt.X("MONTH:T", title="Month", axis=alt.Axis(format="%b %y")),
                    y=alt.Y("Loss Ratio:Q", title="Loss Ratio (%)", scale=alt.Scale(zero=False)),
                    color=alt.Color("Type:N", scale=alt.Scale(
                        domain=["Actual", "Expected"],
                        range=["#FBBF24", "#94A3B8"]
                    )),
                    strokeDash=alt.StrokeDash("Type:N", scale=alt.Scale(
                        domain=["Actual", "Expected"],
                        range=[[1, 0], [5, 5]]
                    )),
                    tooltip=[
                        alt.Tooltip("MONTH:T", title="Month", format="%B %Y"),
                        alt.Tooltip("Type:N"),
                        alt.Tooltip("Loss Ratio:Q", format=".1f")
                    ]
                )
                .properties(height=300)
            )
            # Red dots for anomalies
            anomaly_points = anomalies[anomalies["IS_ANOMALY"] == True]
            if not anomaly_points.empty:
                dots = (
                    alt.Chart(anomaly_points)
                    .mark_circle(size=120, color="#EF4444")
                    .encode(
                        x=alt.X("MONTH:T"),
                        y=alt.Y("ACTUAL_LOSS_RATIO:Q"),
                        tooltip=[
                            alt.Tooltip("MONTH:T", title="Month", format="%B %Y"),
                            alt.Tooltip("ACTUAL_LOSS_RATIO:Q", title="Actual", format=".1f"),
                            alt.Tooltip("EXPECTED_LOSS_RATIO:Q", title="Expected", format=".1f")
                        ]
                    )
                )
                st.altair_chart(lines + dots, use_container_width=True)
            else:
                st.altair_chart(lines, use_container_width=True)
                st.caption("No anomalies detected — loss ratios tracking within expected bounds.")

# --- CHART ROW 2: Loss Ratio by Type + Portfolio Mix ---
c3, c4 = st.columns(2)

with c3:
    with st.container(border=True):
        st.markdown("**Loss Ratio by Line of Business**")
        lr_by_type = run_query(f"""
            SELECT p.POLICY_TYPE,
                   ROUND(SUM(cl.CLAIM_AMOUNT) / NULLIF(SUM(p.PREMIUM_AMOUNT), 0) * 100, 1) AS LOSS_RATIO
            FROM INSURANCE_AI_HUB.ANALYTICS.POLICIES p
            LEFT JOIN INSURANCE_AI_HUB.ANALYTICS.CLAIMS cl
                ON cl.POLICY_ID = p.POLICY_ID
                AND cl.CLAIM_DATE >= '{period_start}'
            GROUP BY p.POLICY_TYPE ORDER BY LOSS_RATIO DESC
        """)
        if not lr_by_type.empty:
            lr_by_type["LOSS_RATIO"] = lr_by_type["LOSS_RATIO"].astype(float)
            lr_by_type["STATUS"] = lr_by_type["LOSS_RATIO"].apply(
                lambda x: "Critical (>100%)" if x > 100 else "Elevated (70-100%)" if x > 70 else "Healthy (<70%)"
            )
            bar_chart = (
                alt.Chart(lr_by_type)
                .mark_bar(cornerRadiusEnd=4)
                .encode(
                    x=alt.X("LOSS_RATIO:Q", title="Loss Ratio (%)", scale=alt.Scale(domain=[0, max(lr_by_type["LOSS_RATIO"].max() * 1.1, 100)])),
                    y=alt.Y("POLICY_TYPE:N", title="", sort="-x"),
                    color=alt.Color("STATUS:N", scale=alt.Scale(
                        domain=["Healthy (<70%)", "Elevated (70-100%)", "Critical (>100%)"],
                        range=["#34D399", "#FBBF24", "#EF4444"]
                    ), title="Status"),
                    tooltip=[
                        alt.Tooltip("POLICY_TYPE:N", title="Line"),
                        alt.Tooltip("LOSS_RATIO:Q", title="Loss Ratio", format=".1f")
                    ]
                )
                .properties(height=300)
            )
            # Reference line at 100%
            rule = alt.Chart(pd.DataFrame({"x": [100]})).mark_rule(
                strokeDash=[4, 4], color="#94A3B8", strokeWidth=1.5
            ).encode(x="x:Q")
            st.altair_chart(bar_chart + rule, use_container_width=True)

with c4:
    with st.container(border=True):
        st.markdown("**Portfolio Mix — Premium by Line of Business**")
        mix = run_query("""
            SELECT POLICY_TYPE,
                   ROUND(SUM(PREMIUM_AMOUNT), 0) AS PREMIUM
            FROM INSURANCE_AI_HUB.ANALYTICS.POLICIES
            WHERE STATUS IN ('Active', 'InForce', 'Renewed')
            GROUP BY POLICY_TYPE ORDER BY PREMIUM DESC
        """)
        if not mix.empty:
            mix["PREMIUM"] = mix["PREMIUM"].astype(float)
            total = mix["PREMIUM"].sum()
            mix["PCT"] = round(mix["PREMIUM"] / total * 100, 1)
            mix["LABEL"] = mix["POLICY_TYPE"] + " (" + mix["PCT"].astype(str) + "%)"
            donut = (
                alt.Chart(mix)
                .mark_arc(innerRadius=60, outerRadius=120, cornerRadius=3)
                .encode(
                    theta=alt.Theta("PREMIUM:Q"),
                    color=alt.Color("POLICY_TYPE:N", title="Line of Business",
                                    scale=alt.Scale(scheme="tableau10")),
                    tooltip=[
                        alt.Tooltip("POLICY_TYPE:N", title="Line"),
                        alt.Tooltip("PREMIUM:Q", title="Premium", format="$,.0f"),
                        alt.Tooltip("PCT:Q", title="Share", format=".1f")
                    ]
                )
                .properties(height=300)
            )
            st.altair_chart(donut, use_container_width=True)

# --- ONE-CLICK EXECUTIVE BRIEF ---
st.divider()
if st.button("Generate Executive Brief", icon=":material/auto_awesome:", type="secondary"):
    with st.spinner("Generating your board-ready executive brief..."):
        conn = st.session_state.conn
        brief_prompt = (
            f"You are a P&C insurance CEO's briefing assistant. Generate a concise executive brief for the {time_period} period ({period_label}).\n\n"
            f"KPIs:\n"
            f"- Active Policies: {_policies:,}\n"
            f"- Written Premium: ${_written:,.0f}\n"
            f"- Earned Premium: ${_earned:,.0f}\n"
            f"- Incurred Claims: ${_incurred:,.0f}\n"
            f"- Loss Ratio: {_lr}%\n\n"
            f"Write a 3-4 paragraph executive brief: (1) Portfolio health and premium trajectory, "
            f"(2) Underwriting performance and loss ratio assessment, (3) Strategic priorities for the next quarter. "
            f"Be direct, specific with numbers, and frame constructively. This is for a board presentation."
        )
        result = conn.query(
            "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESPONSE",
            params=["claude-sonnet-4-6", brief_prompt],
        )
        with st.container(border=True):
            st.markdown("### Executive Brief")
            st.markdown(result["RESPONSE"].iloc[0].replace("$", "\\$"))
