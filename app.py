import streamlit as st
import json
import math
from datetime import datetime, timedelta

# Load updated data with HolidayWeekStart
with open("Marriott_2025_with_AllHolidayWeekStarts.json", "r") as f:
    data = json.load(f)

# UI: Select resort and room type
st.title("Marriott Points & Holiday Week Calculator")

resort = st.selectbox("Select Resort", options=list(data.keys()))
sample_day = next(iter(data[resort].values()))
room_types = [k for k in sample_day if k not in ("Day", "HolidayWeek", "HolidayWeekStart")]
room_type = st.selectbox("Select Room Type", options=room_types)

checkin_date = st.date_input("Check-in Date (2025)", min_value=datetime(2025, 1, 1), max_value=datetime(2025, 12, 31))
num_nights = st.number_input("Number of Nights", min_value=1, max_value=30, value=1)

# Fallback reference points (for early January)
reference_points = data[resort].get("2025-07-31", {}).get(room_type)

# -- Non-holiday breakdown logic --
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
                continue  # Skip holiday week days

            points = entry.get(room_type, "N/A")
            rent_val = math.ceil(points * 0.81) if isinstance(points, int) else "N/A"
            rent = f"${rent_val}" if isinstance(rent_val, int) else "N/A"

            if isinstance(points, int):
                total_points += points
                total_rent += rent_val

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

# -- Holiday week summarizer using "HolidayWeekStart" flag --
def summarize_holiday_weeks(data, resort, room_type, checkin_date, num_nights, fallback_points=None):
    summaries = []
    start_date = checkin_date
    end_date = checkin_date + timedelta(days=num_nights)

    for i in range(num_nights):
        current = checkin_date + timedelta(days=i)
        date_str = current.strftime("%Y-%m-%d")
        try:
            entry = data[resort][date_str]
            if entry.get("HolidayWeekStart", False):
                start_str = date_str
                end_str = (current + timedelta(days=7)).strftime("%Y-%m-%d")
                points = entry.get(room_type, fallback_points)
                rent = f"${math.ceil(points * 0.81)}" if isinstance(points, int) else "N/A"
                summaries.append({
                    "Holiday Week Start": start_str,
                    "Holiday Week End (Checkout)": end_str,
                    "Points on Start Day": points,
                    "Estimated Rent": rent
                })
        except KeyError:
            continue

    return summaries

# -- Run when user clicks --
if st.button("Calculate"):
    breakdown, total_points, total_rent = calculate_non_holiday_stay(
        data, resort, room_type, checkin_date, num_nights
    )
    holiday_weeks = summarize_holiday_weeks(
        data, resort, room_type, checkin_date, num_nights, fallback_points=reference_points
    )

    st.subheader("🗓️ Non-Holiday Stay Breakdown")
    st.table(breakdown)
    st.success(f"Total Points: {total_points}")
    st.success(f"Estimated Rent: ${total_rent}")

    if holiday_weeks:
        st.subheader("🎉 Holiday Weeks Summary")
        st.table(holiday_weeks)
