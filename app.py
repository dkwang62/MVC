import streamlit as st
import json
from datetime import datetime, timedelta

# Load JSON data
with open("Marriott_2025.json", "r") as file:
    data = json.load(file)

st.title("Marriott Vacation Club Points & Rent Calculator")

# Resort selector
resort = st.selectbox("Select a Resort", options=list(data.keys()))

# Room type selector
sample_day = next(iter(data[resort].values()))
room_types = [k for k in sample_day.keys() if k not in ("Day", "HolidayWeek")]
room_type = st.selectbox("Select a Room Type", options=room_types)

# Check-in date and number of nights
checkin_date = st.date_input("Select Check-in Date (2025)", min_value=datetime(2025, 1, 1), max_value=datetime(2025, 12, 31))
num_nights = st.number_input("Number of Nights", min_value=1, max_value=30, value=1)

# Button to calculate
if st.button("Calculate"):
    total_points = 0
    total_rent = 0.0
    rows = []
    holiday_summary = []

    for i in range(num_nights):
        current_date = checkin_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")

        try:
            day_data = data[resort][date_str]
            is_holiday = day_data.get("HolidayWeek", False)
            day_of_week = day_data.get("Day", "N/A")
            points = day_data.get(room_type, "N/A")

            if is_holiday:
                if not holiday_summary or holiday_summary[-1]["Holiday Start"] != date_str:
                    holiday_summary.append({
                        "Holiday Start": date_str,
                        "Day": day_of_week,
                        "Points on Start Day": points
                    })
                continue  # skip adding to main table

            rent = round(points * 0.81, 2) if isinstance(points, int) else "N/A"
            if isinstance(points, int):
                total_points += points
                total_rent += rent

            rows.append({
                "Date": date_str,
                "Day": day_of_week,
                "Points Required": points,
                "Estimated Rent ($)": rent
            })

        except KeyError:
            rows.append({
                "Date": date_str,
                "Day": "N/A",
                "Points Required": "Date Not Found",
                "Estimated Rent ($)": "N/A"
            })

    st.write("### Stay Breakdown (Excludes Holiday Weeks)")
    st.table(rows)

    st.success(f"Total Points Required: {total_points}")
    st.success(f"Estimated Total Rent: ${total_rent:,.2f}")

    if holiday_summary:
        st.write("### Holiday Week Days (Excluded)")
        st.table(holiday_summary)
