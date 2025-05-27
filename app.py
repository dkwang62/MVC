import streamlit as st
import math
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff

# Initialize session state for debug messages
if "debug_messages" not in st.session_state:
    st.session_state.debug_messages = []

# Hardcoded data
season_blocks = {
    "Kauai Beach Club": {
        "2025": {
            "Low Season": [
                ["2025-01-03", "2025-01-30"],
                ["2025-03-28", "2025-04-17"],
                ["2025-04-25", "2025-06-05"],
                ["2025-08-29", "2025-11-20"],
                ["2025-12-05", "2025-12-18"]
            ],
            "High Season": [
                ["2025-01-31", "2025-02-13"],
                ["2025-02-21", "2025-03-27"],
                ["2025-06-06", "2025-07-03"],
                ["2025-07-11", "2025-08-28"]
            ]
        },
        "2026": {
            "Low Season": [
                ["2026-01-02", "2026-01-29"],
                ["2026-03-27", "2026-04-02"],
                ["2026-04-10", "2026-06-04"],
                ["2026-08-28", "2026-11-19"],
                ["2026-12-04", "2026-12-17"]
            ],
            "High Season": [
                ["2026-01-30", "2026-02-12"],
                ["2026-02-20", "2026-03-26"],
                ["2026-06-05", "2026-07-02"],
                ["2026-07-10", "2026-08-27"]
            ]
        }
    },
    "Ko Olina Beach Club": {
        "2025": {
            "Low Season": [
                ["2025-01-03", "2025-01-30"],
                ["2025-03-28", "2025-04-17"],
                ["2025-04-25", "2025-06-05"],
                ["2025-08-29", "2025-11-20"],
                ["2025-12-05", "2025-12-18"]
            ],
            "High Season": [
                ["2025-01-31", "2025-02-13"],
                ["2025-02-21", "2025-03-27"],
                ["2025-06-06", "2025-07-03"],
                ["2025-07-11", "2025-08-28"]
            ]
        },
        "2026": {
            "Low Season": [
                ["2026-01-02", "2026-01-29"],
                ["2026-03-27", "2026-04-02"],
                ["2026-04-10", "2026-06-04"],
                ["2026-08-28", "2026-11-19"],
                ["2026-12-04", "2026-12-17"]
            ],
            "High Season": [
                ["2026-01-30", "2026-02-12"],
                ["2026-02-20", "2026-03-26"],
                ["2026-06-05", "2026-07-02"],
                ["2026-07-10", "2026-08-27"]
            ]
        }
    }
}

holiday_weeks = {
    "Kauai Beach Club": {
        "2025": {
            "Presidents Day": ["2025-02-14", "2025-02-20"],
            "Easter": ["2025-04-18", "2025-04-24"],
            "Independence Day": ["2025-07-04", "2025-07-10"],
            "Thanksgiving": ["2025-11-21", "2025-11-27"],
            "Thanksgiving 2": ["2025-11-28", "2025-12-04"],
            "Christmas": ["2025-12-19", "2025-12-25"],
            "New Year's Eve/Day": ["2025-12-26", "2026-01-01"]
        },
        "2026": {
            "Presidents Day": ["2026-02-13", "2026-02-19"],
            "Easter": ["2026-04-03", "2026-04-09"],
            "Independence Day": ["2026-07-03", "2026-07-09"],
            "Thanksgiving": ["2026-11-20", "2026-11-26"],
            "Thanksgiving 2": ["2026-11-27", "2026-12-03"],
            "Christmas": ["2026-12-18", "2026-12-24"],
            "New Year's Eve/Day": ["2026-12-25", "2026-12-31"]
        }
    },
    "Ko Olina Beach Club": {
        "2025": {
            "Presidents Day": ["2025-02-14", "2025-02-20"],
            "Easter": ["2025-04-18", "2025-04-24"],
            "Independence Day": ["2025-07-04", "2025-07-10"],
            "Thanksgiving": ["2025-11-21", "2025-11-27"],
            "Thanksgiving 2": ["2025-11-28", "2025-12-04"],
            "Christmas": ["2025-12-19", "2025-12-25"],
            "New Year's Eve/Day": ["2025-12-26", "2026-01-01"]
        },
        "2026": {
            "Presidents Day": ["2026-02-13", "2026-02-19"],
            "Easter": ["2026-04-03", "2026-04-09"],
            "Independence Day": ["2026-07-03", "2026-07-09"],
            "Thanksgiving": ["2026-11-20", "2026-11-26"],
            "Thanksgiving 2": ["2026-11-27", "2026-12-03"],
            "Christmas": ["2026-12-18", "2026-12-24"],
            "New Year's Eve/Day": ["2026-12-25", "2026-12-31"]
        }
    }
}

