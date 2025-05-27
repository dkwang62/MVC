import streamlit as st
import json
import math
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

# --- Configuration ---
st.set_page_config(page_title="Marriott Points Calculator", layout="wide")
st.title("\U0001F3DD Marriott Vacation Club Points Calculator")

# --- Room View Descriptions ---
room_view_legend = {
    "GV": "Garden View", "OV": "Ocean View", "OF": "Ocean Front",
    "MA": "Mountain View", "MK": "Ocean View",
    "PH MA": "Penthouse Mountain View", "PH MK": "Penthouse Ocean View"
}

# --- Season and Holiday Data ---
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
            "Christmas": ["2025-12-19", "2025-12-24"],
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
            "Christmas": ["2025-12-19", "2025-12-24"],
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

# --- Reference Points ---
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
            "Presidents Day": {
                "Parlor GV": 1375,
                "Parlor OV": 1600,
                "Parlor OF": 1900,
                "Studio GV": 1900,
                "Studio OV": 2350,
                "Studio OF": 2750,
                "1BR GV": 2575,
                "1BR OV": 3325,
                "1BR OF": 4075,
                "2BR OV": 5100,
                "2BR OF": 6250
            },
            "Easter": {
                "Parlor GV": 1375,
                "Parlor OV": 1600,
                "Parlor OF": 1900,
                "Studio GV": 1900,
                "Studio OV": 2350,
                "Studio OF": 2750,
                "1BR GV": 2575,
                "1BR OV": 3325,
                "1BR OF": 4075,
                "2BR OV": 5100,
                "2BR OF": 6250
            },
            "Independence Day": {
                "Parlor GV": 1150,
                "Parlor OV": 1550,
                "Parlor OF": 1725,
                "Studio GV": 1725,
                "Studio OV": 2175,
                "Studio OF": 2700,
                "1BR GV": 2525,
                "1BR OV": 3150,
                "1BR OF": 3900,
                "2BR OV": 4875,
                "2BR OF": 5900
            },
            "Thanksgiving": {
                "Parlor GV": 975,
                "Parlor OV": 1325,
                "Parlor OF": 1550,
                "Studio GV": 1550,
                "Studio OV": 1950,
                "Studio OF": 2350,
                "1BR GV": 2175,
                "1BR OV": 2750,
                "1BR OF": 3325,
                "2BR OV": 4125,
                "2BR OF": 5100
            },
            "Thanksgiving 2": {
                "Parlor GV": 1375,
                "Parlor OV": 1600,
                "Parlor OF": 1900,
                "Studio GV": 1900,
                "Studio OV": 2350,
                "Studio OF": 2750,
                "1BR GV": 2575,
                "1BR OV": 3325,
                "1BR OF": 4075,
                "2BR OV": 5100,
                "2BR OF": 6250
            },
            "Christmas": {
                "Parlor GV": 1375,
                "Parlor OV": 1600,
                "Parlor OF": 1900,
                "Studio GV": 1900,
                "Studio OV": 2350,
                "Studio OF": 2750,
                "1BR GV": 2575,
                "1BR OV": 3325,
                "1BR OF": 4075,
                "2BR OV": 5100,
                "2BR OF": 6250
            },
            "New Year's Eve/Day": {
                "Parlor GV": 1550,
                "Parlor OV": 1775,
                "Parlor OF": 2125,
                "Studio GV": 2125,
                "Studio OV": 2575,
                "Studio OF": 3100,
                "1BR GV": 2925,
                "1BR OV": 3725,
                "1BR OF": 4475,
                "2BR OV": 5675,
                "2BR OF": 6825
            }
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
            "Presidents Day": {
                "Studio MA": 2160,
                "Studio MK": 2475,
                "Studio PH MA": 2160,
                "Studio PH MK": 2880,
                "1BR MA": 3525,
                "1BR MK": 4300,
                "1BR PH MA": 3525,
                "1BR PH MK": 5275,
                "2BR MA": 4800,
                "2BR MK": 6025,
                "2BR PH MA": 4800,
                "2BR PH MK": 7225,
                "3BR MA": 6250,
                "3BR MK": 8025
            },
            "Easter": {
                "Studio MA": 2160,
                "Studio MK": 2475,
                "Studio PH MA": 2160,
                "Studio PH MK": 2880,
                "1BR MA": 3525,
                "1BR MK": 4300,
                "1BR PH MA": 3525,
                "1BR PH MK": 5275,
                "2BR MA": 4800,
                "2BR MK": 6025,
                "2BR PH MA": 4800,
                "2BR PH MK": 7225,
                "3BR MA": 6250,
                "3BR MK": 8025
            },
            "Independence Day": {
                "Studio MA": 1960,
                "Studio MK": 2320,
                "Studio PH MA": 1960,
                "Studio PH MK": 2725,
                "1BR MA": 3325,
                "1BR MK": 4100,
                "1BR PH MA": 3325,
                "1BR PH MK": 5025,
                "2BR MA": 4575,
                "2BR MK": 5725,
                "2BR PH MA": 4575,
                "2BR PH MK": 6875,
                "3BR MA": 5900,
                "3BR MK": 7625
            },
            "Thanksgiving": {
                "Studio MA": 1690,
                "Studio MK": 2070,
                "Studio PH MA": 1690,
                "Studio PH MK": 2410,
                "1BR MA": 2950,
                "1BR MK": 3600,
                "1BR PH MA": 2950,
                "1BR PH MK": 4450,
                "2BR MA": 4050,
                "2BR MK": 4925,
                "2BR PH MA": 4050,
                "2BR PH MK": 5900,
                "3BR MA": 5100,
                "3BR MK": 6475
            },
            "Thanksgiving 2": {
                "Studio MA": 2160,
                "Studio MK": 2475,
                "Studio PH MA": 2160,
                "Studio PH MK": 2880,
                "1BR MA": 3525,
                "1BR MK": 4300,
                "1BR PH MA": 3525,
                "1BR PH MK": 5275,
                "2BR MA": 4800,
                "2BR MK": 6025,
                "2BR PH MA": 4800,
                "2BR PH MK": 7225,
                "3BR MA": 6250,
                "3BR MK": 8025
            },
            "Christmas": {
                "Studio MA": 2160,
                "Studio MK": 2475,
                "Studio PH MA": 2160,
                "Studio PH MK": 2880,
                "1BR MA": 3525,
                "1BR MK": 4300,
                "1BR PH MA": 3525,
                "1BR PH MK": 5275,
                "2BR MA": 4800,
                "2BR MK": 6025,
                "2BR PH MA": 4800,
                "2BR PH MK": 7225,
                "3BR MA": 6250,
                "3BR MK": 8025
            },
            "New Year's Eve/Day": {
                "Studio MA": 2365,
                "Studio MK": 2835,
                "Studio PH MA": 2365,
                "Studio PH MK": 3330,
                "1BR MA": 4075,
                "1BR MK": 4975,
                "1BR PH MA": 4075,
                "1BR PH MK": 6100,
                "2BR MA": 5550,
                "2BR MK": 6875,
                "2BR PH MA": 5550,
                "2BR PH MK": 8250,
                "3BR MA": 7100,
                "3BR MK": 9175
            }
        }
    }
}

