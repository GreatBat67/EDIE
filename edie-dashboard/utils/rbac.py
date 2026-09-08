import streamlit as st

ROLE_PAGE_ACCESS = {
    "ACCOUNTADMIN": ["executive_kpis", "claims_intel", "policy_pricing", "customer_retention", "voice_of_customer", "risk_map", "chatbot_hub", "alerts", "data_quality", "analytics_builder", "research_predict", "document_intake"],
    "EXECUTIVE": ["executive_kpis", "claims_intel", "policy_pricing", "customer_retention", "voice_of_customer", "risk_map", "chatbot_hub", "alerts", "data_quality", "analytics_builder", "research_predict", "document_intake"],
    "CLAIMS_ANALYST": ["claims_intel", "voice_of_customer", "risk_map", "chatbot_hub", "analytics_builder", "research_predict", "document_intake"],
    "UNDERWRITER": ["claims_intel", "policy_pricing", "risk_map", "chatbot_hub", "analytics_builder", "research_predict", "document_intake"],
    "RETENTION_MANAGER": ["customer_retention", "voice_of_customer", "chatbot_hub", "analytics_builder", "research_predict"],
    "AGENCY_MANAGER": ["customer_retention", "policy_pricing", "risk_map", "chatbot_hub", "analytics_builder", "research_predict"],
    "DATA_GOVERNANCE": ["data_quality", "alerts", "chatbot_hub", "analytics_builder", "research_predict"],
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
        st.caption(f"{icon} **Role:** {label}")
        st.caption(f"Session: `{role}`")
