import os
import streamlit as st

st.set_page_config(
    page_title="E.D.I.E. — Insurance Enterprise Cockpit",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)



# Global Custom CSS — Soft Dark Theme (Zinc + Emerald)
st.markdown("""
<style>
    /* Full width & clean container */
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 95% !important;
    }
    
    /* Top Banner Gradient — Emerald on dark zinc */
    .edie-hero-banner {
        background: linear-gradient(135deg, #18181B 0%, #27272A 40%, #065F46 100%);
        padding: 1rem 1.4rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1.2rem;
        border: 1px solid #3F3F46;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    
    /* Metric Cards — Lifted zinc surface */
    div[data-testid="stMetric"] {
        background: #3F3F46 !important;
        border: 1px solid #52525B !important;
        padding: 8px 12px !important;
        border-radius: 8px !important;
        min-height: 70px !important;
    }
    div[data-testid="stMetric"] label {
        font-size: 0.8rem !important;
        color: #A1A1AA !important;
        margin-bottom: 2px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        color: #FAFAFA !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricDelta"] {
        font-size: 0.75rem !important;
    }

    /* Chat Response Text */
    .stChatMessage p {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
        letter-spacing: 0.01em !important;
        word-spacing: normal !important;
    }
    
    /* Trust Bar — Emerald tint */
    .edie-trust-strip {
        display: flex;
        align-items: center;
        gap: 12px;
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.25);
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 0.85rem;
        color: #D4D4D8;
        margin-top: 8px;
        margin-bottom: 8px;
    }

    /* Buttons — Emerald accent */
    button[data-testid="stBaseButton-secondary"] {
        border-color: #10B981 !important;
        color: #10B981 !important;
    }
    button[data-testid="stBaseButton-secondary"]:hover {
        background: rgba(16, 185, 129, 0.1) !important;
        border-color: #34D399 !important;
    }

    /* Pills / segmented controls */
    div[data-testid="stSegmentedControl"] button[aria-checked="true"] {
        background: #10B981 !important;
        color: #18181B !important;
    }

    /* Container borders — zinc */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #52525B !important;
    }

    /* ============================================ */
    /* FUTURISTIC SIDEBAR                           */
    /* ============================================ */

    /* Sidebar gradient background */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #18181B 0%, #1F1F23 40%, #1A1A2E 100%) !important;
        border-right: 1px solid rgba(16, 185, 129, 0.1) !important;
    }

    /* Section headers — uppercase, letter-spaced, accent bar */
    section[data-testid="stSidebar"] h2 {
        font-size: 0.6rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.15em !important;
        color: #10B981 !important;
        font-weight: 700 !important;
        padding-left: 10px !important;
        border-left: 2px solid #10B981 !important;
        margin-top: 0.8rem !important;
        margin-bottom: 0.15rem !important;
    }

    /* Navigation links — sleek with hover glow */
    section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"] {
        border-radius: 6px !important;
        margin: 0px 4px !important;
        padding: 4px 10px !important;
        transition: all 0.2s ease !important;
        border: 1px solid transparent !important;
        min-height: unset !important;
    }
    section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"]:hover {
        background: rgba(16, 185, 129, 0.08) !important;
        border: 1px solid rgba(16, 185, 129, 0.15) !important;
        transform: translateX(2px);
    }

    /* Active page — emerald glow */
    section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"][aria-current="page"] {
        background: rgba(16, 185, 129, 0.12) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        box-shadow: 0 0 12px rgba(16, 185, 129, 0.15), inset 0 0 8px rgba(16, 185, 129, 0.05) !important;
    }
    section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"][aria-current="page"] span {
        color: #34D399 !important;
        font-weight: 600 !important;
    }

    /* Nav link text color */
    section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"] span {
        color: #A1A1AA !important;
        font-size: 0.85rem !important;
        transition: color 0.2s ease !important;
    }
    section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"]:hover span {
        color: #E4E4E7 !important;
    }

    /* Material icons in sidebar — emerald tint */
    section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"] span[data-testid="stIconMaterial"] {
        color: #10B981 !important;
        opacity: 0.7;
        transition: opacity 0.2s ease !important;
    }
    section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"]:hover span[data-testid="stIconMaterial"],
    section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"][aria-current="page"] span[data-testid="stIconMaterial"] {
        opacity: 1;
    }

    /* Sidebar captions — muted */
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown span,
    section[data-testid="stSidebar"] .stCaption {
        color: #71717A !important;
    }

    /* Sidebar divider — subtle emerald */
    section[data-testid="stSidebar"] hr {
        border-color: rgba(16, 185, 129, 0.12) !important;
    }
</style>
""", unsafe_allow_html=True)

conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))
st.session_state.conn = conn

from utils.rbac import get_current_role, has_access, render_sidebar_badge, ROLE_LABELS

ALL_PAGES = {
    "chatbot_hub": st.Page("app_pages/chatbot_hub.py", title="E.D.I.E. Chat", icon=":material/smart_toy:"),
    "executive_kpis": st.Page("app_pages/executive_kpis.py", title="Executive KPI Cockpit", icon=":material/monitoring:"),
    "claims_intel": st.Page("app_pages/claims_intel.py", title="Claims Intelligence", icon=":material/assignment:"),
    "policy_pricing": st.Page("app_pages/policy_pricing.py", title="Pricing & Adequacy", icon=":material/policy:"),
    "risk_map": st.Page("app_pages/risk_map.py", title="Exposure Risk Map", icon=":material/map:"),
    "customer_retention": st.Page("app_pages/customer_retention.py", title="Retention & Churn Rx", icon=":material/group:"),
    "voice_of_customer": st.Page("app_pages/voice_of_customer.py", title="Voice of Customer", icon=":material/record_voice_over:"),
    "analytics_builder": st.Page("app_pages/analytics_builder.py", title="Analytics Builder", icon=":material/dashboard_customize:"),
    "ai_research": st.Page("app_pages/ai_research.py", title="AI Research Assistant", icon=":material/science:"),
    "table_forecaster": st.Page("app_pages/table_forecaster.py", title="Forecasting Assistant", icon=":material/trending_up:"),
    "what_if": st.Page("app_pages/what_if.py", title="What-If Simulator", icon=":material/calculate:"),
    "document_intake": st.Page("app_pages/document_intake.py", title="Document Intake", icon=":material/upload_file:"),
    "alerts": st.Page("app_pages/alerts.py", title="Alerts & Monitoring", icon=":material/notifications_active:"),
    "data_quality": st.Page("app_pages/data_quality.py", title="Data Quality & Trust", icon=":material/verified:"),
}

role = get_current_role()
visible_pages = {k: v for k, v in ALL_PAGES.items() if has_access(k)}

if not visible_pages:
    st.error(f"Role `{role}` has no dashboard access. Contact your administrator.")
    st.stop()

nav_sections = {
    "E.D.I.E. Assistant": [],
    "Intelligent Assistants": [],
    "Customer Intelligence": [],
    "Data Operations": [],
    "Risk & Underwriting": [],
    "Executive Cockpit": [],
}

section_map = {
    "chatbot_hub": "E.D.I.E. Assistant",
    "analytics_builder": "Intelligent Assistants",
    "ai_research": "Intelligent Assistants",
    "table_forecaster": "Intelligent Assistants",
    "what_if": "Intelligent Assistants",
    "customer_retention": "Customer Intelligence",
    "voice_of_customer": "Customer Intelligence",
    "document_intake": "Data Operations",
    "alerts": "Data Operations",
    "data_quality": "Data Operations",
    "claims_intel": "Risk & Underwriting",
    "policy_pricing": "Risk & Underwriting",
    "risk_map": "Risk & Underwriting",
    "executive_kpis": "Executive Cockpit",
}

for key, page in visible_pages.items():
    section = section_map.get(key, "Intelligent Assistants")
    nav_sections[section].append(page)

nav_sections = {k: v for k, v in nav_sections.items() if v}

page = st.navigation(nav_sections, position="sidebar")
render_sidebar_badge()

with st.sidebar:
    st.divider()
    st.markdown("""
<div style="text-align: center; padding: 4px 0;">
    <span style="font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.12em; color: #52525B;">E.D.I.E. v3.1</span>
    <br>
    <span style="font-size: 0.6rem; color: #3F3F46;">Insurance AI Hub · Apex National P&C</span>
</div>
""", unsafe_allow_html=True)

page.run()
