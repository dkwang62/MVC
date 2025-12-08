import streamlit as st
import os
import sys

# Ensure local package imports work on Streamlit Cloud
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Set up base page config (must be first Streamlit command)
st.set_page_config(
    page_title="MVC Tools",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Marriott Vacation Club – internal tools"},
)

from common.ui import setup_page
import calculator
import editor

# Apply shared CSS
setup_page()

def main():
    # --- 1. SESSION STATE FOR NAVIGATION ---
    # We use 'app_phase' to track the current view: 'renter', 'owner', 'editor'
    if "app_phase" not in st.session_state:
        st.session_state.app_phase = "renter"

    # --- 2. SIDEBAR NAVIGATION CONTROLS ---
    with st.sidebar:
        st.header("Navigation")
        
        # STATE: RENTER MODE
        if st.session_state.app_phase == "renter":
            st.info("Currently: **Renter Mode**")
            st.markdown("---")
            if st.button("Go to Owner Mode ➡️", use_container_width=True):
                st.session_state.app_phase = "owner"
                st.rerun()

        # STATE: OWNER MODE
        elif st.session_state.app_phase == "owner":
            if st.button("⬅️ Back to Renter", use_container_width=True):
                st.session_state.app_phase = "renter"
                st.rerun()
            
            st.markdown("---")
            st.info("Currently: **Owner Mode**")
            st.markdown("---")
            
            if st.button("Go to Editor 🛠️", use_container_width=True):
                st.session_state.app_phase = "editor"
                st.rerun()

        # STATE: EDITOR MODE
        elif st.session_state.app_phase == "editor":
            if st.button("⬅️ Back to Calculator", use_container_width=True):
                st.session_state.app_phase = "owner"
                st.rerun()
            st.markdown("---")
            st.info("Currently: **Data Editor**")

    # --- 3. ROUTING ---
    if st.session_state.app_phase == "renter":
        # Pass the forced mode to the calculator
        calculator.run(forced_mode="Renter")
        
    elif st.session_state.app_phase == "owner":
        # Pass the forced mode to the calculator
        calculator.run(forced_mode="Owner")
        
    elif st.session_state.app_phase == "editor":
        editor.run()

if __name__ == "__main__":
    main()
