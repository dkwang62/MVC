import streamlit as st
import math
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff

# Initialize session state for debug messages
if "debug_messages" not in st.session_state:
    st.session_state.debug_messages = []

# Hardcoded data (unchanged)
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
    "Penthouse": "Penthouse"
}

reference_points = {
    "Kauai Beach Club": {
        "Low Season": {
            "Fri-Sat": {
                "Parlor Garden View": 175,
                "Parlor Ocean View": 225,
                "Parlor Ocean Front": 275,
                "Studio Garden View": 275,
                "Studio Ocean View": 350,
                "Studio Ocean Front": 425,
                "1BR Garden View": 400,
                "1BR Ocean View": 500,
                "1BR Ocean Front": 600,
                "2BR Ocean View": 750,
                "2BR Ocean Front": 925
            },
            "Sun-Thu": {
                "Parlor Garden View": 125,
                "Parlor Ocean View": 175,
                "Parlor Ocean Front": 200,
                "Studio Garden View": 200,
                "Studio Ocean View": 250,
                "Studio Ocean Front": 300,
                "1BR Garden View": 275,
                "1BR Ocean View": 350,
                "1BR Ocean Front": 425,
                "2BR Ocean View": 525,
                "2BR Ocean Front": 650
            }
        },
        "High Season": {
            "Fri-Sat": {
                "Parlor Garden View": 200,
                "Parlor Ocean View": 275,
                "Parlor Ocean Front": 300,
                "Studio Garden View": 300,
                "Studio Ocean View": 400,
                "Studio Ocean Front": 475,
                "1BR Garden View": 450,
                "1BR Ocean View": 575,
                "1BR Ocean Front": 700,
                "2BR Ocean View": 875,
                "2BR Ocean Front": 1075
            },
            "Sun-Thu": {
                "Parlor Garden View": 150,
                "Parlor Ocean View": 200,
                "Parlor Ocean Front": 225,
                "Studio Garden View": 225,
                "Studio Ocean View": 275,
                "Studio Ocean Front": 350,
                "1BR Garden View": 325,
                "1BR Ocean View": 400,
                "1BR Ocean Front": 500,
                "2BR Ocean View": 625,
                "2BR Ocean Front": 750
            }
        },
        "Holiday Week": {
            "Presidents Day": {
                "Parlor Garden View": 1375,
                "Parlor Ocean View": 1600,
                "Parlor Ocean Front": 1900,
                "Studio Garden View": 1900,
                "Studio Ocean View": 2350,
                "Studio Ocean Front": 2750,
                "1BR Garden View": 2575,
                "1BR Ocean View": 3325,
                "1BR Ocean Front": 4075,
                "2BR Ocean View": 5100,
                "2BR Ocean Front": 6250
            },
            "Easter": {
                "Parlor Garden View": 1375,
                "Parlor Ocean View": 1600,
                "Parlor Ocean Front": 1900,
                "Studio Garden View": 1900,
                "Studio Ocean View": 2350,
                "Studio Ocean Front": 2750,
                "1BR Garden View": 2575,
                "1BR Ocean View": 3325,
                "1BR Ocean Front": 4075,
                "2BR Ocean View": 5100,
                "2BR Ocean Front": 6250
            },
            "Independence Day": {
                "Parlor Garden View": 1150,
                "Parlor Ocean View": 1550,
                "Parlor Ocean Front": 1725,
                "Studio Garden View": 1725,
                "Studio Ocean View": 2175,
                "Studio Ocean Front": 2700,
                "1BR Garden View": 2525,
                "1BR Ocean View": 3150,
                "1BR Ocean Front": 3900,
                "2BR Ocean View": 4875,
                "2BR Ocean Front": 5900
            },
            "Thanksgiving": {
                "Parlor Garden View": 975,
                "Parlor Ocean View": 1325,
                "Parlor Ocean Front": 1550,
                "Studio Garden View": 1550,
                "Studio Ocean View": 1950,
                "Studio Ocean Front": 2350,
                "1BR Garden View": 2175,
                "1BR Ocean View": 2750,
                "1BR Ocean Front": 3325,
                "2BR Ocean View": 4125,
                "2BR Ocean Front": 5100
            },
            "Thanksgiving 2": {
                "Parlor Garden View": 1375,
                "Parlor Ocean View": 1600,
                "Parlor Ocean Front": 1900,
                "Studio Garden View": 1900,
                "Studio Ocean View": 2350,
                "Studio Ocean Front": 2750,
                "1BR Garden View": 2575,
                "1BR Ocean View": 3325,
                "1BR Ocean Front": 4075,
                "2BR Ocean View": 5100,
                "2BR Ocean Front": 6250
            },
            "Christmas": {
                "Parlor Garden View": 1375,
                "Parlor Ocean View": 1600,
                "Parlor Ocean Front": 1900,
                "Studio Garden View": 1900,
                "Studio Ocean View": 2350,
                "Studio Ocean Front": 2750,
                "1BR Garden View": 2575,
                "1BR Ocean View": 3325,
                "1BR Ocean Front": 4075,
                "2BR Ocean View": 5100,
                "2BR Ocean Front": 6250
            },
            "New Year's Eve/Day": {
                "Parlor Garden View": 1550,
                "Parlor Ocean View": 1775,
                "Parlor Ocean Front": 2125,
                "Studio Garden View": 2125,
                "Studio Ocean View": 2575,
                "Studio Ocean Front": 3100,
                "1BR Garden View": 2925,
                "1BR Ocean View": 3725,
                "1BR Ocean Front": 4475,
                "2BR Ocean View": 5675,
                "2BR Ocean Front": 6825
            }
        }
    },
    "Ko Olina Beach Club": {
        "Low Season": {
            "Fri-Sat": {
                "Studio Mountain View": 340,
                "Studio Ocean View": 360,
                "Studio Penthouse Mountain View": 340,
                "Studio Penthouse Ocean View": 475,
                "1BR Mountain View": 575,
                "1BR Ocean View": 625,
                "1BR Penthouse Mountain View": 575,
                "1BR Penthouse Ocean View": 850,
                "2BR Mountain View": 775,
                "2BR Ocean View": 900,
                "2BR Penthouse Mountain View": 775,
                "2BR Penthouse Ocean View": 1075,
                "3BR Mountain View": 925,
                "3BR Ocean View": 1175
            },
            "Sun-Thu": {
                "Studio Mountain View": 205,
                "Studio Ocean View": 270,
                "Studio Penthouse Mountain View": 205,
                "Studio Penthouse Ocean View": 295,
                "1BR Mountain View": 355,
                "1BR Ocean View": 465,
                "1BR Penthouse Mountain View": 355,
                "1BR Penthouse Ocean View": 550,
                "2BR Mountain View": 500,
                "2BR Ocean View": 625,
                "2BR Penthouse Mountain View": 500,
                "2BR Penthouse Ocean View": 750,
                "3BR Mountain View": 650,
                "3BR Ocean View": 825
            }
        },
        "High Season": {
            "Fri-Sat": {
                "Studio Mountain View": 360,
                "Studio Ocean View": 430,
                "Studio Penthouse Mountain View": 360,
                "Studio Penthouse Ocean View": 520,
                "1BR Mountain View": 625,
                "1BR Ocean View": 725,
                "1BR Penthouse Mountain View": 625,
                "1BR Penthouse Ocean View": 925,
                "2BR Mountain View": 850,
                "2BR Ocean View": 1050,
                "2BR Penthouse Mountain View": 850,
                "2BR Penthouse Ocean View": 1250,
                "3BR Mountain View": 1075,
                "3BR Ocean View": 1375
            },
            "Sun-Thu": {
                "Studio Mountain View": 250,
                "Studio Ocean View": 295,
                "Studio Penthouse Mountain View": 250,
                "Studio Penthouse Ocean View": 340,
                "1BR Mountain View": 415,
                "1BR Ocean View": 525,
                "1BR Penthouse Mountain View": 415,
                "1BR Penthouse Ocean View": 625,
                "2BR Mountain View": 575,
                "2BR Ocean View": 725,
                "2BR Penthouse Mountain View": 575,
                "2BR Penthouse Ocean View": 875,
                "3BR Mountain View": 750,
                "3BR Ocean View": 975
            }
        },
        "Holiday Week": {
            "Presidents Day": {
                "Studio Mountain View": 2160,
                "Studio Ocean View": 2475,
                "Studio Penthouse Mountain View": 2160,
                "Studio Penthouse Ocean View": 2880,
                "1BR Mountain View": 3525,
                "1BR Ocean View": 4300,
                "1BR Penthouse Mountain View": 3525,
                "1BR Penthouse Ocean View": 5275,
                "2BR Mountain View": 4800,
                "2BR Ocean View": 6025,
                "2BR Penthouse Mountain View": 4800,
                "2BR Penthouse Ocean View": 7225,
                "3BR Mountain View": 6250,
                "3BR Ocean View": 8025
            },
            "Easter": {
                "Studio Mountain View": 2160,
                "Studio Ocean View": 2475,
                "Studio Penthouse Mountain View": 2160,
                "Studio Penthouse Ocean View": 2880,
                "1BR Mountain View": 3525,
                "1BR Ocean View": 4300,
                "1BR Penthouse Mountain View": 3525,
                "1BR Penthouse Ocean View": 5275,
                "2BR Mountain View": 4800,
                "2BR Ocean View": 6025,
                "2BR Penthouse Mountain View": 4800,
                "2BR Penthouse Ocean View": 7225,
                "3BR Mountain View": 6250,
                "3BR Ocean View": 8025
            },
            "Independence Day": {
                "Studio Mountain View": 1960,
                "Studio Ocean View": 2320,
                "Studio Penthouse Mountain View": 1960,
                "Studio Penthouse Ocean View": 2725,
                "1BR Mountain View": 3325,
                "1BR Ocean View": 4100,
                "1BR Penthouse Mountain View": 3325,
                "1BR Penthouse Ocean View": 5025,
                "2BR Mountain View": 4575,
                "2BR Ocean View": 5725,
                "2BR Penthouse Mountain View": 4575,
                "2BR Penthouse Ocean View": 6875,
                "3BR Mountain View": 5900,
                "3BR Ocean View": 2250
            },
            "Thanksgiving": {
                "Studio Mountain View": 1690,
                "Studio Ocean View": 2070,
                "Studio Penthouse Mountain View": 1690,
                "Studio Penthouse Ocean View": 2410,
                "1BR Mountain View": 2950,
                "1BR Ocean View": 3600,
                "1BR Penthouse Mountain View": 2950,
                "1BR Penthouse Ocean View": 4450,
                "2BR Mountain View": 4050,
                "2BR Ocean View": 4925,
                "2BR Penthouse Mountain View": 4050,
                "2BR Penthouse Ocean View": 5900,
                "3BR Mountain View": 5100,
                "3BR Ocean View": 6475
            },
            "Thanksgiving 2": {
                "Studio Mountain View": 2160,
                "Studio Ocean View": 2475,
                "Studio Penthouse Mountain View": 2160,
                "Studio Penthouse Ocean View": 2880,
                "1BR Mountain View": 3525,
                "1BR Ocean View": 4300,
                "1BR Penthouse Mountain View": 3525,
                "1BR Penthouse Ocean View": 5275,
                "2BR Mountain View": 4800,
                "2BR Ocean View": 6025,
                "2BR Penthouse Mountain View": 4800,
                "2BR Penthouse Ocean View": 7225,
                "3BR Mountain View": 6250,
                "3BR Ocean View": 8025
            },
            "Christmas": {
                "Studio Mountain View": 2160,
                "Studio Ocean View": 2475,
                "Studio Penthouse Mountain View": 2160,
                "Studio Penthouse Ocean View": 2880,
                "1BR Mountain View": 3525,
                "1BR Ocean View": 4300,
                "1BR Penthouse Mountain View": 3525,
                "1BR Penthouse Ocean View": 5275,
                "2BR Mountain View": 4800,
                "2BR Ocean View": 6025,
                "2BR Penthouse Mountain View": 4800,
                "2BR Penthouse Ocean View": 7225,
                "3BR Mountain View": 6250,
                "3BR Ocean View": 8025
            },
            "New Year's Eve/Day": {
                "Studio Mountain View": 2365,
                "Studio Ocean View": 2835,
                "Studio Penthouse Mountain View": 2365,
                "Studio Penthouse Ocean View": 3330,
                "1BR Mountain View": 4075,
                "1BR Ocean View": 4975,
                "1BR Penthouse Mountain View": 4075,
                "1BR Penthouse Ocean View": 6100,
                "2BR Mountain View": 5550,
                "2BR Ocean View": 6875,
                "2BR Penthouse Mountain View": 5550,
                "2BR Penthouse Ocean View": 8250,
                "3BR Mountain View": 7100,
                "3BR Ocean View": 9175
            }
        }
    }
}

