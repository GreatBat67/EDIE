import streamlit as st
import altair as alt
from utils.queries import run_query

st.header("Analytics Explorer")
st.caption("Pick a domain, perspective, and measure — no table names needed.")

# === DOMAIN CONFIGS ===
DOMAINS = {
    "Claims": {
        "perspectives": {
            "By State": {"group": "c.STATE", "label": "STATE", "join": "JOIN INSURANCE_AI_HUB.ANALYTICS.CUSTOMERS c ON c.CUSTOMER_ID = cl.CUSTOMER_ID"},
            "By Policy Type": {"group": "p.POLICY_TYPE", "label": "POLICY_TYPE", "join": "JOIN INSURANCE_AI_HUB.ANALYTICS.POLICIES p ON p.POLICY_ID = cl.POLICY_ID"},
            "By Cause of Loss": {"group": "cl.CAUSE_OF_LOSS", "label": "CAUSE_OF_LOSS", "join": ""},
            "By Claim Type": {"group": "cl.CLAIM_TYPE", "label": "CLAIM_TYPE", "join": ""},
            "By Fraud Band": {"group": "CASE WHEN cl.FRAUD_SCORE < 20 THEN '1. Low' WHEN cl.FRAUD_SCORE < 50 THEN '2. Medium' WHEN cl.FRAUD_SCORE < 80 THEN '3. High' ELSE '4. Critical' END", "label": "FRAUD_BAND", "join": ""},
            "By Month": {"group": "DATE_TRUNC('month', cl.CLAIM_DATE)::DATE", "label": "MONTH", "join": ""},
            "By Friction Reason": {"group": "cl.FRICTION_REASON", "label": "FRICTION_REASON", "join": ""},
        },
        "measures": {
            "Count": "COUNT(*)",
            "Total Claim Amount": "ROUND(SUM(cl.CLAIM_AMOUNT), 0)",
            "Avg Claim Amount": "ROUND(AVG(cl.CLAIM_AMOUNT), 0)",
            "Avg Fraud Score": "ROUND(AVG(cl.FRAUD_SCORE), 1)",
            "Avg Resolution Days": "ROUND(AVG(cl.RESOLUTION_DAYS), 1)",
            "Max Claim Amount": "ROUND(MAX(cl.CLAIM_AMOUNT), 0)",
        },
        "base": "INSURANCE_AI_HUB.ANALYTICS.CLAIMS cl",
    },
    "Policies": {
        "perspectives": {
            "By Type": {"group": "p.POLICY_TYPE", "label": "POLICY_TYPE", "join": ""},
            "By State": {"group": "p.ISSUING_STATE", "label": "STATE", "join": ""},
            "By Coverage Tier": {"group": "p.COVERAGE_TIER", "label": "COVERAGE_TIER", "join": ""},
            "By Status": {"group": "p.STATUS", "label": "STATUS", "join": ""},
            "By Renewal Status": {"group": "p.RENEWAL_STATUS", "label": "RENEWAL_STATUS", "join": ""},
            "By Month": {"group": "DATE_TRUNC('month', p.EFFECTIVE_DATE)::DATE", "label": "MONTH", "join": ""},
            "By Line of Business": {"group": "p.LINE_OF_BUSINESS", "label": "LOB", "join": ""},
        },
        "measures": {
            "Count": "COUNT(*)",
            "Total Premium": "ROUND(SUM(p.PREMIUM_AMOUNT), 0)",
            "Avg Premium": "ROUND(AVG(p.PREMIUM_AMOUNT), 0)",
            "Avg Coverage": "ROUND(AVG(p.COVERAGE_AMOUNT), 0)",
            "Avg Underwriting Score": "ROUND(AVG(p.UNDERWRITING_SCORE), 1)",
            "Total Expense": "ROUND(SUM(p.EXPENSE_AMOUNT), 0)",
        },
        "base": "INSURANCE_AI_HUB.ANALYTICS.POLICIES p",
    },
    "Customers": {
        "perspectives": {
            "By Risk Tier": {"group": "cu.RISK_TIER", "label": "RISK_TIER", "join": ""},
            "By Segment": {"group": "cu.SEGMENT", "label": "SEGMENT", "join": ""},
            "By State": {"group": "cu.STATE", "label": "STATE", "join": ""},
            "By Credit Band": {"group": "CASE WHEN cu.CREDIT_SCORE < 580 THEN '1. Poor' WHEN cu.CREDIT_SCORE < 670 THEN '2. Fair' WHEN cu.CREDIT_SCORE < 740 THEN '3. Good' WHEN cu.CREDIT_SCORE < 800 THEN '4. Very Good' ELSE '5. Excellent' END", "label": "CREDIT_BAND", "join": ""},
            "By Income Range": {"group": "cu.ANNUAL_INCOME_RANGE", "label": "INCOME_RANGE", "join": ""},
            "By Gender": {"group": "cu.GENDER", "label": "GENDER", "join": ""},
        },
        "measures": {
            "Count": "COUNT(*)",
            "Avg Credit Score": "ROUND(AVG(cu.CREDIT_SCORE), 0)",
            "Min Credit Score": "MIN(cu.CREDIT_SCORE)",
            "Max Credit Score": "MAX(cu.CREDIT_SCORE)",
        },
        "base": "INSURANCE_AI_HUB.ANALYTICS.CUSTOMERS cu",
    },
    "Billing": {
        "perspectives": {
            "By Payment Status": {"group": "b.PAYMENT_STATUS", "label": "PAYMENT_STATUS", "join": ""},
            "By Payment Method": {"group": "b.PAYMENT_METHOD", "label": "PAYMENT_METHOD", "join": ""},
            "By Month": {"group": "DATE_TRUNC('month', b.DUE_DATE)::DATE", "label": "MONTH", "join": ""},
            "By Billing Plan": {"group": "b.BILLING_PLAN", "label": "BILLING_PLAN", "join": ""},
        },
        "measures": {
            "Count": "COUNT(*)",
            "Total Outstanding": "ROUND(SUM(b.OUTSTANDING_BALANCE), 0)",
            "Total Late Fees": "ROUND(SUM(b.LATE_FEE), 0)",
            "Avg Amount Due": "ROUND(AVG(b.AMOUNT_DUE), 0)",
            "Total Amount Paid": "ROUND(SUM(b.AMOUNT_PAID), 0)",
        },
        "base": "INSURANCE_AI_HUB.ANALYTICS.BILLING b",
    },
    "External: Weather": {
        "perspectives": {
            "By State": {"group": "w.STATE", "label": "STATE", "join": ""},
            "By Event Type": {"group": "w.EVENT_TYPE", "label": "EVENT_TYPE", "join": ""},
            "By Severity": {"group": "w.EVENT_SEVERITY", "label": "SEVERITY", "join": ""},
            "By Month": {"group": "DATE_TRUNC('month', w.REPORTED_DATE)::DATE", "label": "MONTH", "join": ""},
        },
        "measures": {
            "Alert Count": "COUNT(*)",
        },
        "base": "INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_NWS_WEATHER_ALERTS w",
        "where": "w.STATE IS NOT NULL AND w.REPORTED_DATE >= '2026-01-01'",
    },
    "External: FEMA": {
        "perspectives": {
            "By State": {"group": "f.STATE", "label": "STATE", "join": ""},
            "By Year": {"group": "YEAR(f.DESIGNATED_DATE)", "label": "YEAR", "join": ""},
        },
        "measures": {
            "Disaster Count": "COUNT(*)",
            "Distinct Disasters": "COUNT(DISTINCT f.DISASTER_ID)",
        },
        "base": "INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_FEMA_DISASTER_DECLARATIONS f",
        "where": "f.STATE IS NOT NULL AND f.DESIGNATED_DATE >= '2020-01-01'",
    },
    "External: Economic": {
        "perspectives": {
            "By Series": {"group": "e.SERIES_ID", "label": "SERIES", "join": ""},
            "By Month": {"group": "e.OBSERVATION_DATE", "label": "MONTH", "join": ""},
        },
        "measures": {
            "Latest Value": "MAX(e.VALUE)",
            "Avg Value": "ROUND(AVG(e.VALUE), 2)",
        },
        "base": "INSURANCE_AI_HUB.EXTERNAL_DATA.LIVE_FRED_ECONOMIC_DATA e",
        "where": "e.OBSERVATION_DATE >= '2022-01-01'",
    },
}

