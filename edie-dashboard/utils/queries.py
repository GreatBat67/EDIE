import os
import streamlit as st
import pandas as pd


def get_connection():
    if "conn" not in st.session_state:
        st.session_state.conn = st.connection(
            "snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL")
        )
    return st.session_state.conn


def run_query(sql, ttl=300):
    conn = get_connection()
    return conn.query(sql, ttl=ttl)


def safe_query(sql, ttl=300, fallback_msg="Unable to load data."):
    """Run a query with error handling. Returns (df, error_msg). If ok, error_msg is None."""
    try:
        df = run_query(sql, ttl=ttl)
        return df, None
    except Exception as e:
        return pd.DataFrame(), str(e)[:200]


def val(df, col, default=0):
    """Safely get first row value from a dataframe column."""
    if df is None or df.empty or col not in df.columns:
        return default
    v = df[col].iloc[0]
    return v if v is not None else default


def fmt_currency(v):
    if v is None:
        return "$0"
    try:
        v = float(v)
    except (ValueError, TypeError):
        return "$0"
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:,.1f}M"
    if abs(v) >= 1_000:
        return f"${v / 1_000:,.1f}K"
    return f"${v:,.0f}"


def fmt_pct(v):
    if v is None:
        return "0%"
    return f"{float(v):.1f}%"


def fmt_number(v):
    if v is None:
        return "0"
    return f"{float(v):,.0f}"