room_view_legend = {
    "GV": "Garden View",
    "OV": "Ocean View",
    "OF": "Ocean Front",
    "Mountain View": "Mountain View",
    "Ocean View": "Ocean View",
    "Penthouse": "Penthouse",
    "MA": "Mountain View",
    "MK": "Ocean View",
    "PH MA": "Penthouse Mountain View",
    "PH MK": "Penthouse Ocean View",
    "AP Studio MA": "Asia Pacific Studio Mountain View",
    "AP 1 BDRM MA": "Asia Pacific 1 Bedroom Mountain View",
    "AP 2 BDRM MA": "Asia Pacific 2 Bedroom Mountain View",
    "AP 2 BDRM MK": "Asia Pacific 2 Bedroom Ocean View"
}

reference_points = {
    "Kauai Beach Club": {
        "Low Season": {
            "Fri-Sat": {
                "Parlor GV": 175,
                "Parlor OV": 225,
                "Parlor OF": 275,
                "Studio GV": 275,
                "Studio OV": 350,
                "Studio OF": 425,
                "1BR GV": 400,
                "1BR OV": 500,
                "1BR OF": 600,
                "2BR OV": 750,
                "2BR OF": 925
            },
            "Sun-Thu": {
                "Parlor GV": 125,
                "Parlor OV": 175,
                "Parlor OF": 200,
                "Studio GV": 200,
                "Studio OV": 250,
                "Studio OF": 300,
                "1BR GV": 275,
                "1BR OV": 350,
                "1BR OF": 425,
                "2BR OV": 525,
                "2BR OF": 650
            }
        },
        "High Season": {
            "Fri-Sat": {
                "Parlor GV": 200,
                "Parlor OV": 275,
                "Parlor OF": 300,
                "Studio GV": 300,
                "Studio OV": 400,
                "Studio OF": 475,
                "1BR GV": 450,
                "1BR OV": 575,
                "1BR OF": 700,
                "2BR OV": 875,
                "2BR OF": 1075
            },
            "Sun-Thu": {
                "Parlor GV": 150,
                "Parlor OV": 200,
                "Parlor OF": 225,
                "Studio GV": 225,
                "Studio OV": 275,
                "Studio OF": 350,
                "1BR GV": 325,
                "1BR OV": 400,
                "1BR OF": 500,
                "2BR OV": 625,
                "2BR OF": 750
            }
        },
        "Holiday Week": {
            "Presidents Day": {"Parlor GV": 1375},
            "Easter": {"Parlor GV": 1375},
            "Independence Day": {"Parlor GV": 1150},
            "Thanksgiving": {"Parlor GV": 975},
            "Thanksgiving 2": {"Parlor GV": 1375},
            "Christmas": {"Parlor GV": 1375},
            "New Year's Eve/Day": {"Parlor GV": 1550}
        }
    },
    "Ko Olina Beach Club": {
        "Low Season": {
            "Fri-Sat": {
                "Studio MA": 340,
                "Studio MK": 360,
                "Studio PH MA": 340,
                "Studio PH MK": 475,
                "1BR MA": 575,
                "1BR MK": 625,
                "1BR PH MA": 575,
                "1BR PH MK": 850,
                "2BR MA": 775,
                "2BR MK": 900,
                "2BR PH MA": 775,
                "2BR PH MK": 1075,
                "3BR MA": 925,
                "3BR MK": 1175
            },
            "Sun-Thu": {
                "Studio MA": 205,
                "Studio MK": 270,
                "Studio PH MA": 205,
                "Studio PH MK": 295,
                "1BR MA": 355,
                "1BR MK": 465,
                "1BR PH MA": 355,
                "1BR PH MK": 550,
                "2BR MA": 500,
                "2BR MK": 625,
                "2BR PH MA": 500,
                "2BR PH MK": 750,
                "3BR MA": 650,
                "3BR MK": 825
            }
        },
        "High Season": {
            "Fri-Sat": {
                "Studio MA": 360,
                "Studio MK": 430,
                "Studio PH MA": 360,
                "Studio PH MK": 520,
                "1BR MA": 625,
                "1BR MK": 725,
                "1BR PH MA": 625,
                "1BR PH MK": 925,
                "2BR MA": 850,
                "2BR MK": 1050,
                "2BR PH MA": 850,
                "2BR PH MK": 1250,
                "3BR MA": 1075,
                "3BR MK": 1375
            },
            "Sun-Thu": {
                "Studio MA": 250,
                "Studio MK": 295,
                "Studio PH MA": 250,
                "Studio PH MK": 340,
                "1BR MA": 415,
                "1BR MK": 525,
                "1BR PH MA": 415,
                "1BR PH MK": 625,
                "2BR MA": 575,
                "2BR MK": 725,
                "2BR PH MA": 575,
                "2BR PH MK": 875,
                "3BR MA": 750,
                "3BR MK": 975
            }
        },
        "Holiday Week": {
            "Presidents Day": {"Studio MA": 2160},
            "Easter": {"Studio MA": 2160},
            "Independence Day": {"Studio MA": 1960},
            "Thanksgiving": {"Studio MA": 1690},
            "Thanksgiving 2": {"Studio MA": 2160},
            "Christmas": {"Studio MA": 2160},
            "New Year's Eve/Day": {"Studio MA": 2365}
        },
        "AP Rooms": {
            "Fri-Sat": {
                "AP Studio MA": 440,
                "AP 1 BDRM MA": 630,
                "AP 2 BDRM MA": 960,
                "AP 2 BDRM MK": 1160
            },
            "Sun": {
                "AP Studio MA": 350,
                "AP 1 BDRM MA": 510,
                "AP 2 BDRM MA": 770,
                "AP 2 BDRM MK": 910
            },
            "Mon-Thu": {
                "AP Studio MA": 250,
                "AP 1 BDRM MA": 360,
                "AP 2 BDRM MA": 550,
                "AP 2 BDRM MK": 660
            },
            "Full Week": {
                "AP Studio MA": 2220,
                "AP 1 BDRM MA": 3210,
                "AP 2 BDRM MA": 4890,
                "AP 2 BDRM MK": 5870
            }
        }
    }
}