# Function to generate data structure
@st.cache_data
def generate_data(resort, date):
    date_str = date.strftime("%Y-%m-%d")
    year = date.strftime("%Y")
    day_of_week = date.strftime("%a")
    is_fri_sat = day_of_week in ["Friday", "Saturday"]
    day_category = "Fri-Sat" if is_fri_sat else "Sun-Thu"
    entry = {}

    # Check for holiday week
    is_holiday = False
    is_holiday_start = False
    holiday_name = None
    try:
        for h_name, [start, end] in holiday_weeks[resort][year].items():
            h_start = datetime.strptime(start, "%Y-%m-%d").date()
            h_end = datetime.strptime(end, "%Y-%m-%d").date()
            if h_start <= date <= h_end:
                is_holiday = True
                holiday_name = h_name
                if date == h_start:
                    is_holiday_start = True
                break
    except ValueError as e:
        st.session_state.debug_messages.append(f"Invalid holiday date in {resort}, {year}, {h_name}: {e}")

    # Determine season
    season = "Low Season"
    try:
        for s_type in ["Low Season", "High Season"]:
            for [start, end] in season_blocks[resort][year][s_type]:
                s_start = datetime.strptime(start, "%Y-%m-%d").date()
                s_end = datetime.strptime(end, "%Y-%m-%d").date()
                if s_start <= date <= s_end:
                    season = s_type
                    break
            if season == s_type:
                break
    except ValueError as e:
        st.session_state.debug_messages.append(f"Invalid season date in {resort}, {year}, {s_type}: {e}")

    # Assign points
    if is_holiday and is_holiday_start:
        points_ref = reference_points[resort]["Holiday Week"].get(holiday_name, {})
    elif is_holiday and not is_holiday_start:
        points_ref = {room: 0 for room in reference_points[resort]["Holiday Week"].get(holiday_name, {})}
    else:
        points_ref = reference_points[resort][season][day_category]
    
    for room_type, points in points_ref.items():
        entry[room_type] = points

    # Add flags
    if is_holiday:
        entry["HolidayWeek"] = True
        entry["holiday_name"] = holiday_name
    if is_holiday_start:
        entry["HolidayWeekStart"] = True

    return entry

