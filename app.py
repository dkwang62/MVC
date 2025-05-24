import streamlit as st
import json
import math
from datetime import datetime, timedelta
import pandas as pd
import io

# Load JSON data
with open("Marriott_2025.json", "r") as f:
    data = json.load(f)

# Resort display name mapping
resort_aliases = {
    "Kauai": "Kaua‘i"
}
reverse_aliases = {v: k for k, v in resort_aliases.items()}

# Get display names
display_resorts = [resort_aliases.get(name, name) for name in data.keys()]

# Subtle discount setting in sidebar with tooltip
with st.sidebar:
    discount_percent = st.selectbox(
        "Apply Points Discount",
        options=[0, 25, 30],
        index=0,
        format_func=lambda x: f"{x}%" if x else "No Discount"
    )
    st.caption("\U0001F4A1 Discount applies only to points. Rent is always based on the original points value.")

discount_multiplier = 1 - (discount_percent / 100)

# Title and user input
st.title("\U0001F3DD Marriott Vacation Club Points Calculator")

with st.expander("ℹ️ How Rent Is Calculated"):
    st.markdown("""
    - **Rent is estimated based on original points only.**
    - $0.81 per point for dates in **2025**
    - $0.86 per point for dates in **2026 and beyond**
    - Points are **rounded down** when discounts are applied.
    """)

resort_display = st.selectbox("\U0001F3E8 Select Resort", options=display_resorts)
resort = reverse_aliases.get(resort_display, resort_display)

sample_day = next(iter(data[resort].values()))
room_types = [k for k in sample_day if k not in ("Day", "HolidayWeek", "HolidayWeekStart")]
room_type = st.selectbox("\U0001F6CF Select Room Type", options=room_types)
compare_rooms = st.multiselect("\U0001F4CA Compare With Other Room Types", options=[r for r in room_types if r != room_type])

checkin_date = st.date_input("\U0001F4C5 Check-in Date", min_value=datetime(2024, 12, 27), max_value=datetime(2026, 12, 31))
num_nights = st.number_input("\U0001F319 Number of Nights", min_value=1, max_value=30, value=1)

reference_points = data[resort].get("2025-07-31", {}).get(room_type)

# Function definitions
def calculate_non_holiday_stay(data, resort, room_type, checkin_date, num_nights, discount_multiplier, discount_percent):
    """
    Calculate points and rent for a non-holiday stay.
    Returns a breakdown list, total points, and total rent.
    """
    breakdown = []
    total_points = 0
    total_rent = 0
    rate_per_point = 0.81 if checkin_date.year == 2025 else 0.86

    for i in range(num_nights):
        date = (checkin_date + timedelta(days=i)).strftime("%Y-%m-%d")
        points = data[resort].get(date, {}).get(room_type, reference_points)
        if points is None:
            points = reference_points
        discounted_points = math.floor(points * discount_multiplier)
        rent = points * rate_per_point
        breakdown.append({
            "Date": date,
            "Points": discounted_points,
            "Estimated Rent ($)": f"${rent:.2f}"
        })
        total_points += discounted_points
        total_rent += rent

    return breakdown, total_points, total_rent

def summarize_holiday_weeks(data, resort, room_type, checkin_date, num_nights, reference_points, discount_multiplier, discount_percent):
    """
    Placeholder for summarizing holiday weeks.
    """
    return []

def compare_room_types(data, resort, room_types, checkin_date, num_nights, discount_multiplier, discount_percent):
    """
    Placeholder for comparing room types.
    """
    return pd.DataFrame(), pd.DataFrame()

# Main Calculation
if st.button("\U0001F4CA Calculate"):
    breakdown, total_points, total_rent = calculate_non_holiday_stay(
        data, resort, room_type, checkin_date, num_nights, discount_multiplier, discount_percent
    )

    holiday_weeks = summarize_holiday_weeks(
        data, resort, room_type, checkin_date, num_nights, reference_points, discount_multiplier, discount_percent
    )

    st.subheader("\U0001F4CB Non-Holiday Stay Breakdown")
    df_breakdown = pd.DataFrame(breakdown)
    st.dataframe(df_breakdown, use_container_width=True)

    st.success(f"Total Points Used: {total_points}")
    st.success(f"Estimated Total Rent: ${total_rent}")

    if holiday_weeks:
        st.subheader("\U0001F389 Holiday Weeks Summary")
        df_holidays = pd.DataFrame(holiday_weeks)
        st.dataframe(df_holidays, use_container_width=True)

    csv_data = df_breakdown.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="\U0001F4C4 Download Breakdown as CSV",
        data=csv_data,
        file_name=f"{resort}_stay_breakdown.csv",
        mime="text/csv"
    )

    st.subheader("\U0001F4C5 Visual Calendar View")
    cal_data = df_breakdown[["Date", "Estimated Rent ($)"]].copy()
    cal_data["Date"] = pd.to_datetime(cal_data["Date"])
    cal_data.set_index("Date", inplace=True)
    cal_data["Estimated Rent ($)"] = cal_data["Estimated Rent ($)"].str.replace("$", "").astype(float)
    st.line_chart(cal_data)

    if compare_rooms:
        st.subheader("\U0001F6CF Room Type Comparison")
        all_rooms = [room_type] + compare_rooms
        compare_df, compare_chart = compare_room_types(
            data, resort, all_rooms, checkin_date, num_nights,
            discount_multiplier, discount_percent
        )
        st.dataframe(compare_df, use_container_width=True)
        st.line_chart(compare_chart)

        compare_csv = compare_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="\U0001F4C5 Download Room Comparison as CSV",
            data=compare_csv,
            file_name=f"{resort}_room_comparison.csv",
            mime="text/csv"
        )