# Function to generate data structure
def generate_data(resort, date):
    date_str = date.strftime("%Y-%m-%d")
    year = date.strftime("%Y")
    day_of_week = date.strftime("%a")
    
    st.session_state.debug_messages.append(f"Processing date: {date_str}, Day of week: {day_of_week}")
    
    # Determine day category for regular and AP rooms
    is_fri_sat = day_of_week in ["Fri", "Sat"]
    is_sun = day_of_week == "Sun"
    day_category = "Fri-Sat" if is_fri_sat else "Sun-Thu"  # For regular rooms
    ap_day_category = "Fri-Sat" if is_fri_sat else ("Sun" if is_sun else "Mon-Thu")  # For AP rooms
    st.session_state.debug_messages.append(f"Day category determined: {day_category} (is_fri_sat: {is_fri_sat})")
    st.session_state.debug_messages.append(f"AP day category determined: {ap_day_category}")

    entry = {}

    # Check if the resort has AP rooms and identify AP room types
    ap_room_types = []
    if resort == "Ko Olina Beach Club" and "AP Rooms" in reference_points[resort]:
        ap_room_types = list(reference_points[resort]["AP Rooms"]["Fri-Sat"].keys())
        st.session_state.debug_messages.append(f"AP room types found: {ap_room_types}")

    # Determine season for the specific date (for all resorts, including Ko Olina for normal rooms)
    season = None
    try:
        for s_type in ["Low Season", "High Season"]:
            for [start, end] in season_blocks[resort][year][s_type]:
                s_start = datetime.strptime(start, "%Y-%m-%d").date()
                s_end = datetime.strptime(end, "%Y-%m-%d").date()
                st.session_state.debug_messages.append(f"Checking season {s_type}: {start} to {end}")
                if s_start <= date <= s_end:
                    season = s_type
                    st.session_state.debug_messages.append(f"Season match found: {season} for {date_str}")
                    break
            if season:
                break
    except ValueError as e:
        st.session_state.debug_messages.append(f"Invalid season date in {resort}, {year}, {s_type}: {e}")

    if not season:
        season = "Low Season"
        st.session_state.debug_messages.append(f"No season match found for {date_str}, defaulting to {season}")
    
    st.session_state.debug_messages.append(f"Final season determined for {date_str}: {season}")

    # Check for holiday week (only for non-AP rooms)
    is_holiday = False
    is_holiday_start = False
    holiday_name = None
    if not ap_room_types or resort != "Ko Olina Beach Club":  # Skip holiday check for AP rooms
        try:
            for h_name, [start, end] in holiday_weeks[resort][year].items():
                h_start = datetime.strptime(start, "%Y-%m-%d").date()
                h_end = datetime.strptime(end, "%Y-%m-%d").date()
                st.session_state.debug_messages.append(f"Checking holiday {h_name}: {start} to {end}")
                if h_start <= date <= h_end:
                    is_holiday = True
                    holiday_name = h_name
                    if date == h_start:
                        is_holiday_start = True
                    st.session_state.debug_messages.append(f"Holiday match found: {holiday_name} for {date_str}")
                    break
        except ValueError as e:
            st.session_state.debug_messages.append(f"Invalid holiday date in {resort}, {year}, {h_name}: {e}")

    # Assign points based on room type
    all_room_types = []
    # Always include normal room types based on season and day category
    all_room_types.extend(list(reference_points[resort][season][day_category].keys()))
    # Add AP room types if they exist (for Ko Olina Beach Club)
    if ap_room_types:
        all_room_types.extend(ap_room_types)

    for room_type in all_room_types:
        if room_type in ap_room_types:
            # AP room: Use AP day category and skip season/holiday logic
            points_ref = reference_points[resort]["AP Rooms"][ap_day_category]
            points = points_ref.get(room_type, 0)
            st.session_state.debug_messages.append(f"Applying AP room points for {room_type} on {date_str} ({ap_day_category}): {points}")
        else:
            # Regular room: Use season and holiday logic
            if is_holiday and is_holiday_start:
                points_ref = reference_points[resort]["Holiday Week"].get(holiday_name, {})
                st.session_state.debug_messages.append(f"Applying Holiday Week points for {holiday_name} on {date_str}")
            elif is_holiday and not is_holiday_start:
                points_ref = {room: 0 for room in reference_points[resort]["Holiday Week"].get(holiday_name, {})}
                st.session_state.debug_messages.append(f"Zero points for {date_str} (part of holiday week {holiday_name})")
            else:
                points_ref = reference_points[resort][season][day_category]
                st.session_state.debug_messages.append(f"Applying {season} {day_category} points for {date_str}")

            points = points_ref.get(room_type, 0)
            st.session_state.debug_messages.append(f"Assigned points for {room_type}: {points}")

        entry[room_type] = points

    if is_holiday and not ap_room_types:  # Only add holiday info for non-AP rooms
        entry["HolidayWeek"] = True
        entry["holiday_name"] = holiday_name
    if is_holiday_start and not ap_room_types:
        entry["HolidayWeekStart"] = True

    return entry