tab1, tab2, tab3 = st.tabs(["Explore", "Compare & Correlate", "My Workspace"])

# ============================================================
# TAB 1: EXPLORE
# ============================================================
with tab1:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        domain = st.selectbox("Domain", list(DOMAINS.keys()))
    cfg = DOMAINS[domain]
    with col2:
        perspective = st.selectbox("Perspective", list(cfg["perspectives"].keys()))
    with col3:
        measure = st.selectbox("Measure", list(cfg["measures"].keys()))
    with col4:
        chart_type = st.selectbox("Chart", ["Bar", "Horizontal Bar", "Line", "Area", "Data Table"])

    persp = cfg["perspectives"][perspective]
    group_expr = persp["group"]
    group_label = persp["label"]
    measure_expr = cfg["measures"][measure]
    join_clause = persp.get("join", "")
    where_clause = cfg.get("where", "1=1")

    sql = (
        f"SELECT {group_expr} AS {group_label}, {measure_expr} AS VALUE "
        f"FROM {cfg['base']} {join_clause} "
        f"WHERE {where_clause} AND {group_expr} IS NOT NULL "
        f"GROUP BY {group_expr} ORDER BY VALUE DESC LIMIT 50"
    )

    try:
        df = run_query(sql)
        if df.empty:
            st.warning("No data returned for this combination.")
        else:
            st.markdown(f"**{domain} — {measure} {perspective}** ({len(df)} groups)")

            if chart_type == "Bar":
                st.bar_chart(df, x=group_label, y="VALUE")
            elif chart_type == "Horizontal Bar":
                st.bar_chart(df, y=group_label, x="VALUE", horizontal=True)
            elif chart_type == "Line":
                st.line_chart(df, x=group_label, y="VALUE")
            elif chart_type == "Area":
                st.area_chart(df, x=group_label, y="VALUE")
            else:
                st.dataframe(df, hide_index=True, use_container_width=True)

            with st.expander("View SQL"):
                st.code(sql, language="sql")
    except Exception as e:
        st.error(f"Query error: {str(e)}")

    # --- HEATMAP: Cross-tab two perspectives ---
    st.divider()
    st.markdown("**Cross-Tab Heatmap** — pick two perspectives for a matrix view")
    h_col1, h_col2, h_col3 = st.columns(3)
    with h_col1:
        h_row = st.selectbox("Rows", list(cfg["perspectives"].keys()), key="hm_row")
    with h_col2:
        h_col_sel = st.selectbox("Columns", [p for p in cfg["perspectives"].keys() if p != h_row], key="hm_col")
    with h_col3:
        h_measure = st.selectbox("Value", list(cfg["measures"].keys()), key="hm_measure")

    if st.button("Generate Heatmap", icon=":material/grid_on:"):
        rp = cfg["perspectives"][h_row]
        cp = cfg["perspectives"][h_col_sel]
        h_measure_expr = cfg["measures"][h_measure]
        joins = " ".join(filter(None, [rp.get("join", ""), cp.get("join", "")]))
        # deduplicate joins
        join_parts = list(dict.fromkeys(joins.split("JOIN ")))
        clean_join = "JOIN ".join(join_parts) if len(join_parts) > 1 else joins

        h_sql = (
            f"SELECT {rp['group']} AS ROW_DIM, {cp['group']} AS COL_DIM, {h_measure_expr} AS VAL "
            f"FROM {cfg['base']} {clean_join} "
            f"WHERE {where_clause} AND {rp['group']} IS NOT NULL AND {cp['group']} IS NOT NULL "
            f"GROUP BY ROW_DIM, COL_DIM ORDER BY ROW_DIM, COL_DIM"
        )
        try:
            hm_df = run_query(h_sql)
            if hm_df.empty:
                st.warning("No data for this cross-tab.")
            else:
                pivot = hm_df.pivot_table(index="ROW_DIM", columns="COL_DIM", values="VAL", fill_value=0)
                st.markdown(f"**{h_measure}: {h_row} × {h_col_sel}**")
                hm_df["VAL"] = hm_df["VAL"].astype(float)
                heatmap = (
                    alt.Chart(hm_df)
                    .mark_rect(cornerRadius=3)
                    .encode(
                        x=alt.X("COL_DIM:N", title=h_col_sel),
                        y=alt.Y("ROW_DIM:N", title=h_row, sort=alt.SortField("VAL", order="descending")),
                        color=alt.Color("VAL:Q", title=h_measure,
                                        scale=alt.Scale(scheme="blues")),
                        tooltip=[
                            alt.Tooltip("ROW_DIM:N", title=h_row),
                            alt.Tooltip("COL_DIM:N", title=h_col_sel),
                            alt.Tooltip("VAL:Q", title=h_measure, format=",.0f")
                        ]
                    )
                    .properties(height=max(len(pivot) * 28, 200))
                )
                text = (
                    alt.Chart(hm_df)
                    .mark_text(fontSize=11, color="white")
                    .encode(
                        x=alt.X("COL_DIM:N"),
                        y=alt.Y("ROW_DIM:N", sort=alt.SortField("VAL", order="descending")),
                        text=alt.Text("VAL:Q", format=",.0f")
                    )
                )
                st.altair_chart(heatmap + text, use_container_width=True)
        except Exception as e:
            st.error(f"Heatmap error: {str(e)}")

