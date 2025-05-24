import streamlit as st
import json
import math
from datetime import datetime, timedelta
import pandas as pd
import io
import plotly.express as px

# Debug statement to verify deployment
st.write("App version: 2025-05-24-v14")

# Initialize session state for debug messages and chart offset
if "debug_messages" not in st.session_state:
    st.session_state.debug_messages = []
if "chart_offset" not in st.session_state:
    st.session_state.chart_offset = 0
if "num_nights" not in st.session_state:
    st.session_state.num_nights = 7  # Default value

# Load JSON data with error handling
try:
    with open("Marriott_2025.json", "r") as f:
        data = json.load(f)
except Exception as e:
    st.error(f"Error loading Marriott_2025.json: {e}")
    st.session_state.debug_messages.append(f"Data loading error: {e}")
    data = {}
    st.stop()

# Resort display name mapping
resort_aliases = {
    "Kauai Beach Club": "Kaua‘i Beach Club",
    "Ko Olina Beach Club": "Ko Olina Beach Club"
}
reverse_aliases = {v: k for k, v in resort_aliases.items()}

# Get display names
display_resorts = [resort_aliases.get(name, name) for name in data.keys()]

# Check if there are any resorts available
if not display_resorts:
    st.error("No resorts found in Marriott_2025.json. Please check the data file.")
    st.session_state.debug_messages.append("No resorts found in data.")
    st.stop()

# Sidebar setup
with st.sidebar:
    discount_percent = st.selectbox(
        "Apply Points Discount",
        options=[0, 25, 30],
        index=0,
        format_func=lambda x: f"{x}%" if x else "No Discount"
    )
    st.caption("\U0001F4A1 Discount applies only to points. Rent is always based on the original points value.")

# Title and user input
st.title("\U0001F3DD Marriott Vacation Club Points Calculator")

with st.expander("ℹ️ How Rent Is Calculated"):
    st.markdown("""
    - **Rent is estimated based on original points only.**
    - $0.81 per point for dates in **2025**
    - $0.86 per point for dates in **2026 and beyond**
    - Points are **rounded down** when discounts are applied.
    """)

# Use a form to collect inputs and ensure proper sequencing
with st.form(key="input_form"):
    resort_display = st.selectbox("\U0001F3E8 Select Resort", options=display_resorts, key="resort_select")
    resort = reverse_aliases.get(resort_display, resort_display)

    # Debug: Log the selected resort key
    st.session_state.debug_messages.append(f"Selected resort key: {resort}")

    # Validate resort exists in data
    if resort not in data:
        st.error(f"Resort '{resort}' not found in Marriott_2025.json. Available resorts: {list(data.keys())}")
        st.warning("Please update the Marriott_2025.json file to include this resort or select a different one.")
        st.session_state.debug_messages.append(f"Resort not found: {resort}. Available: {list(data.keys())}")
        st.stop()

    # Get room types for the selected resort
    try:
        sample_day = next(iter(data[resort].values()))
        room_types = [k for k in sample_day if k not in ("Day", "HolidayWeek", "HolidayWeekStart")]
    except StopIteration:
        st.error(f"No data available for {resort} in Marriott_2025.json.")
        st.session_state.debug_messages.append(f"No data entries for resort: {resort}")
        st.stop()

    if not room_types:
        st.error(f"No room types found for {resort} in Marriott_2025.json.")
        st.session_state.debug_messages.append(f"No room types found for resort: {resort}")
        st.stop()

    room_type = st.selectbox("\U0001F6CF Select Room Type", options=room_types, key="room_type_select")
    compare_rooms = st.multiselect("\U0001F4CA Compare With Other Room Types", options=[r for r in room_types if r != room_type])

    checkin_date = st.date_input("\U0001F4C5 Check-in Date", min_value=datetime(2024, 12, 27), max_value=datetime(2026, 12, 31), value=datetime(2025, 7, 1))
    st.session_state.num_nights = st.number_input("\U0001F319 Number of Nights", min_value=1, max_value=30, value=st.session_state.num_nights)

    # Slider for chart offset
    st.session_state.chart_offset = st.slider(
        "Select 7-Day Chart Offset (days)",
        min_value=0,
        max_value=max(0, st.session_state.num_nights - 7),
        value=st.session_state.chart_offset,
        step=1,
        help="Adjust to view different 7-day periods of your stay."
    )

    # Submit button for the form
    submit_button = st.form_submit_button(label="\U0001F4CA Calculate")

# Set reference points outside the submit block since it's needed for validation
first_date = next(iter(data[resort]), None)
reference_points = data[resort].get(first_date, {}).get(room_type)
if reference_points is None:
    st.error(f"No points data found for {room_type} in {resort}. Please select a different room type.")
    st.session_state.debug_messages.append(f"No points for {room_type} on {first_date} in {resort}")
    st.stop()

# Set discount multiplier
discount_multiplier = 1 - (discount_percent / 100)