# Function to adjust date range for holiday weeks
def adjust_date_range(resort, checkin_date, num_nights):
    year_str = str(checkin_date.year)
    original_checkin_date = checkin_date
    original_num_nights = num_nights
    stay_end = checkin_date + timedelta(days=num_nights - 1)
    holiday_ranges = []
    
    st.session_state.debug_messages.append(f"Checking holiday overlap for {checkin_date} to {stay_end}")
    try:
        for h_name, [start, end] in holiday_weeks[resort][year_str].items():
            h_start = datetime.strptime(start, "%Y-%m-%d").date()
            h_end = datetime.strptime(end, "%Y-%m-%d").date()
            st.session_state.debug_messages.append(f"Evaluating holiday {h_name}: {h_start} to {h_end}")
            if (h_start <= stay_end) and (h_end >= checkin_date):
                holiday_ranges.append((h_start, h_end))
                st.session_state.debug_messages.append(f"Holiday overlap found with {h_name}")
            else:
                st.session_state.debug_messages.append(f"No overlap with {h_name}")
    except ValueError as e:
        st.session_state.debug_messages.append(f"Invalid holiday range in {resort}, {year_str}: {e}")

    if holiday_ranges:
        earliest_holiday_start = min(h_start for h_start, _ in holiday_ranges)
        latest_holiday_end = max(h_end for _, h_end in holiday_ranges)
        adjusted_start = min(checkin_date, earliest_holiday_start)
        adjusted_end = max(stay_end, latest_holiday_end)
        adjusted_nights = (adjusted_end - adjusted_start).days + 1
        st.session_state.debug_messages.append(f"Adjusted date range to include holiday week: {adjusted_start} to {adjusted_end} ({adjusted_nights} nights)")
        return adjusted_start, adjusted_nights, True
    st.session_state.debug_messages.append(f"No holiday week adjustment needed for {checkin_date} to {stay_end}")
    return checkin_date, num_nights, False

