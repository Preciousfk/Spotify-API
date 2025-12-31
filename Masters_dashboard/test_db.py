import streamlit as st
from db import get_connection

st.write("Testing DB connection...")

conn = get_connection()
st.success("✅ DB connected successfully!")
