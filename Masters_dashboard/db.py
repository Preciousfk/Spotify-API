import streamlit as st
import pyodbc
import os

@st.cache_resource(show_spinner=False)
def get_connection():
    cfg = st.secrets["db"]

    conn_str = (
        f"DRIVER={{{cfg['driver']}}};"
        f"SERVER={cfg['server']};"
        f"DATABASE={cfg['database']};"
        f"UID={cfg['username']};"
        f"PWD={cfg['password']};"
        f"Connection Timeout={cfg.get('timeout', 30)};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
    )

    return pyodbc.connect(conn_str)