# Function to create Gantt chart
def create_gantt_chart(resort, year):
    gantt_data = []
    year_str = str(year)
    
    try:
        # Add holiday data
        for h_name, [start, end] in holiday_weeks[resort][year_str].items():
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
            gantt_data.append({
                "Task": h_name,
                "Start": start_date,
                "Finish": end_date,
                "Type": "Holiday"
            })
            st.session_state.debug_messages.append(f"Added holiday: {h_name}, Start: {start_date}, Finish: {end_date}")

        # Add season data
        for season_type in ["Low Season", "High Season"]:
            for i, [start, end] in enumerate(season_blocks[resort][year_str][season_type], 1):
                start_date = datetime.strptime(start, "%Y-%m-%d").date()
                end_date = datetime.strptime(end, "%Y-%m-%d").date()
                gantt_data.append({
                    "Task": f"{season_type} {i}",
                    "Start": start_date,
                    "Finish": end_date,
                    "Type": season_type
                })
                st.session_state.debug_messages.append(f"Added season: {season_type} {i}, Start: {start_date}, Finish: {end_date}")
    
        df = pd.DataFrame(gantt_data)
        if df.empty:
            st.session_state.debug_messages.append("Gantt DataFrame is empty")
            return px.timeline(pd.DataFrame({"Task": ["No Data"], "Start": [datetime.now().date()], "Finish": [datetime.now().date()], "Type": ["No Data"]}))

        colors = {
            "Holiday": "rgb(255, 99, 71)",
            "Low Season": "rgb(135, 206, 250)",
            "High Season": "rgb(50, 205, 50)"
        }
        
        fig = px.timeline(
            df,
            x_start="Start",
            x_end="Finish",
            y="Task",
            color="Type",
            color_discrete_map=colors,
            title=f"{resort} Seasons and Holidays ({year})",
            height=600
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Period",
            showlegend=True
        )
        return fig
    except Exception as e:
        st.session_state.debug_messages.append(f"Error in create_gantt_chart: {str(e)}")
        return px.timeline(pd.DataFrame({"Task": ["Error"], "Start": [datetime.now().date()], "Finish": [datetime.now().date()], "Type": ["Error"]}))

# Resort display name mapping
resort_aliases = {
    "Kauai Beach Club": "Kaua‘i Beach Club",
    "Ko Olina Beach Club": "Ko Olina Beach Club"
}
reverse_aliases = {v: k for k, v in resort_aliases.items()}
display_resorts = list(resort_aliases.values())

# Sidebar for discount
with st.sidebar:
    discount_percent = st.selectbox(
        "Apply Points Discount",
        options=[0, 25, 30],
        index=0,
        format_func=lambda x: f"{x}%" if x else "No Discount"
    )
    st.caption("Discount applies only to points. Rent is based on original points.")

discount_multiplier = 1 - (discount_percent / 100)

# Title and user input
st.title("Marriott Vacation Club Points Calculator")

with st.expander("ℹ️ How Rent Is Calculated"):
    st.markdown("""
    - **Rent is estimated based on original points only.**
    - $0.81 per point for dates in **2025**
    - $0.86 per point for dates in **2026 and beyond**
    - Points are **rounded down** when discounts are applied.
    - **Holiday weeks**: Points are applied only on the first day; other days within the holiday week are 0 points (except for AP rooms, which use daily points).
    """)

# Year selection for Gantt chart
year_options = ["2025", "2026"]
default_year = "2025"
year_select = st.selectbox("Select Year for Calendar", options=year_options, index=year_options.index(default_year))

# Display Gantt chart
resort_display = st.selectbox("Select Resort", options=display_resorts, key="resort_select")
resort = reverse_aliases.get(resort_display, resort_display)
st.session_state.debug_messages.append(f"Selected resort: {resort}")
st.subheader(f"Season and Holiday Calendar ({year_select})")
gantt_fig = create_gantt_chart(resort, year_select)
st.plotly_chart(gantt_fig, use_container_width=True)

