import os
import streamlit as st

st.set_page_config(
    page_title="E.D.I.E. — Insurance Control Center",
    page_icon=":material/shield:",
    layout="wide",
)

conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))
st.session_state.conn = conn

from utils.rbac import get_current_role, has_access, render_sidebar_badge, ROLE_LABELS

ALL_PAGES = {
    "executive_kpis": st.Page("app_pages/executive_kpis.py", title="Executive KPIs", icon=":material/monitoring:"),
    "claims_intel": st.Page("app_pages/claims_intel.py", title="Claims Forecasting", icon=":material/assignment:"),
    "policy_pricing": st.Page("app_pages/policy_pricing.py", title="Pricing & Risk", icon=":material/policy:"),
    "customer_retention": st.Page("app_pages/customer_retention.py", title="Retention Rx", icon=":material/group:"),
    "voice_of_customer": st.Page("app_pages/voice_of_customer.py", title="Voice of Customer", icon=":material/record_voice_over:"),
    "risk_map": st.Page("app_pages/risk_map.py", title="Risk Map", icon=":material/map:"),
    "chatbot_hub": st.Page("app_pages/chatbot_hub.py", title="E.D.I.E. Chat", icon=":material/smart_toy:"),
    "analytics_builder": st.Page("app_pages/analytics_builder.py", title="Analytics Explorer", icon=":material/dashboard_customize:"),
    "research_predict": st.Page("app_pages/research_predict.py", title="Research & Predict", icon=":material/science:"),
    "document_intake": st.Page("app_pages/document_intake.py", title="Document Intake", icon=":material/upload_file:"),
    "alerts": st.Page("app_pages/alerts.py", title="Alerts & Monitoring", icon=":material/notifications_active:"),
    "data_quality": st.Page("app_pages/data_quality.py", title="Data Quality", icon=":material/verified:"),
}

role = get_current_role()
visible_pages = {k: v for k, v in ALL_PAGES.items() if has_access(k)}

if not visible_pages:
    st.error(f"Role `{role}` has no dashboard access. Contact your administrator.")
    st.stop()

nav_sections = {
    "Analytics": [],
    "Operations": [],
    "Tools": [],
}

section_map = {
    "executive_kpis": "Analytics",
    "claims_intel": "Analytics",
    "policy_pricing": "Analytics",
    "voice_of_customer": "Analytics",
    "risk_map": "Analytics",
    "customer_retention": "Operations",
    "alerts": "Operations",
    "data_quality": "Operations",
    "document_intake": "Operations",
    "chatbot_hub": "Tools",
    "analytics_builder": "Tools",
    "research_predict": "Tools",
}

for key, page in visible_pages.items():
    section = section_map.get(key, "Tools")
    nav_sections[section].append(page)

nav_sections = {k: v for k, v in nav_sections.items() if v}

page = st.navigation(nav_sections, position="sidebar")
render_sidebar_badge()

with st.sidebar:
    st.divider()
    st.caption("E.D.I.E. v3.0 | Insurance AI Hub")

page.run()
