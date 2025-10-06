import streamlit as st
import math
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import traceback
from collections import defaultdict
import uuid

st.write("App is running")

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

    st.session_state.debug_messages.append(f"Holiday weeks for {resort}, {year_str}: {list(data['holiday_weeks'][resort][year_str].keys())}")

    try:
        for h_name, holiday_data in data["holiday_weeks"][resort][year_str].items():
            try:
                if isinstance(holiday_data, str) and holiday_data.startswith("global:"):
                    global_key = holiday_data.split(":", 1)[1]
                    if not (
                        "global_dates" in data
                        and year_str in data["global_dates"]
                        and global_key in data["global_dates"][year_str]
                    ):
                        st.session_state.debug_messages.append(
                            f"Invalid global reference for {h_name}: global:{global_key} not found"
                        )
                        continue
                    holiday_data = data["global_dates"][year_str][global_key]

                if len(holiday_data) >= 2:
                    h_start = datetime.strptime(holiday_data[0], "%Y-%m-%d").date()
                    h_end = datetime.strptime(holiday_data[1], "%Y-%m-%d").date()
                    st.session_state.debug_messages.append(
                        f"Evaluating holiday {h_name}: {holiday_data[0]} to {holiday_data[1]} at {resort}"
                    )
                    if (h_start <= stay_end) and (h_end >= checkin_date):
                        holiday_ranges.append((h_start, h_end, h_name))
                        st.session_state.debug_messages.append(
                            f"Holiday overlap found with {h_name} ({h_start} to {h_end}) at {resort}"
                        )
                    else:
                        st.session_state.debug_messages.append(
                            f"No overlap with {h_name} ({h_start} to {h_end}) at {resort}"
                        )
                else:
                    st.session_state.debug_messages.append(
                        f"Invalid holiday data length for {h_name} at {resort}: {holiday_data}"
                    )
            except (IndexError, ValueError) as e:
                st.session_state.debug_messages.append(f"Invalid holiday range for {h_name} at {resort}: {e}")
    except Exception as e:
        st.session_state.debug_messages.append(f"Error processing holiday weeks for {resort}, {year_str}: {e}")

    if holiday_ranges:
        earliest_holiday_start = min(h_start for h_start, _, _ in holiday_ranges)
        latest_holiday_end = max(h_end for _, h_end, _ in holiday_ranges)
        adjusted_start_date = min(checkin_date, earliest_holiday_start)
        adjusted_end_date = max(stay_end, latest_holiday_end)
        adjusted_nights = (adjusted_end_date - adjusted_start_date).days + 1
        holiday_names = [h_name for _, _, h_name in holiday_ranges]
        st.session_state.debug_messages.append(
            f"Adjusted date range to include holiday week(s) {holiday_names}: {adjusted_start_date} to {adjusted_end_date} ({adjusted_nights} nights) at {resort}"
        )
        return adjusted_start_date, adjusted_nights, True
    st.session_state.debug_messages.append(f"No holiday week adjustment needed for {checkin_date} to {stay_end} at {resort}")
    return checkin_date, num_nights, False

def generate_data(resort, date, cache=None):
    if cache is None:
        cache = st.session_state.data_cache

    date_str = date.strftime("%Y-%m-%d")
    if date_str in cache:
        return cache[date_str]

    year = date.strftime("%Y")
    day_of_week = date.strftime("%a")

    st.session_state.debug_messages.append(f"Processing date: {date_str}, Day: {day_of_week}, Resort: {resort}")

    is_fri_sat = day_of_week in ["Fri", "Sat"]
    is_sun = day_of_week == "Sun"
    day_category = "Fri-Sat" if is_fri_sat else ("Sun" if is_sun else "Mon-Thu")
    st.session_state.debug_messages.append(f"Day_category: {day_category}")

    entry = {}
    season = None
    holiday_name = None
    is_holiday = False
    is_holiday_start = False
    holiday_start_date = None
    holiday_end_date = None
    prev_year = str(int(year) - 1)

    # Check for year-end/beginning holiday assumption
    is_year_end_holiday = False
    if (date.month == 12 and date.day >= 26) or (date.month == 1 and date.day <= 1):
        holiday_start = datetime.strptime(f"{prev_year}-12-26", "%Y-%m-%d").date()
        holiday_end = datetime.strptime(f"{year}-01-01", "%Y-%m-%d").date()
        if holiday_start <= date <= holiday_end:
            is_year_end_holiday = True
            holiday_name = "New Year's Eve/Day"
            season = "Holiday Week"
            is_holiday = True
            holiday_start_date = holiday_start
            holiday_end_date = holiday_end
            if date == holiday_start:
                is_holiday_start = True
            st.session_state.debug_messages.append(f"Assuming 7-day New Year's Holiday for {date_str} at {resort}")

    # Check other holidays
    if year in holiday_weeks.get(resort, {}) and not is_year_end_holiday:
        holiday_data_dict = holiday_weeks[resort][year]
        for h_name, holiday_data in holiday_data_dict.items():
            if isinstance(holiday_data, str) and holiday_data.startswith("global:"):
                global_key = holiday_data.split(":", 1)[1]
                holiday_data = data["global_dates"].get(year, {}).get(global_key, [])
            try:
                if len(holiday_data) >= 2:
                    start = datetime.strptime(holiday_data[0], "%Y-%m-%d").date()
                    end = datetime.strptime(holiday_data[1], "%Y-%m-%d").date()
                    st.session_state.debug_messages.append(f"Checking holiday {h_name} for {resort}: {start} to {end}")
                    if start <= date <= end:
                        is_holiday = True
                        holiday_name = h_name
                        season = "Holiday Week"
                        holiday_start_date = start
                        holiday_end_date = end
                        if date == start:
                            is_holiday_start = True
            except (IndexError, ValueError) as e:
                st.session_state.debug_messages.append(f"Holiday parse error for {h_name}: {e}")

    # Season determination
    if not is_holiday:
        if year in season_blocks.get(resort, {}):
            for season_name, ranges in season_blocks[resort][year].items():
                for start_date, end_date in ranges:
                    try:
                        start = datetime.strptime(start_date, "%Y-%m-%d").date()
                        end = datetime.strptime(end_date, "%Y-%m-%d").date()
