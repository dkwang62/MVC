import streamlit as st
import json
import math
from datetime import datetime, timedelta

# Load updated data
with open("Marriott_2025_updated.json", "r") as file:
    data = json.load(file)

st.title("Marriott Points & Holiday Week Estimator")

# UI selections
resort = st.selectbox("Select Resort", options=list(data.keys()))
sample_day = next(iter(data[resort].values()))
room_types = [k for k in sample_day.keys() if k not in ("Day", "HolidayWeek")]
room_type = st.selectbox("Select Room Type", options=room_types)
checkin_date = st.date_input("Check-in Date (2025)", min_value=datetime(2025, 1, 1), max_value=datetime(2025, 12, 31))
num_nights = st.number_input("Number of Nights", min_value=1, max_value=30, value=1)

# Fallback points template from July 31
reference_points = data[resort].get("2025-07-31", {}).get(room_type)

# --- Non-holiday calculator ---
def calculate_non_holiday_stay(data, resort, room_type, checkin_date, num_nights):
    total_points = 0
    total_rent = 0
    rows = []

    for i in range(num_nights):
        date = checkin_date + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        try:
            entry = data[resort][date_str]
            if entry.get("HolidayWeek", False):
                continue
            points = entry.get(room_type, "N/A")
            rent_val = math.ceil(points * 0.81) if isinstance(points, int) else "N/A"
            rent = f"${rent_val}" if isinstance(rent_val, int) else "N/A"
            total_points += points if isinstance(points, int) else 0
            total_rent += rent_val if isinstance(rent_val, int) else 0
            rows.append({
                "Date": date_str,
                "Day": entry.get("Day", "N/A"),
                "Points Required": points,
                "Estimated Rent": rent
            })
        except KeyError:
            rows.append({
                "Date": date_str,
                "Day": "N/A",
                "Points Required": "Date Not Found",
                "Estimated Rent": "N/A"
            })

    return rows, total_points, total_rent

# --- Holiday week summarizer (non-overlapping only) ---
def summarize_non_overlapping_holiday_weeks(data, resort, room_type, checkin_date, num_nights, fallback_points):
    summaries = []
    covered_dates = set()
    current_date = checkin_date
    end_date = checkin_date + timedelta(days=num_nights)

    while current_date < end_date:
        date_str = current_date.strftime("%Y-%m-%d")

        if date_str in covered_dates:
            current_date += timedelta(days=1)
            continue

        try:
            if data[resort][date_str].get("HolidayWeek", False):
                # Build 7-day block
                block = [current_date + timedelta(days=d_]()