# Initialize session state for debug messages
if "debug_messages" not in st.session_state:
    st.session_state.debug_messages = []

# --- Load JSON Data ---
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

# --- Helper Functions ---
def describe_room_type(room_code):
    for key, label in room_view_legend.items():
        if room_code.endswith(" " + key):
            return f"{room_code} ({label})"
        elif room_code == key:
            return f"{room_code} ({label})"
    return room_code

def get_day_type(date_obj):
    weekday = date_obj.weekday()
    return "Fri-Sat" if weekday in (4, 5) else "Sun-Thu"

def classify_date(resort, date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    year = str(date_obj.year)
    for holiday_name, (start_str, end_str) in holiday_weeks.get(resort, {}).get(year, {}).items():
        start = datetime.strptime(start_str, "%Y-%m-%d")
        end = datetime.strptime(end_str, "%Y-%m-%d")
        if start <= date_obj <= end:
            return {"season": "Holiday Week", "holiday": holiday_name}
    for season_type in ["High Season", "Low Season"]:
        for start_str, end_str in season_blocks.get(resort, {}).get(year, {}).get(season_type, []):
            start = datetime.strptime(start_str, "%Y-%m-%d")
            end = datetime.strptime(end_str, "%Y-%m-%d")
            if start <= date_obj <= end:
                return {"season": season_type, "holiday": None}
    return {"season": "Unknown", "holiday": None}

def lookup_points_formula(resort, room_type, date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    year = str(date_obj.year)
    tag = classify_date(resort, date_str)
    if tag["season"] == "Holiday Week":
        holiday = tag["holiday"]
        return reference_points[resort]["Holiday Week"].get(holiday, {}).get(room_type)
    day_type = get_day_type(date_obj)
    season = tag["season"]
    if season in reference_points[resort]:
        return reference_points[resort][season].get(day_type, {}).get(room_type)
    return None

def calculate_formula_based(resort, room_type, checkin_date, num_nights, discount_multiplier):
    results = []
    total_points = 0
    total_rent = 0
    rate_per_point = 0.81 if checkin_date.year == 2025 else 0.86

    for i in range(num_nights):
        date = checkin_date + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        points = lookup_points_formula(resort, room_type, date_str)
        tag = classify_date(resort, date_str)
        if points is None:
            results.append({
                "Date": date_str,
                "Day": date.strftime("%a"),
                "Season": "Unknown",
                "Holiday": "-",
                "Points": 0,
                "Rent": 0
            })
            continue
        discount_pts = math.floor(points * discount_multiplier)
        rent = math.ceil(points * rate_per_point)
        results.append({
            "Date": date_str,
            "Day": date.strftime("%a"),
            "Season": tag["season"],
            "Holiday": tag["holiday"] or "-",
            "Points": discount_pts,
            "Rent": rent
        })
        total_points += discount_pts
        total_rent += rent
    return results, total_points, total_rent

def calculate_json_based(data, resort, room_type, checkin_date, num_nights, discount_multiplier):
    breakdown = []
    total_points = 0
    total_rent = 0
    rate_per_point = 0.81 if checkin_date.year == 2025 else 0.86
    reference_points = data[resort].get(next(iter(data[resort])), {}).get(room_type)

    for i in range(num_nights):
        date = checkin_date + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        entry = data[resort].get(date_str, {})
        points = entry.get(room_type, reference_points)
        if points is None:
            points = reference_points
            st.session_state.debug_messages.append(f"Using reference points for {room_type} on {date_str}: {points}")
        discounted_points = math.floor(points * discount_multiplier)
        rent = math.ceil(points * rate_per_point)
        breakdown.append({
            "Date": date_str,
            "Day": date.strftime("%a"),
            "Points": discounted_points,
            "Rent": rent,  # Changed to numeric value
            "Holiday": "Yes" if entry.get("HolidayWeek", False) else "No"
        })
        total_points += discounted_points
        total_rent += rent
    return breakdown, total_points, total_rent

def summarize_holiday_weeks(data, resort, room_type, checkin_date, num_nights, reference_points, discount_multiplier):
    summaries = []
    rate_per_point = 0.81 if checkin_date.year == 2025 else 0.86
    search_start = checkin_date - timedelta(days=7)
    search_end = checkin_date + timedelta(days=num_nights)
    current = search_start
    while current < search_end:
        date_str = current.strftime("%Y-%m-%d")
        entry = data[resort].get(date_str, {})
        if entry.get("HolidayWeekStart", False):
            start_str = date_str
            end_str = (current + timedelta(days=6)).strftime("%Y-%m-%d")
            week_range_start = current
            week_range_end = current + timedelta(days=6)
            if week_range_end >= checkin_date and week_range_start < search_end:
                points = entry.get(room_type, reference_points)
                if points is None:
                    points = reference_points
                    st.session_state.debug_messages.append(f"Using reference points for holiday week starting {start_str}: {points}")
                discounted_points = math.floor(points * discount_multiplier)
                rent = math.ceil(points * rate_per_point)
                summaries.append({
                    "Holiday Week Start": start_str,
                    "Holiday Week End": end_str,
                    "Points": discounted_points,
                    "Rent": rent
                })
        current += timedelta(days=1)
    return summaries

def create_timeline_df(resort, year):
    data = []
    for season, blocks in season_blocks[resort][year].items():
        for start, end in blocks:
            data.append({"Task": season, "Start": datetime.strptime(start, "%Y-%m-%d"), "End": datetime.strptime(end, "%Y-%m-%d"), "Type": "Season"})
    for holiday, (start, end) in holiday_weeks[resort][year].items():
        data.append({"Task": holiday, "Start": datetime.strptime(start, "%Y-%m-%d"), "End": datetime.strptime(end, "%Y-%m-%d"), "Type": "Holiday"})
    return pd.DataFrame(data)

# --- User Inputs ---
with st.expander("ℹ️ How Rent Is Calculated"):
    st.markdown("""
    - **Rent is estimated based on original points only.**
    - $0.81 per point for dates in **2025**
    - $0.86 per point for dates in **2026 and beyond**
    - Points are **rounded down** when discounts are applied.
    """)

calculation_method = st.radio("Calculation Method", ["JSON-Based (Default)", "Formula-Based"], index=0)

resort_display = st.selectbox("\U0001F3E8 Select Resort", options=display_resorts, key="resort_select")
resort = reverse_aliases.get(resort_display, resort_display)

# Validate resort exists
if resort not in data:
    st.error(f"Resort '{resort}' not found in Marriott_2025.json. Available resorts: {list(data.keys())}")
    st.session_state.debug_messages.append(f"Resort not found: {resort}. Available: {list(data.keys())}")
    st.stop()

# Get room types
sample_day = next(iter(data[resort].values()))
room_types = [k for k in sample_day if k not in ("Day", "HolidayWeek", "HolidayWeekStart")]
if not room_types:
    st.error(f"No room types found for {resort} in Marriott_2025.json.")
    st.session_state.debug_messages.append(f"No room types found for resort: {resort}")
    st.stop()

room_type_display = st.selectbox("\U0001F6CF Select Room Type", options=[describe_room_type(r) for r in sorted(room_types)], key="room_type_select")
room_type = room_type_display.split(" (")[0]

checkin_date = st.date_input("\U0001F4C5 Check-in Date", min_value=datetime(2024, 12, 27), max_value=datetime(2026, 12, 31), value=datetime(2025, 7, 1))
num_nights = st.number_input("\U0001F319 Number of Nights", min_value=1, max_value=30, value=7)

with st.sidebar:
    discount_percent = st.selectbox("Apply Points Discount", options=[0, 25, 30], index=0, format_func=lambda x: f"{x}%" if x else "No Discount")
discount_multiplier = 1 - (discount_percent / 100)

# --- Main Calculation ---
if st.button("\U0001F4CA Calculate"):
    reference_points_json = data[resort].get(next(iter(data[resort])), {}).get(room_type)
    if reference_points_json is None:
        st.error(f"No points data found for {room_type} in {resort}. Please select a different room type.")
        st.session_state.debug_messages.append(f"No points for {room_type} in {resort}")
        st.stop()

    if calculation_method == "Formula-Based":
        breakdown, total_points, total_rent = calculate_formula_based(resort, room_type, checkin_date, num_nights, discount_multiplier)
        holiday_weeks = []  # Formula-based method handles holidays in breakdown
    else:
        breakdown, total_points, total_rent = calculate_json_based(data, resort, room_type, checkin_date, num_nights, discount_multiplier)
        holiday_weeks = summarize_holiday_weeks(data, resort, room_type, checkin_date, num_nights, reference_points_json, discount_multiplier)

    # Log breakdown for debugging
    st.session_state.debug_messages.append(f"Breakdown: {breakdown}")

    # Display Results
    st.subheader("\U0001F4CB Stay Breakdown")
    if breakdown:
        df_breakdown = pd.DataFrame(breakdown)
        # Ensure numeric types
        df_breakdown["Points"] = pd.to_numeric(df_breakdown["Points"], errors="coerce")
        df_breakdown["Rent"] = pd.to_numeric(df_breakdown["Rent"], errors="coerce")
        st.dataframe(df_breakdown, use_container_width=True)
        csv_data = df_breakdown.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="\U0001F4C4 Download Breakdown as CSV",
            data=csv_data,
            file_name=f"{resort}_stay_breakdown.csv",
            mime="text/csv"
        )
    else:
        st.info("No data available for the selected period.")
        st.session_state.debug_messages.append("Breakdown is empty.")

    st.success(f"Total Points Used: {total_points}")
    st.success(f"Estimated Total Rent: ${total_rent}")

    if holiday_weeks:
        st.subheader("\U0001F389 Holiday Weeks Summary")
        df_holidays = pd.DataFrame(holiday_weeks)
        df_holidays["Points"] = pd.to_numeric(df_holidays["Points"], errors="coerce")
        df_holidays["Rent"] = pd.to_numeric(df_holidays["Rent"], errors="coerce")
        st.dataframe(df_holidays, use_container_width=True)

    # Rent Breakdown Chart
    if breakdown:
        st.subheader("📊 Rent Breakdown by Day")
        chart_df = pd.DataFrame(breakdown)
        # Log chart_df for debugging
        st.session_state.debug_messages.append(f"Chart DataFrame: {chart_df.to_dict()}")
        
        # Ensure Rent column is numeric
        chart_df["Rent"] = pd.to_numeric(chart_df["Rent"], errors="coerce")
        
        # Check if chart_df is not empty and has required columns
        if not chart_df.empty and all(col in chart_df.columns for col in ["Day", "Rent", "Holiday" if calculation_method == "JSON-Based" else "Season"]):
            try:
                fig = px.bar(
                    chart_df,
                    x="Day",
                    y="Rent",
                    color="Holiday" if calculation_method == "JSON-Based" else "Season",
                    barmode="group",
                    text="Rent",
                    labels={"Rent": "Estimated Rent ($)", "Day": "Day of Week"},
                    height=400
                )
                fig.update_traces(texttemplate="$%{text}", textposition="outside")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating chart: {str(e)}")
                st.session_state.debug_messages.append(f"Chart creation error: {str(e)}")
        else:
            st.warning("Cannot create chart: No valid data available.")
            st.session_state.debug_messages.append(f"Chart DataFrame empty or missing columns: {chart_df.columns.tolist()}")

    # Season and Holiday Timeline (only for formula-based)
    if calculation_method == "Formula-Based":
        st.subheader("📅 Season and Holiday Timeline")
        timeline_df = create_timeline_df(resort, str(checkin_date.year))
        timeline_fig = px.timeline(
            timeline_df,
            x_start="Start",
            x_end="End",
            y="Task",
            color="Type",
            color_discrete_map={"Season": "#636EFA", "Holiday": "#EF553B"}
        )
        timeline_fig.update_yaxes(categoryorder="category descending")
        st.plotly_chart(timeline_fig, use_container_width=True)

# Display debug messages
with st.expander("Debug Information"):
    if st.session_state.debug_messages:
        for msg in st.session_state.debug_messages:
            st.write(msg)
    else:
        st.write("No debug messages.")