# ============================================================
# TAB 2: COMPARE & CORRELATE
# ============================================================
with tab2:
    st.subheader("Cross-Domain Correlation")
    st.caption("Pick two domains to see how they relate — auto-joined by state or time.")

    c1, c2 = st.columns(2)
    with c1:
        d1 = st.selectbox("Domain A", list(DOMAINS.keys()), key="corr_d1")
        m1 = st.selectbox("Measure A", list(DOMAINS[d1]["measures"].keys()), key="corr_m1")
    with c2:
        d2 = st.selectbox("Domain B", [d for d in DOMAINS.keys() if d != d1], key="corr_d2")
        m2 = st.selectbox("Measure B", list(DOMAINS[d2]["measures"].keys()), key="corr_m2")

    join_dim = st.radio("Join on", ["State", "Month"], horizontal=True)

    if st.button("Correlate", type="primary", icon=":material/compare_arrows:"):
        cfg1, cfg2 = DOMAINS[d1], DOMAINS[d2]
        w1, w2 = cfg1.get("where", "1=1"), cfg2.get("where", "1=1")

        if join_dim == "State":
            state_perspectives = {k: v for k, v in cfg1["perspectives"].items() if "State" in k}
            state_perspectives2 = {k: v for k, v in cfg2["perspectives"].items() if "State" in k}
            if not state_perspectives or not state_perspectives2:
                st.warning("One of the domains doesn't have a State perspective. Try joining by Month.")
            else:
                p1 = list(state_perspectives.values())[0]
                p2 = list(state_perspectives2.values())[0]
                sql_a = f"SELECT {p1['group']} AS DIM, {cfg1['measures'][m1]} AS VAL_A FROM {cfg1['base']} {p1.get('join','')} WHERE {w1} AND {p1['group']} IS NOT NULL GROUP BY DIM"
                sql_b = f"SELECT {p2['group']} AS DIM, {cfg2['measures'][m2]} AS VAL_B FROM {cfg2['base']} {p2.get('join','')} WHERE {w2} AND {p2['group']} IS NOT NULL GROUP BY DIM"
                try:
                    col_a = f"{d1}_{m1}".replace(" ", "_").replace(":", "_").upper()
                    col_b = f"{d2}_{m2}".replace(" ", "_").replace(":", "_").upper()
                    corr_sql = f"WITH a AS ({sql_a}), b AS ({sql_b}) SELECT a.DIM AS STATE, a.VAL_A AS {col_a}, b.VAL_B AS {col_b} FROM a JOIN b ON a.DIM = b.DIM ORDER BY a.VAL_A DESC"
                    corr_df = run_query(corr_sql)
                    st.scatter_chart(corr_df, x=col_a, y=col_b)
                    st.dataframe(corr_df, hide_index=True, use_container_width=True)

                    conn = st.session_state.conn
                    summary = corr_df.describe().to_string()
                    interp = conn.query(
                        "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS R",
                        params=["claude-sonnet-4-6",
                                f"You are an insurance analyst. Two metrics were compared by state:\n"
                                f"A: {d1} {m1}\nB: {d2} {m2}\n\nStats:\n{summary}\n\n"
                                f"Give: (1) Whether they correlate, (2) Business interpretation, (3) One action. Be concise."],
                    )
                    with st.container(border=True):
                        st.markdown("**AI Interpretation**")
                        st.info(interp["R"].iloc[0].replace("$", "\\$"))
                except Exception as e:
                    st.error(f"Correlation error: {str(e)}")
        else:
            month_perspectives = {k: v for k, v in cfg1["perspectives"].items() if "Month" in k or "Time" in k}
            month_perspectives2 = {k: v for k, v in cfg2["perspectives"].items() if "Month" in k or "Time" in k}
            if not month_perspectives or not month_perspectives2:
                st.warning("One of the domains doesn't have a time perspective.")
            else:
                p1 = list(month_perspectives.values())[0]
                p2 = list(month_perspectives2.values())[0]
                sql_a = f"SELECT {p1['group']}::DATE AS DIM, {cfg1['measures'][m1]} AS VAL_A FROM {cfg1['base']} {p1.get('join','')} WHERE {w1} GROUP BY DIM"
                sql_b = f"SELECT {p2['group']}::DATE AS DIM, {cfg2['measures'][m2]} AS VAL_B FROM {cfg2['base']} {p2.get('join','')} WHERE {w2} GROUP BY DIM"
                try:
                    col_a = f"{d1}_{m1}".replace(" ", "_").replace(":", "_").upper()
                    col_b = f"{d2}_{m2}".replace(" ", "_").replace(":", "_").upper()
                    corr_sql = f"WITH a AS ({sql_a}), b AS ({sql_b}) SELECT a.DIM AS MONTH, a.VAL_A AS {col_a}, b.VAL_B AS {col_b} FROM a JOIN b ON a.DIM = b.DIM ORDER BY a.DIM"
                    corr_df = run_query(corr_sql)
                    st.line_chart(corr_df, x="MONTH", y=[col_a, col_b])
                    st.dataframe(corr_df, hide_index=True, use_container_width=True)
                except Exception as e:
                    st.error(f"Correlation error: {str(e)}")

