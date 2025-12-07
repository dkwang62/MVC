# app.py
import os
import sys

import streamlit as st

# Ensure local package imports work on Streamlit Cloud
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from common.ui import setup_page

# Set up base page config and styling
setup_page()

# --- Navigation Logic ---
# 1. Default to 'calculator' if no state is set
if "active_tool" not in st.session_state:
    st.session_state.active_tool = "calculator"

st.sidebar.markdown("### 🧰 MVC Tools")

if st.session_state.active_tool == "editor":
    # While in Editor, show a back button in sidebar
    with st.sidebar:
        if st.button("⬅️ Back to Calculator", use_container_width=True):
            st.session_state.active_tool = "calculator"
            st.rerun()
    
    import editor
    editor.run()

else:
    # Default: Calculator Mode
    import calculator
    calculator.run()
