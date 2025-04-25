import streamlit as st
import json
from datetime import datetime, timedelta

# Load data
with open("mvc_daily_points_2025_2027.json", "r") as f:
    data = json.load(f)

# User selections
resort = st.selectbox("Select Resort", list(data.keys()))
unit_type = st.selectbox("Select Unit Type", list(data[resort].keys()))
view_type = st.selectbox("Select View Type", list(data[resort][unit_type].keys()))
year = st.selectbox("Select Year", ["2025", "2026", "2027"])
month = st.selectbox("Select Month", [f"{i:02d}" for i in range(1, 13)])

# Generate dates for selected month
start_date = datetime.strptime(f"{year}-{month}-01", "%Y-%m-%d")
end_date = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
days = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((end_date - start_date).days + 1)]

# Display and allow editing
updated = False
for day in days:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"**{day}**")
    with col2:
        new_value = st.number_input(f"Points {day}", min_value=0, value=data[resort][unit_type][view_type].get(day, 0), key=day)
        if new_value != data[resort][unit_type][view_type].get(day, 0):
            data[resort][unit_type][view_type][day] = new_value
            updated = True

# Save updated JSON
if st.button("Save to File") or updated:
    with open("mvc_daily_points_2025_2027_updated.json", "w") as f:
        json.dump(data, f, indent=2)
    if updated:
        st.success("Changes saved to mvc_daily_points_2025_2027_updated.json")