# ============================================================
# TAB 3: MY ANALYTICS WORKSPACE
# ============================================================
with tab3:
    st.subheader("My Analytics Workspace")
    st.caption("Build your own analytics panels — pick domain, group-by, measures, and chart type. Add multiple panels to create a custom dashboard.")

    if "workspace_panels" not in st.session_state:
        st.session_state.workspace_panels = []

    with st.container(border=True):
        st.markdown("**Add a Panel**")
        pc1, pc2 = st.columns(2)
        with pc1:
            ws_domain = st.selectbox("Domain", list(DOMAINS.keys()), key="ws_dom")
        ws_cfg = DOMAINS[ws_domain]
        with pc2:
            ws_title = st.text_input("Panel title", value=f"{ws_domain} Analysis", key="ws_title")

        pc3, pc4, pc5 = st.columns(3)
        with pc3:
            ws_row = st.selectbox("Group by (rows)", list(ws_cfg["perspectives"].keys()), key="ws_row")
        with pc4:
            ws_measures = st.multiselect("Measures (pick 1-3)", list(ws_cfg["measures"].keys()),
                                          default=[list(ws_cfg["measures"].keys())[0]], max_selections=3, key="ws_meas")
        with pc5:
            ws_chart = st.selectbox("Chart type", [
                "Bar", "Horizontal Bar", "Stacked Bar", "Line", "Area",
                "Scatter", "Heatmap", "Data Table", "Metric Cards"
            ], key="ws_chart")

        # Secondary group-by for heatmap/stacked
        ws_col_by = None
        if ws_chart in ("Heatmap", "Stacked Bar"):
            other_perspectives = [p for p in ws_cfg["perspectives"].keys() if p != ws_row]
            if other_perspectives:
                ws_col_by = st.selectbox("Secondary group (columns)", other_perspectives, key="ws_col")

        # Top N filter
        ws_top = st.slider("Top N results", 5, 100, 25, step=5, key="ws_top")

        if st.button("Add Panel", type="primary", icon=":material/add_chart:", key="ws_add"):
            if ws_measures:
                st.session_state.workspace_panels.append({
                    "title": ws_title, "domain": ws_domain, "row": ws_row,
                    "measures": ws_measures, "chart": ws_chart,
                    "col_by": ws_col_by, "top": ws_top,
                })
                st.rerun()

    # --- RENDER PANELS ---
    if st.session_state.workspace_panels:
        for idx, panel in enumerate(st.session_state.workspace_panels):
            with st.container(border=True):
                hdr1, hdr2 = st.columns([6, 1])
                with hdr1:
                    st.markdown(f"### {panel['title']}")
                with hdr2:
                    if st.button("X", key=f"del_{idx}", type="tertiary"):
                        st.session_state.workspace_panels.pop(idx)
                        st.rerun()

                p_cfg = DOMAINS[panel["domain"]]
                p_persp = p_cfg["perspectives"][panel["row"]]
                p_where = p_cfg.get("where", "1=1")
                p_join = p_persp.get("join", "")
                grp = p_persp["group"]
                lbl = p_persp["label"]

                try:
                    if panel["chart"] == "Metric Cards":
                        # Show aggregate metrics as cards
                        parts = []
                        for m in panel["measures"]:
                            mexpr = p_cfg["measures"][m]
                            parts.append(f"{mexpr} AS \"{m}\"")
                        m_sql = f"SELECT {', '.join(parts)} FROM {p_cfg['base']} {p_join} WHERE {p_where}"
                        m_df = run_query(m_sql)
                        cols = st.columns(len(panel["measures"]))
                        for i, m in enumerate(panel["measures"]):
                            val = m_df[m].iloc[0]
                            display = f"${val:,.0f}" if val and abs(float(val)) > 100 else f"{val:,.2f}" if val else "N/A"
                            cols[i].metric(m, display, border=True)

                    elif panel["chart"] == "Heatmap" and panel.get("col_by"):
                        cp = p_cfg["perspectives"][panel["col_by"]]
                        c_join = cp.get("join", "")
                        all_joins = " ".join(filter(None, [p_join, c_join]))
                        # dedupe joins
                        seen = set()
                        deduped = []
                        for part in all_joins.split("JOIN "):
                            part = part.strip()
                            if part and part not in seen:
                                seen.add(part)
                                deduped.append(part)
                        clean_j = " JOIN ".join(deduped) if len(deduped) > 1 else all_joins

                        mexpr = p_cfg["measures"][panel["measures"][0]]
                        h_sql = (f"SELECT {grp} AS R, {cp['group']} AS C, {mexpr} AS V "
                                 f"FROM {p_cfg['base']} {clean_j} "
                                 f"WHERE {p_where} AND {grp} IS NOT NULL AND {cp['group']} IS NOT NULL "
                                 f"GROUP BY R, C ORDER BY R LIMIT 500")
                        h_df = run_query(h_sql)
                        if not h_df.empty:
                            pivot = h_df.pivot_table(index="R", columns="C", values="V", fill_value=0)
                            st.dataframe(pivot, use_container_width=True)

                    elif panel["chart"] == "Stacked Bar" and panel.get("col_by"):
                        cp = p_cfg["perspectives"][panel["col_by"]]
                        c_join = cp.get("join", "")
                        all_joins = " ".join(filter(None, [p_join, c_join]))
                        mexpr = p_cfg["measures"][panel["measures"][0]]
                        s_sql = (f"SELECT {grp} AS GRP, {cp['group']} AS STACK, {mexpr} AS VAL "
                                 f"FROM {p_cfg['base']} {all_joins} "
                                 f"WHERE {p_where} AND {grp} IS NOT NULL AND {cp['group']} IS NOT NULL "
                                 f"GROUP BY GRP, STACK ORDER BY VAL DESC LIMIT {panel['top'] * 5}")
                        s_df = run_query(s_sql)
                        if not s_df.empty:
                            pivot = s_df.pivot_table(index="GRP", columns="STACK", values="VAL", fill_value=0)
                            st.bar_chart(pivot)

                    else:
                        # Standard charts: build multi-measure query
                        sel_parts = [f"{grp} AS {lbl}"]
                        y_cols = []
                        for m in panel["measures"]:
                            safe_name = m.replace(" ", "_").upper()
                            sel_parts.append(f"{p_cfg['measures'][m]} AS \"{safe_name}\"")
                            y_cols.append(safe_name)

                        q = (f"SELECT {', '.join(sel_parts)} FROM {p_cfg['base']} {p_join} "
                             f"WHERE {p_where} AND {grp} IS NOT NULL "
                             f"GROUP BY {grp} ORDER BY \"{y_cols[0]}\" DESC LIMIT {panel['top']}")
                        df = run_query(q)

                        if df.empty:
                            st.warning("No data.")
                        elif panel["chart"] == "Bar":
                            st.bar_chart(df, x=lbl, y=y_cols)
                        elif panel["chart"] == "Horizontal Bar":
                            st.bar_chart(df, y=lbl, x=y_cols[0], horizontal=True)
                        elif panel["chart"] == "Line":
                            st.line_chart(df, x=lbl, y=y_cols)
                        elif panel["chart"] == "Area":
                            st.area_chart(df, x=lbl, y=y_cols)
                        elif panel["chart"] == "Scatter" and len(y_cols) >= 2:
                            st.scatter_chart(df, x=y_cols[0], y=y_cols[1])
                        elif panel["chart"] == "Data Table":
                            st.dataframe(df, hide_index=True, use_container_width=True)
                        else:
                            st.bar_chart(df, x=lbl, y=y_cols)

                except Exception as e:
                    st.error(f"Panel error: {str(e)}")

        st.divider()
        if st.button("Clear all panels", type="tertiary", icon=":material/delete_sweep:"):
            st.session_state.workspace_panels = []
            st.rerun()
    else:
        st.info("No panels yet. Configure a panel above and click **Add Panel** to start building your custom dashboard.")