# Main calculation block
if submit_button:
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
            date = checkin_date + timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            entry = data[resort].get(date_str, {})

            # Skip holiday week days
            if entry.get("HolidayWeek", False):
                continue

            points = entry.get(room_type, reference_points)
            if points is None:
                points = reference_points
                st.session_state.debug_messages.append(f"Using reference points for {room_type} on {date_str}: {points}")
            discounted_points = math.floor(points * discount_multiplier)
            rent = math.ceil(points * rate_per_point)  # Round rent up to nearest dollar
            breakdown.append({
                "Date": date_str,
                "Points": discounted_points,
                "Estimated Rent ($)": f"${rent}"
            })
            total_points += discounted_points
            total_rent += rent

        return breakdown, total_points, total_rent

    def summarize_holiday_weeks(data, resort, room_type, checkin_date, num_nights, reference_points, discount_multiplier, discount_percent):
        """
        Summarize holiday weeks that overlap with the stay period.
        Returns a list of holiday week summaries.
        """
        summaries = []
        rate_per_point = 0.81 if checkin_date.year == 2025 else 0.86
        
        # Expand search window: 7 days before check-in to cover weeks starting just before
        search_start = checkin_date - timedelta(days=7)
        search_end = checkin_date + timedelta(days=num_nights)

        current = search_start
        while current < search_end:
            date_str = current.strftime("%Y-%m-%d")
            entry = data[resort].get(date_str, {})

            if entry.get("HolidayWeekStart", False):
                start_str = date_str
                end_str = (current + timedelta(days=7)).strftime("%Y-%m-%d")  # 7 nights, checkout on 8th day

                # Check if this holiday week overlaps with user’s stay
                week_range_start = current
                week_range_end = current + timedelta(days=6)

                if week_range_end >= checkin_date and week_range_start < search_end:
                    points = entry.get(room_type, reference_points)
                    if points is None:
                        points = reference_points
                        st.session_state.debug_messages.append(f"Using reference points for holiday week starting {start_str}: {points}")
                    discounted_points = math.floor(points * discount_multiplier)
                    rent = math.ceil(points * rate_per_point)  # Rent based on original points
                    summaries.append({
                        "Holiday Week Start": start_str,
                        "Holiday Week End (Checkout)": end_str,
                        "Points on Start Day": discounted_points,
                        "Estimated Rent ($)": f"${rent}"
                    })

            current += timedelta(days=1)

        return summaries

    def compare_room_types(data, resort, room_types, checkin_date, num_nights, discount_multiplier, discount_percent):
        """
        Compare points and rent across room types for the stay.
        Returns a DataFrame for the table and a DataFrame for the non-holiday bar chart.
        """
        rate_per_point = 0.81 if checkin_date.year == 2025 else 0.86
        compare_data = []
        chart_data = []
        
        for room in room_types:
            for i in range(num_nights):
                date = checkin_date + timedelta(days=i)
                date_str = date.strftime("%Y-%m-%d")
                # Get the day of the week (e.g., "Sun", "Mon", "Tue")
                day_of_week = date.strftime("%a")
                entry = data[resort].get(date_str, {})
                
                # Skip holiday week days
                if entry.get("HolidayWeek", False):
                    continue
                    
                points = entry.get(room, reference_points)
                if points is None:
                    points = reference_points
                    st.session_state.debug_messages.append(f"Using reference points for {room} on {date_str}: {points}")
                discounted_points = math.floor(points * discount_multiplier)
                rent = math.ceil(points * rate_per_point)  # Round rent up to nearest dollar
                compare_data.append({
                    "Day of Week": day_of_week,  # Separate column for day
                    "Date": date_str,           # Separate column for date
                    "Room Type": room,
                    "Estimated Rent ($)": f"${rent}"
                })
                chart_data.append({
                    "Date": date_str,
                    "Day": day_of_week,
                    "Room Type": room,
                    "Rent": rent
                })
        
        compare_df = pd.DataFrame(compare_data)
        # Pivot the DataFrame to have room types as columns and rent as values
        compare_df_pivot = compare_df.pivot(index=["Day of Week", "Date"], columns="Room Type", values="Estimated Rent ($)").reset_index()
        
        chart_df = pd.DataFrame(chart_data)
        
        return compare_df_pivot, chart_df

    # Perform calculations
    breakdown, total_points, total_rent = calculate_non_holiday_stay(
        data, resort, room_type, checkin_date, st.session_state.num_nights, discount_multiplier, discount_percent
    )

    holiday_weeks = summarize_holiday_weeks(
        data, resort, room_type, checkin_date, st.session_state.num_nights, reference_points, discount_multiplier, discount_percent
    )

    st.subheader("\U0001F4CB Non-Holiday Stay Breakdown")
    if breakdown:
        df_breakdown = pd.DataFrame(breakdown)
        st.dataframe(df_breakdown, use_container_width=True)
    else:
        st.info("No non-holiday days in the selected period.")

    st.success(f"Total Points Used: {total_points}")
    st.success(f"Estimated Total Rent: ${total_rent}")

    if holiday_weeks:
        st.subheader("\U0001F389 Holiday Weeks Summary")
        df_holidays = pd.DataFrame(holiday_weeks)
        st.dataframe(df_holidays, use_container_width=True)

    if breakdown:
        csv_data = df_breakdown.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="\U0001F4C4 Download Breakdown as CSV",
            data=csv_data,
            file_name=f"{resort}_stay_breakdown.csv",
            mime="text/csv"
        )

    if compare_rooms:
        st.subheader("\U0001F6CF Room Type Comparison")
        all_rooms = [room_type] + compare_rooms
        compare_df, chart_df = compare_room_types(
            data, resort, all_rooms, checkin_date, st.session_state.num_nights,
            discount_multiplier, discount_percent
        )
        st.dataframe(compare_df, use_container_width=True)

        compare_csv = compare_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="\U0001F4C5 Download Room Comparison as CSV",
            data=compare_csv,
            file_name=f"{resort}_room_comparison.csv",
            mime="text/csv"
        )

        # Non-Holiday Bar Chart
        if not chart_df.empty:
            # Calculate the date range for the title
            start_date = checkin_date + timedelta(days=st.session_state.chart_offset)
            end_date = start_date + timedelta(days=min(6, st.session_state.num_nights - st.session_state.chart_offset - 1))
            start_date_str = start_date.strftime("%B %-d")
            end_date_str = end_date.strftime("%-d, %Y")
            title = f"Non-Holiday Rent Comparison ({start_date_str}-{end_date_str})"
            st.subheader("\U0001F4CA " + title)
            # Limit to 7 days based on offset
            start_idx = st.session_state.chart_offset
            end_idx = min(start_idx + 7, len(chart_df))
            chart_df_limited = chart_df.iloc[start_idx:end_idx].copy()
            fig_non_holiday = px.bar(
                chart_df_limited,
                x="Day",
                y="Rent",
                color="Room Type",
                barmode="group",
                title=title,
                labels={"Rent": "Estimated Rent ($)", "Day": "Day of Week"},
                height=400,
                text="Rent",
                text_auto=True
            )
            fig_non_holiday.update_traces(
                texttemplate="$%{text}",
                textposition="auto"
            )
            # Ensure the x-axis days are in the correct order for the selected 7 days
            days_order = [(checkin_date + timedelta(days=i)).strftime("%a") for i in range(start_idx, end_idx) if not data[resort].get((checkin_date + timedelta(days=i)).strftime("%Y-%m-%d"), {}).get("HolidayWeek", False)]
            fig_non_holiday.update_xaxes(
                categoryorder="array",
                categoryarray=days_order
            )
            st.plotly_chart(fig_non_holiday, use_container_width=True)

        # Holiday Week Bar Chart
        if holiday_weeks:
            # Update the title for the holiday chart based on offset
            offset_end_date = checkin_date + timedelta(days=st.session_state.chart_offset + 6)
            holiday_start = min(datetime.strptime(week["Holiday Week Start"], "%Y-%m-%d") for week in holiday_weeks if checkin_date <= datetime.strptime(week["Holiday Week Start"], "%Y-%m-%d") <= offset_end_date)
            holiday_end = max(datetime.strptime(week["Holiday Week End (Checkout)"], "%Y-%m-%d") for week in holiday_weeks if checkin_date <= datetime.strptime(week["Holiday Week End (Checkout)"], "%Y-%m-%d") <= offset_end_date)
            holiday_title = f"Holiday Week Rent Comparison ({holiday_start.strftime('%B %-d')}-{holiday_end.strftime('%-d, %Y')})" if holiday_weeks else "Holiday Week Rent Comparison (No Data)"
            st.subheader("\U0001F389 " + holiday_title)
            holiday_chart_data = [
                {"Holiday Week": f"{week['Holiday Week Start']} to {week['Holiday Week End (Checkout)']}", 
                 "Room Type": room, 
                 "Rent": math.ceil(data[resort].get(week['Holiday Week Start'], {}).get(room, reference_points) * 0.81)}
                for week in holiday_weeks
                for room in all_rooms
                if checkin_date <= datetime.strptime(week["Holiday Week Start"], "%Y-%m-%d") <= offset_end_date
            ]
            holiday_chart_df = pd.DataFrame(holiday_chart_data)
            fig_holiday = px.bar(
                holiday_chart_df,
                x="Holiday Week",
                y="Rent",
                color="Room Type",
                barmode="group",
                title=holiday_title,
                labels={"Rent": "Estimated Rent ($)"},
                height=400,
                text="Rent",
                text_auto=True
            )
            fig_holiday.update_traces(
                texttemplate="$%{text}",
                textposition="auto"
            )
            st.plotly_chart(fig_holiday, use_container_width=True)

# Display debug messages in a collapsed expander
with st.expander("Debug Information"):
    if st.session_state.debug_messages:
        for msg in st.session_state.debug_messages:
            st.write(msg)
    else:
        st.write("No debug messages.")