# Function to adjust date range for holiday weeks
def adjust_date_range(resort, checkin_date, num_nights):
    year_str = str(checkin_date.year)
    stay_end = checkin_date + timedelta(days=num_nights - 1)
    holiday_ranges = []
    
    # Find all holiday weeks that overlap with the stay
    for h_name, [start, end] in holiday_weeks[resort][year_str].items():
        h_start = datetime.strptime(start, "%Y-%m-%d").date()
        h_end = datetime.strptime(end, "%Y-%m-%d").date()
        if (h_start <= stay_end) and (h_end >= checkin_date):
            holiday_ranges.append((h_start, h_end))
    
    if holiday_ranges:
        # Extend to include the latest holiday end date
        latest_holiday_end = max(h_end for _, h_end in holiday_ranges)
        adjusted_end = max(stay_end, latest_holiday_end)
        adjusted_nights = (adjusted_end - checkin_date).days + 1
        st.session_state.debug_messages.append(f"Adjusted date range to include holiday week: {checkin_date} to {adjusted_end}")
        return checkin_date, adjusted_nights
    return checkin_date, num_nights

# Function to create Gantt chart
def create_gantt_chart(resort, year):
    gantt_data = []
    year_str = str(year)
    
    # Add holiday weeks
    for h_name, [start, end] in holiday_weeks[resort][year_str].items():
        gantt_data.append({
            "Task": h_name,
            "Start": start,
            "Finish": end,
            "Type": "Holiday"
        })
    
    # Add season blocks
    for season_type in ["Low Season", "High Season"]:
        for i, [start, end] in enumerate(season_blocks[resort][year_str][season_type], 1):
            gantt_data.append({
                "Task": f"{season_type} {i}",
                "Start": start,
                "Finish": end,
                "Type": season_type
            })
    
    df = pd.DataFrame(gantt_data)
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
    - **Holiday weeks**: If your stay includes any part of a holiday week, the entire holiday week is included in the date range. Points and rent are calculated only for the first day of the holiday week; other days in the holiday week have zero points and rent.
    """)

# Year selection for Gantt chart
year_options = ["2025", "2026"]
default_year = str(checkin_date.year) if "checkin_date" in locals() else "2025"
year_select = st.selectbox("Select Year for Calendar", options=year_options, index=year_options.index(default_year))

# Display Gantt chart
resort_display = st.selectbox("Select Resort", options=display_resorts, key="resort_select")
resort = reverse_aliases.get(resort_display, resort_display)
st.session_state.debug_messages.append(f"Selected resort: {resort}")
st.subheader(f"Season and Holiday Calendar ({year_select})")
gantt_fig = create_gantt_chart(resort, year_select)
st.plotly_chart(gantt_fig, use_container_width=True)

# Get room types
sample_date = datetime(2025, 1, 3).date()
sample_entry = generate_data(resort, sample_date)
room_types = [k for k in sample_entry if k not in ("HolidayWeek", "HolidayWeekStart", "holiday_name")]
if not room_types:
    st.error(f"No room types found for {resort}.")
    st.session_state.debug_messages.append(f"No room types for {resort}")
    st.stop()

room_type = st.selectbox("Select Room Type", options=room_types, key="room_type_select")
compare_rooms = st.multiselect("Compare With Other Room Types", options=[r for r in room_types if r != room_type])

checkin_date = st.date_input("Check-in Date", min_value=datetime(2024, 12, 27).date(), max_value=datetime(2026, 12, 31).date(), value=datetime(2025, 7, 1).date())
num_nights = st.number_input("Number of Nights", min_value=1, max_value=30, value=7)

# Adjust date range for holidays
checkin_date, adjusted_nights = adjust_date_range(resort, checkin_date, num_nights)
if adjusted_nights != num_nights:
    st.info(f"Date range adjusted to include full holiday week: {num_nights} nights extended to {adjusted_nights} nights.")

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
        if points == 0:
            st.session_state.debug_messages.append(f"No points for {room_type} on {date_str}, using reference: {points}")
        discounted_points = math.floor(points * discount_multiplier)
        rent = math.ceil(points * rate_per_point)
        breakdown.append({
            "Date": date_str,
            "Day": date.strftime("%a"),
            "Points": discounted_points,
            "Rent": rent,
            "Holiday": entry.get("holiday_name", "No")
        })
        total_points += discounted_points
        total_rent += rent

    return breakdown, total_points, total_rent

def compare_room_types(resort, room_types, checkin_date, num_nights, discount_multiplier, discount_percent):
    rate_per_point = 0.81 if checkin_date.year == 2025 else 0.86
    compare_data = []
    chart_data = []
    
    # Find holiday weeks in the stay
    holiday_ranges = []
    year_str = str(checkin_date.year)
    stay_start = checkin_date
    stay_end = checkin_date + timedelta(days=num_nights - 1)
    for h_name, [start, end] in holiday_weeks[resort][year_str].items():
        h_start = datetime.strptime(start, "%Y-%m-%d").date()
        h_end = datetime.strptime(end, "%Y-%m-%d").date()
        if (h_start <= stay_end) and (h_end >= stay_start):
            holiday_ranges.append((h_start, h_end))
    
    # Determine date range for chart
    all_dates = []
    for i in range(num_nights):
        date = checkin_date + timedelta(days=i)
        all_dates.append(date)
    for h_start, h_end in holiday_ranges:
        current_date = h_start
        while current_date <= h_end:
            if current_date not in all_dates:
                all_dates.append(current_date)
            current_date += timedelta(days=1)
    all_dates = sorted(list(set(all_dates)))
    
    for room in room_types:
        for date in all_dates:
            date_str = date.strftime("%Y-%m-%d")
            day_of_week = date.strftime("%a")
            entry = generate_data(resort, date)
            
            points = entry.get(room, reference_points_resort.get(room, 0))
            if points == 0:
                st.session_state.debug_messages.append(f"No points for {room} on {date_str}, using reference: {points}")
            discounted_points = math.floor(points * discount_multiplier)
            rent = math.ceil(points * rate_per_point)
            compare_data.append({
                "Date": date_str,
                "Room Type": room,
                "Estimated Rent ($)": f"${rent}"
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
    
    compare_df = pd.DataFrame(compare_data)
    compare_df_pivot = compare_df.pivot_table(index="Date", columns="Room Type", values="Estimated Rent ($)", aggfunc="first").reset_index()
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
        all_rooms = [room_type] + compare_rooms
        chart_df, compare_df = compare_room_types(
            resort, all_rooms, checkin_date, adjusted_nights, discount_multiplier, discount_percent
        )
        st.dataframe(compare_df, use_container_width=True)

        compare_csv = compare_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Room Comparison as CSV",
            data=compare_csv,
            file_name=f"{resort}_room_comparison.csv",
            mime="text/csv"
        )

        # Bar Chart
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
                    color="Holiday",
                    facet_col="Room Type",
                    barmode="group",
                    title=title,
                    labels={"Rent": "Estimated Rent ($)", "Day": "Day of Week"},
                    height=400,
                    text="Rent",
                    text_auto=True
                )
                fig.update_traces(texttemplate="$%{text}", textposition="auto")
                fig.update_xaxes(
                    categoryorder="array",
                    categoryarray=[d.strftime("%a") for d in sorted(chart_df["Date"].unique())]
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
