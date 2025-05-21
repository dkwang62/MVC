import streamlit as st
import json
import math
from datetime import datetime, timedelta

# Load the updated data file
with open("Marriott_2025_updated.json", "r") as file:
    data = json.load(file)

# UI
st.title("Marriott Points & Holiday Week Estimator")

resort = st.selectbox("Select Resort", options=list(data.keys()))
sample_day = next(iter(data[resort].values()))
room_types = [k for k in sample_day if k not in ("Day", "HolidayWeek")]
room_type = st.selectbox("Select Room Type", options=room_types)

checkin_date = st.date_input("Select Check-in Date (2025)", min_value=datetime(2025, 1, 1), max_value=datetime(2025, 12, 31))
num_nights = st.number_input("Number of Nights", min_value=1, max_value=30, value=1)

# Reference fallback points from July 31
reference_points = data[resort].get("2025-07-31", {}).get(room_type)

# --- Calculate non-holiday days ---
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

# --- Identify full, non-overlapping holiday weeks ---
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
                block = [current_date + timedelta(days=d) for d in range(7)]
                block_strs = [d.strftime("%Y-%m-%d") for d in block]

                # Validate full block is holiday week
                if all(d in data[resort] and data[resort][d].get("HolidayWeek", False) for d in block_strs):
                    start_str = block_strs[0]
                    end_checkout = block[-1] + timedelta(days=1)

                    if start_str <= "2025-01-03":
                        start_str = "2024-12-27"
                        end_checkout = datetime(2026, 1, 3) + timedelta(days=1)
                        points = fallback_points
                    else:
                        points = data[resort][start_str].get(room_type, "N/A")

                    rent = f"${math.ceil(points * 0.81)}" if isinstance(points, int) else "N/A"

                    summaries.append({
                        "Holiday Week Start": start_str,
                        "Holiday Week End (Checkout)": end_checkout.strftime("%Y-%m-%d"),
                        "Points on Start Day": points,
                        "Estimated Rent": rent
                    })

                    # Mark these 7 days as covered
                    covered_dates.update(block_strs)
                    current_date += timedelta(days=7)
                    continue
        except KeyError:
            pass

        current_date += timedelta(days=1)

    return summaries

# --- Run when user clicks ---
if st.button("Calculate"):
    breakdown, total_points, total_rent = calculate_non_holiday_stay(
        data, resort, room_type, checkin_date, num_nights
    )
    holidays = summarize_non_overlapping_holiday_weeks(
        data, resort, room_type, checkin_date, num_nights, fallback_points=reference_points
    )

    st.subheader("🗓️ Non-Holiday Stay Breakdown")
    st.table(breakdown)
    st.success(f"Total Points: {total_points}")
    st.success(f"Estimated Rent: ${total_rent}")

    if holidays:
        st.subheader("🎉 Holiday Weeks Summary")
        st.table(holidays)
