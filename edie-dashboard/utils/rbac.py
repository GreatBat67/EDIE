import streamlit as st

ROLE_PAGE_ACCESS = {
    "ACCOUNTADMIN": ["executive_kpis", "claims_intel", "policy_pricing", "customer_retention", "voice_of_customer", "risk_map", "chatbot_hub", "alerts", "data_quality", "analytics_builder", "ai_research", "table_forecaster", "what_if", "document_intake"],
    "EXECUTIVE": ["executive_kpis", "claims_intel", "policy_pricing", "customer_retention", "voice_of_customer", "risk_map", "chatbot_hub", "alerts", "data_quality", "analytics_builder", "ai_research", "table_forecaster", "what_if", "document_intake"],
    "CLAIMS_ANALYST": ["claims_intel", "voice_of_customer", "risk_map", "chatbot_hub", "analytics_builder", "ai_research", "table_forecaster", "what_if", "document_intake"],
    "UNDERWRITER": ["claims_intel", "policy_pricing", "risk_map", "chatbot_hub", "analytics_builder", "ai_research", "table_forecaster", "what_if", "document_intake"],
    "RETENTION_MANAGER": ["customer_retention", "voice_of_customer", "chatbot_hub", "analytics_builder", "ai_research", "table_forecaster", "what_if"],
    "AGENCY_MANAGER": ["customer_retention", "policy_pricing", "risk_map", "chatbot_hub", "analytics_builder", "ai_research", "table_forecaster", "what_if"],
    "DATA_GOVERNANCE": ["data_quality", "alerts", "chatbot_hub", "analytics_builder", "ai_research", "table_forecaster", "what_if"],
}

ROLE_LABELS = {
    "ACCOUNTADMIN": ("Admin", ":material/shield:"),
    "EXECUTIVE": ("Executive", ":material/workspace_premium:"),
    "CLAIMS_ANALYST": ("Claims Analyst", ":material/assignment:"),
    "UNDERWRITER": ("Underwriter", ":material/policy:"),
    "RETENTION_MANAGER": ("Retention Mgr", ":material/group:"),
    "AGENCY_MANAGER": ("Agency Mgr", ":material/storefront:"),
    "DATA_GOVERNANCE": ("Data Gov", ":material/verified_user:"),
}


def get_current_role():
    if "user_role" not in st.session_state:
        conn = st.session_state.get("conn")
        if conn:
            row = conn.query("SELECT CURRENT_ROLE() AS R")
            st.session_state.user_role = row["R"].iloc[0]
        else:
            st.session_state.user_role = "ACCOUNTADMIN"
    return st.session_state.user_role


def has_access(page_key):
    role = get_current_role()
    allowed = ROLE_PAGE_ACCESS.get(role, [])
    return page_key in allowed


def render_sidebar_badge():
    role = get_current_role()
    label, icon = ROLE_LABELS.get(role, (role, ":material/person:"))
    with st.sidebar:
        st.divider()
        st.markdown(f"""
<div style="background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.2); border-radius: 8px; padding: 8px 12px; margin-top: 4px;">
    <div style="font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.1em; color: #10B981; font-weight: 700; margin-bottom: 4px;">Session Role</div>
    <div style="font-size: 0.9rem; font-weight: 600; color: #E4E4E7;">{label}</div>
    <div style="font-size: 0.7rem; color: #71717A; margin-top: 2px; font-family: monospace;">{role}</div>
</div>
""", unsafe_allow_html=True)
