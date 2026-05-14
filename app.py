"""Streamlit Cloud entrypoint for the Safwa pricing dashboard."""

try:
    # Importing this module renders the Streamlit dashboard.
    import dashboard_pro  # noqa: F401
except Exception as exc:
    import streamlit as st

    st.error("تعذر تشغيل التطبيق. افتح Logs في Streamlit Cloud لمعرفة تفاصيل الخطأ.")
    st.exception(exc)
    raise
