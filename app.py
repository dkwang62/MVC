import streamlit as st
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# ========== CONFIGURATION ==========
# Years to project
start_year = 2025
end_year = 2027  # You can change to 2028, 2029, etc.

# Points per season and day type
points = {
    "low": {"weekday": 250, "weekend": 350},
    "high": {"weekday": 300, "weekend": 400},
}

# Define low and high seasons
low_season_start = {"month": 1, "day": 7}
low_season_end = {"month": 6, "day": 30}
high_season_start = {"month": 7, "day": 1}
high_season_end = {"month": 12, "day": 15}

# Holiday periods (dates where points will be left blank for manual input)
holiday_periods = [
    ("2025-01-01", "2025-01-06"),  # New Year Week
    ("2025-02-16", "2025-02-23"),  # Presidents' Week
    ("2025-04-13", "2025-04-20"),  # Easter Week
    ("2025-12-20", "2025-12-31"),  # Christmas Week
    # Add similar periods for 2026, 2027 if needed
]

# ========== HELPER FUNCTIONS ==========

def is_holiday(date_obj):
    """Check if a date falls in any holiday period."""
    for start_str, end_str in holiday_periods:
        start = datetime.strptime(start_str, "%Y-%m-%d")
        end = datetime.strptime(end_str, "%Y-%m-%d")
        if start <= date_obj <= end:
            return True
    return False

# ========== BUILD DAILY DICTIONARY ==========

structured_calendar = {}

for year in range(start_year, end_year + 1):
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)
    current = start_date

    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        if is_holiday(current):
            structured_calendar[date_str] = None
        else:
            # Determine season
            low_start = datetime(year, low_season_start["month"], low_season_start["day"])
            low_end = datetime(year, low_season_end["month"], low_season_end["day"])
            high_start = datetime(year, high_season_start["month"], high_season_start["day"])
            high_end = datetime(year, high_season_end["month"], high_season_end["day"])

            if low_start <= current <= low_end:
                season = "low"
            elif high_start <= current <= high_end:
                season = "high"
            else:
                season = "high"  # Default to high season if out of defined range

            # Determine weekday vs weekend
            if current.weekday() in [4, 5]:  # Friday=4, Saturday=5
                day_type = "weekend"
            else:
                day_type = "weekday"

            structured_calendar[date_str] = points[season][day_type]

        current += timedelta(days=1)

# ========== STREAMLIT APP ==========

st.title("Marriott Vacation Club - Daily Points Viewer (2025-2027)")

# Select year and month
year = st.selectbox("Select Year", [str(y) for y in range(start_year, end_year + 1)])
month = st.selectbox("Select Month", [f"{i:02d}" for i in range(1, 13)])

start_of_month = datetime.strptime(f"{year}-{month}-01", "%Y-%m-%d")
end_of_month = (start_of_month + relativedelta(months=1)) - timedelta(days=1)

days_in_month = [(start_of_month + timedelta(days=i)) for i in range((end_of_month - start_of_month).days + 1)]

# Display editable points
updated = False
for day in days_in_month:
    day_str = day.strftime("%Y-%m-%d")
    day_display = day.strftime("%a %d %b %Y")  # Example: Wed 01 Jan 2025

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"**{day_display}**")
    with col2:
        current_value = structured_calendar.get(day_str, 0)
        new_value = st.number_input(
            f"Points {day_str}",
            min_value=0,
            value=current_value if isinstance(current_value, int) else 0,
            key=day_str
        )
        if new_value != (current_value if isinstance(current_value, int) else 0):
            structured_calendar[day_str] = new_value
            updated = True

# Save updated points
if st.button("Save Changes to File") or updated:
    with open("auto_projected_calendar_2025_2027_updated.json", "w") as f:
        json.dump(structured_calendar, f, indent=2)
    if updated:
        st.success("Changes saved to auto_projected_calendar_2025_2027_updated.json")