# Get room types
sample_date = datetime(2025, 1, 8).date()  # Wednesday
sample_entry = generate_data(resort, sample_date)
room_types = [k for k in sample_entry if k not in ("HolidayWeek", "HolidayWeekStart", "holiday_name")]
if not room_types:
    st.error(f"No room types found for {resort}.")
    st.session_state.debug_messages.append(f"No room types for {resort}")
    st.stop()

room_type = st.selectbox("Select Room Type", options=room_types, key="room_type_select")
compare_rooms = st.multiselect("Compare With Other Room Types", options=[r for r in room_types if r != room_type])

checkin_date = st.date_input("Check-in Date", min_value=datetime(2024, 12, 27).date(), max_value=datetime(2026, 12, 31).date(), value=datetime(2025, 3, 25).date())
num_nights = st.number_input("Number of Nights", min_value=1, max_value=30, value=10)

# Adjust date range for holidays
original_checkin_date = checkin_date
checkin_date, adjusted_nights, was_adjusted = adjust_date_range(resort, checkin_date, num_nights)
if was_adjusted:
    st.info(f"Date range adjusted to include full holiday week: {checkin_date.strftime('%Y-%m-%d')} to {(checkin_date + timedelta(days=adjusted_nights-1)).strftime('%Y-%m-%d')} ({adjusted_nights} nights).")
st.session_state.last_checkin_date = checkin_date

# Set reference points
reference_entry = generate_data(resort, sample_date)
reference_points_resort = {k: v for k, v in reference_entry.items() if k not in ("HolidayWeek", "HolidayWeekStart", "holiday_name")}

# Functions
def calculate_stay(resort, room_type, checkin_date, num_nights, discount_multiplier, discount_percent):
    breakdown = []
    total_points = 0
    total_rent = 0
    rate_per_point = 0.81 if checkin_date.year == 2025 else 0.86

    for i in range(num_nights):
        date = checkin_date + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        entry = generate_data(resort, date)
        
        points = entry.get(room_type, reference_points_resort.get(room_type, 0))
        st.session_state.debug_messages.append(f"Calculating for {date_str}: Points for {room_type} = {points}")
        discounted_points = math.floor(points * discount_multiplier)
        rent = math.ceil(points * rate_per_point)
        breakdown.append({
            "Date": date_str,
            "Day": date.strftime("%a"),
            "Points": discounted_points,
            "Rent": rent,
            "Holiday": entry.get("holiday_name", "No")
        })
        # Add holiday marker for AP rooms
        if "HolidayWeek" in entry and entry.get("HolidayWeekStart", False):
            breakdown[-1]["HolidayMarker"] = "🏖️"
        total_points += discounted_points
        total_rent += rent

    return breakdown, total_points, total_rent

def compare_room_types(resort, room_types, checkin_date, num_nights, discount_multiplier, discount_percent):
    rate_per_point = 0.81 if checkin_date.year == 2025 else 0.86
    compare_data = []
    chart_data = []
    
    all_dates = []
    for i in range(num_nights):
        date = checkin_date + timedelta(days=i)
        all_dates.append(date)
    for h_start, h_end in holiday_weeks[resort][str(checkin_date.year)].values():
        h_start = datetime.strptime(h_start, "%Y-%m-%d").date()
        h_end = datetime.strptime(h_end, "%Y-%m-%d").date()
        if (h_start <= checkin_date + timedelta(days=num_nights-1)) and (h_end >= checkin_date):
            current_date = h_start
            while current_date <= h_end:
                if current_date not in all_dates:
                    all_dates.append(current_date)
                current_date += timedelta(days=1)
    all_dates = sorted(list(set(all_dates)))
    
    total_points_by_room = {room: 0 for room in room_types}  # Track total points
    
    for room in room_types:
        for date in all_dates:
            date_str = date.strftime("%Y-%m-%d")
            day_of_week = date.strftime("%a")
            entry = generate_data(resort, date)
            
            points = entry.get(room, reference_points_resort.get(room, 0))
            discounted_points = math.floor(points * discount_multiplier)
            rent = math.ceil(points * rate_per_point)
            compare_data.append({
                "Date": date_str,
                "Room Type": room,
                "Estimated Rent ($)": f"${rent}",
                "Points": discounted_points  # Add points for total calculation
            })
            chart_data.append({
                "Date": date,
                "DateStr": date_str,
                "Day": day_of_week,
                "Room Type": room,
                "Rent": rent,
                "Points": discounted_points,
                "Holiday": entry.get("holiday_name", "No")
            })
            total_points_by_room[room] += discounted_points  # Accumulate points
    
    # Add total points row
    total_row = {"Date": "Total Points"}
    for room in room_types:
        total_row[room] = total_points_by_room[room]
    compare_data.append(total_row)
    
    compare_df = pd.DataFrame(compare_data)
    compare_df_pivot = compare_df.pivot_table(index="Date", columns="Room Type", values=["Estimated Rent ($)", "Points"], aggfunc="first").reset_index()
    # Flatten the pivot table columns
    compare_df_pivot.columns = ['Date'] + [f"{col[1]} {col[0]}" for col in compare_df_pivot.columns[1:]]
    chart_df = pd.DataFrame(chart_data)
    
    st.session_state.debug_messages.append(f"chart_df columns: {chart_df.columns.tolist()}")
    st.session_state.debug_messages.append(f"chart_df head: {chart_df.head().to_dict()}")
    
    return chart_df, compare_df_pivot

