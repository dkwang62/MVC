import streamlit as st
import math
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import traceback
from collections import defaultdict
import uuid

# Load data.json
with open("data.json", "r") as f:
    data = json.load(f)

# Define constants
room_view_legend = {
    "GV": "Garden",
    "OV": "Ocean View",
    "OF": "Oceanfront",
    "S": "Standard",
    "IS": "Island Side",
    "PS": "Pool Low Flrs",
    "PSH": "Pool High Flrs",
    "UF": "Gulf Front",
    "UV": "Gulf View",
    "US": "Gulf Side",
    "PH": "Penthouse",
    "PHGV": "Penthouse Garden",
    "PHOV": "Penthouse Ocean View",
    "PHOF": "Penthouse Ocean Front",
    "IV": "Island",
    "MG": "Garden",
    "PHMA": "Penthouse Mountain",
    "PHMK": "Penthouse Ocean",
    "PHUF": "Penthouse Gulf Front",
    "AP_Studio_MA": "AP Studio Mountain",
    "AP_1BR_MA": "AP 1BR Mountain",
    "AP_2BR_MA": "AP 2BR Mountain",
    "AP_2BR_MK": "AP 2BR Ocean",
    "LO": "Lock-Off",
    "CV": "City",
    "LV": "Lagoon",
    "PV": "Pool",
    "OS": "Oceanside",
    "K": "King",
    "DB": "Double Bed",
    "MV": "Mountain",
    "MA": "Mountain",
    "MK": "Ocean"
}
season_blocks = data.get("season_blocks", {})
reference_points = data.get("reference_points", {})
holiday_weeks = data.get("holiday_weeks", {})

# Initialize session state
if "debug_messages" not in st.session_state:
    st.session_state.debug_messages = []
if "data_cache" not in st.session_state:
    st.session_state.data_cache = {}
if "allow_renter_modifications" not in st.session_state:
    st.session_state.allow_renter_modifications = False  # Default to disallow

# Helper functions
def get_display_room_type(room_key):
    if room_key in room_view_legend:
        return room_view_legend[room_key]
    parts = room_key.split()
    if not parts:
        return room_key
    if room_key.startswith("AP_"):
        if room_key == "AP_Studio_MA":
            return "AP Studio Mountain"
        elif room_key == "AP_1BR_MA":
            return "AP 1BR Mountain"
        elif room_key == "AP_2BR_MA":
            return "AP 2BR Mountain"
        elif room_key == "AP_2BR_MK":
            return "AP 2BR Ocean"
    view = parts[-1]
    if len(parts) > 1 and view in room_view_legend:
        view_display = room_view_legend[view]
        return f"{parts[0]} {view_display}"
    if room_key in ["2BR", "1BR", "3BR"]:
        return room_key
    return room_key

def get_internal_room_key(display_name):
    reverse_legend = {v: k for k, v in room_view_legend.items()}
    if display_name in reverse_legend:
        return reverse_legend[display_name]
    if display_name.startswith("AP "):
        if display_name == "AP Studio Mountain":
            return "AP_Studio_MA"
        elif display_name == "AP 1BR Mountain":
            return "AP_1BR_MA"
        elif display_name == "AP 2BR Mountain":
            return "AP_2BR_MA"
        elif display_name == "AP 2BR Ocean":
            return "AP_2BR_MK"
    parts = display_name.split()
    if not parts:
        return display_name
    base_parts = []
    view_parts = []
    found_view = False
    for part in parts:
        if part in ["Mountain", "Ocean", "Penthouse", "Garden", "Front"] and not found_view:
            found_view = True
            view_parts.append(part)
        else:
            base_parts.append(part)
            if found_view:
                view_parts.append(part)
    base = " ".join(base_parts)
    view_display = " ".join(view_parts)
    view = reverse_legend.get(view_display, view_display)
    return f"{base} {view}".strip()

def adjust_date_range(resort, checkin_date, num_nights):
    year_str = str(checkin_date.year)
    stay_end = checkin_date + timedelta(days=num_nights - 1)
    holiday_ranges = []

    st.session_state.debug_messages.append(f"Checking holiday overlap for {checkin_date} to {stay_end} at {resort}")

    if "holiday_weeks" not in data or resort not in data["holiday_weeks"]:
        st.session_state.debug_messages.append(f"No holiday weeks defined for {resort}")
        return checkin_date, num_nights, False
    if year_str not in data["holiday_weeks"][resort]:
        st.session_state.debug_messages.append(f"No holiday weeks defined for {resort} in {year_str}")
        return checkin_date, num_nights, False

    st.session_state.debug_messages.append(f"Holiday weeks for {resort}, {year_str}: {list(data['
