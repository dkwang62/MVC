import streamlit as st
import json
from datetime import datetime, timedelta

# Load JSON data
with open("Marriott_2025.json", "r") as file:
    data = json.load(file)

st.title("Marriott Vacation Club Points Calculator")

# Resort selector
resort = st.selectbox("Select a Resort", options=list(data.keys()))

# Room type selector
sample_day = next(iter(data[resort].values()))
room_types = [k for k in sample_day.keys() if k not in ("Day", "HolidayWeek")]
room_type = st.selectbox("Select a Room Type", options=room_types)

# Check-in date selector (only 2025)
checkin_date = st.date_input("Select Check-in Date (2025)", min_value=datetime(2025, 1, 1), max_value=datetime(2025, 12, 31))

# Number of nights
num_nights = st.number_input("Number of Nights", min_value=1, max_value=30, value=1)

# Show reservation breakdown
if st.button("Calculate Points"):
    total_points = 0
    result = []

    for i in range(num_nights):
        date = checkin_date + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")

        try:
            day_data = data[resort][date_str]
            day_of_week = day_data["Day"]
            points = day_data.get(room_type, "N/A")
        except KeyError:
            day_of_week = "N/A"
            points = "Date Not Found"

        result.append({
            "Date": date_str,
            "Day": day_of_week,
            "Points Required": points
        })

        if isinstance(points, int):
            total_points += points

    st.write("### Stay Breakdown")
    st.table(result)
    st.success(f"Total Points Required: {total_points}")