# Main Calculation
if st.button("Calculate"):
    breakdown, total_points, total_rent = calculate_stay(
        resort, room_type, checkin_date, adjusted_nights, discount_multiplier, discount_percent
    )

    st.subheader("Stay Breakdown")
    if breakdown:
        df_breakdown = pd.DataFrame(breakdown)
        st.dataframe(df_breakdown, use_container_width=True)
    else:
        st.info("No data available for the selected period.")

    st.success(f"Total Points Used: {total_points}")
    st.success(f"Estimated Total Rent: ${total_rent}")

    if breakdown:
        csv_data = df_breakdown.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Breakdown as CSV",
            data=csv_data,
            file_name=f"{resort}_stay_breakdown.csv",
            mime="text/csv"
        )

    if compare_rooms:
        st.subheader("Room Type Comparison")
        st.info("Note: During holiday weeks, normal rooms apply points only on the first day, while AP rooms use daily points based on the day of the week.")
        all_rooms = [room_type] + compare_rooms
        chart_df, compare_df = compare_room_types(
            resort, all_rooms, checkin_date, adjusted_nights, discount_multiplier, discount_percent
        )
        # Split the pivot table into rent and points for better display
        rent_columns = ["Date"] + [col for col in compare_df.columns if "Estimated Rent ($)" in col]
        points_columns = ["Date"] + [col for col in compare_df.columns if "Points" in col]
        st.write("### Estimated Rent ($)")
        st.dataframe(compare_df[rent_columns], use_container_width=True)
        st.write("### Total Points")
        st.dataframe(compare_df[points_columns], use_container_width=True)

        compare_csv = compare_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Room Comparison as CSV",
            data=compare_csv,
            file_name=f"{resort}_room_comparison.csv",
            mime="text/csv"
        )

        if not chart_df.empty:
            required_columns = ["Date", "DateStr", "Day", "Room Type", "Rent", "Points", "Holiday"]
            if all(col in chart_df.columns for col in required_columns):
                start_date = chart_df["Date"].min()
                end_date = chart_df["Date"].max()
                start_date_str = start_date.strftime("%B %-d")
                end_date_str = end_date.strftime("%-d, %Y")
                title = f"Rent Comparison ({start_date_str}-{end_date_str})"
                st.subheader(title)
                fig = px.bar(
                    chart_df,
                    x="Day",
                    y="Rent",
                    color="Room Type",
                    barmode="group",
                    title=title,
                    labels={"Rent": "Estimated Rent ($)", "Day": "Day of Week"},
                    height=500,
                    text="Rent",
                    text_auto=True
                )
                fig.update_traces(texttemplate="$%{text}", textposition="auto")
                fig.update_xaxes(
                    categoryorder="array",
                    categoryarray=[d.strftime("%a") for d in sorted(chart_df["Date"].unique())]
                )
                fig.update_layout(
                    legend_title_text="Room Type",
                    bargap=0.2,
                    bargroupgap=0.1
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("Chart DataFrame missing required columns.")
                st.session_state.debug_messages.append(f"Chart DataFrame columns: {chart_df.columns.tolist()}")
        else:
            st.info("No data available for comparison.")
            st.session_state.debug_messages.append("chart_df is empty.")

# Debug Information
with st.expander("Debug Information"):
    if st.session_state.debug_messages:
        for msg in st.session_state.debug_messages:
            st.write(msg)
    else:
        st.write("No debug messages.")
