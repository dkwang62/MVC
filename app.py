import streamlit as st
import json
import math
from datetime import datetime, timedelta

# Load updated JSON file with HolidayWeekStart flags
with open("Marriott_2025.json", "r") as f:
    data = json.load(f)

# UI controls
st.title("Marriott Points & Holiday Week Calculator")

resort = st.selectbox("Select Resort", options=list(data.keys()))
sample_day = next(iter(data[resort].values()))
room_types = [k for k in sample_day if k not in ("Day", "HolidayWeek", "HolidayWeekStart")]
room_type = st.selectbox("Select Room Type", options=room_types)

checkin_date = st.date_input("Check-in Date (2025)", min_value=datetime(2025, 1, 1), max_value=datetime(2025, 12, 31))
num_nights = st.number_input("Number of Nights", min_value=1, max_value=30, value=1)

# Reference fallback points (for special spillover cases)
reference_points = data[resort].get("2025-07-31", {}).get(room_type)

# -- Non-Holiday Stay Breakdown --
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
                continue  # skip holiday days

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

# -- Holiday Weeks Summary using HolidayWeekStart --
def summarize_holiday_weeks(data, resort, room_type, checkin_date, num_nights, fallback_points=None):
    summaries = []
    
    # Expand search window: 7 days before check-in, to cover weeks starting just before
    search_start = checkin_date - timedelta(days=7)
    search_end = checkin_date + timedelta(days=num_nights)

    current = search_start
    while current < search_end:
        date_str = current.strftime("%Y-%m-%d")

        try:
            entry = data[resort][date_str]
            if entry.get("HolidayWeekStart", False):
                start_str = date_str
                end_str = (current + timedelta(days=8)).strftime("%Y-%m-%d")  # 7 nights, checkout on 8th day

                # Check if this holiday week overlaps with user’s stay
                week_range_start = current
                week_range_end = current + timedelta(days=7)

                if week_range_end >= checkin_date and week_range_start < search_end:
                    points = entry.get(room_type, fallback_points)
                    rent = f"${math.ceil(points * 0.81)}" if isinstance(points, int) else "N/A"

                    summaries.append({
                        "Holiday Week Start": start_str,
                        "Holiday Week End (Checkout)": end_str,
                        "Points on Start Day": points,
                        "Estimated Rent": rent
                    })

        except KeyError:
            pass

        current += timedelta(days=1)

    return summaries

# -- Button Logic --
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
