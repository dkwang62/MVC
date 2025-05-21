import streamlit as st
import json
import math
from datetime import datetime, timedelta

# Load Marriott data
with open("Marriott_2025.json", "r") as file:
    data = json.load(file)

# Setup UI
st.title("Marriott Points & Holiday Week Estimator")

resort = st.selectbox("Select Resort", options=list(data.keys()))

sample_day = next(iter(data[resort].values()))
room_types = [k for k in sample_day.keys() if k not in ("Day", "HolidayWeek")]
room_type = st.selectbox("Select Room Type", options=room_types)

checkin_date = st.date_input("Select Check-in Date (2025)", min_value=datetime(2025, 1, 1), max_value=datetime(2025, 12, 31))
num_nights = st.number_input("Number of Nights", min_value=1, max_value=30, value=1)

# Reference value for Dec-Jan spillover
reference_date = "2025-07-31"
reference_points = None
if reference_date in data[resort]:
    reference_points = data[resort][reference_date].get(room_type)

# Calculate non-holiday stay
def calculate_non_holiday_stay(data, resort, room_type, checkin_date, num_nights):
    total_points = 0
    total_rent = 0
    rows = []

    for i in range(num_nights):
        date = checkin_date + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")

        try:
            day_data = data[resort][date_str]
            if day_data.get("HolidayWeek", False):
                continue

            day_of_week = day_data.get("Day", "N/A")
            points = day_data.get(room_type, "N/A")
            rent_val = math.ceil(points * 0.81) if isinstance(points, int) else "N/A"
            rent = f"${rent_val}" if isinstance(rent_val, int) else "N/A"

            if isinstance(points, int):
                total_points += points
                total_rent += rent_val

            rows.append({
                "Date": date_str,
                "Day": day_of_week,
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

# Summarize holiday weeks
def summarize_holiday_weeks(data, resort, room_type, checkin_date, num_nights, fallback_points=None):
    summaries = []
    seen_weeks = set()

    for i in range(num_nights):
        current_date = checkin_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")

        try:
            day_data = data[resort][date_str]
            if day_data.get("HolidayWeek", False):
                start_date = current_date
                for j in range(1, 7):
                    prev_date = current_date - timedelta(days=j)
                    prev_str = prev_date.strftime("%Y-%m-%d")
                    if prev_str not in data[resort] or not data[resort][prev_str].get("HolidayWeek", False):
                        break
                    start_date = prev_date

                start_str = start_date.strftime("%Y-%m-%d")
                if start_str in seen_weeks:
                    continue
                seen_weeks.add(start_str)

                end_date = start_date + timedelta(days=7)

                if start_str <= "2025-01-03":
                    points = fallback_points
                    start_str = "2024-12-27"
                    end_date = datetime(2025, 1, 3) + timedelta(days=1)
                else:
                    points = data[resort][start_str].get(room_type, "N/A")

                rent = f"${math.ceil(points * 0.81)}" if isinstance(points, int) else "N/A"

                summaries.append({
                    "Holiday Week Start": start_str,
                    "Holiday Week End (Checkout)": end_date.strftime("%Y-%m-%d"),
                    "Points on Start Day": points,
                    "Estimated Rent": rent
                })

        except KeyError:
            continue

    return summaries

# Display results
if st.button("Calculate"):
    breakdown, total_points, total_rent = calculate_non_holiday_stay(
        data, resort, room_type, checkin_date, num_nights
    )
    holidays = summarize_holiday_weeks(
        data, resort, room_type, checkin_date, num_nights, fallback_points=reference_points
    )

    st.subheader("Non-Holiday Stay Breakdown")
    st.table(breakdown)
    st.success(f"Total Points: {total_points}")
    st.success(f"Estimated Rent: ${total_rent}")

    if holidays:
        st.subheader("Holiday Weeks Summary")
        st.table(holidays)
