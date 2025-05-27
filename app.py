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

# Helper function to map room type keys to descriptive names
def get_display_room_type(room_key):
    if room_key in room_view_legend:
        return room_view_legend[room_key]
    
    parts = room_key.split()
    if not parts:
        return room_key

    base = " ".join(parts[:-1]) if len(parts) > 1 else parts[0]
    view = parts[-1]
    if view in room_view_legend:
        view_display = room_view_legend[view]
    else:
        view_display = view

    if len(parts) > 2 and parts[-2] == "PH":
        base = " ".join(parts[:-2])
        view = " ".join(parts[-2:])
        view_display = room_view_legend.get(view, view)

    return f"{base} {view_display}"

# Helper function to map display name back to internal key
def get_internal_room_key(display_name):
    reverse_legend = {v: k for k, v in room_view_legend.items()}
    if display_name in reverse_legend:
        return reverse_legend[display_name]

    parts = display_name.split()
    if not parts:
        return display_name

    base_parts = []
    view_parts = []
    found_view = False
    for part in parts:
        if part in ["Mountain", "Ocean", "Penthouse", "Garden", "Front"] and not found_view:
            found_view = True
            view_parts.append(part)
        elif found_view:
            view_parts.append(part)
        else:
            base_parts.append(part)

    base = " ".join(base_parts)
    view_display = " ".join(view_parts)
    view = reverse_legend.get(view_display, view_display)

    return f"{base} {view}"

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

    # Determine season for the specific date
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

    # Check for holiday week
    is_holiday = False
    is_holiday_start = False
    holiday_name = None
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
    all_display_room_types = []
    normal_room_types = list(reference_points[resort][season][day_category].keys())
    normal_display_room_types = [get_display_room_type(rt) for rt in normal_room_types]
    all_room_types.extend(normal_room_types)
    all_display_room_types.extend(normal_display_room_types)
    if ap_room_types:
        all_room_types.extend(ap_room_types)
        all_display_room_types.extend([get_display_room_type(rt) for rt in ap_room_types])

    display_to_internal = dict(zip(all_display_room_types, all_room_types))

    for display_room_type, room_type in display_to_internal.items():
        points = 0
        is_ap_room = room_type in ap_room_types

        if is_ap_room:
            points_ref = reference_points[resort]["AP Rooms"][ap_day_category]
            points = points_ref.get(room_type, 0)
            st.session_state.debug_messages.append(f"Applying AP room points for {room_type} ({display_room_type}) on {date_str} ({ap_day_category}): {points}")
        else:
            if is_holiday and is_holiday_start:
                points_ref = reference_points[resort]["Holiday Week"].get(holiday_name, {})
                points = points_ref.get(room_type, 0)
                st.session_state.debug_messages.append(f"Applying Holiday Week points for {holiday_name} on {date_str} for {display_room_type}: {points}")
            elif is_holiday and not is_holiday_start:
                points = 0
                st.session_state.debug_messages.append(f"Zero points for {date_str} (part of holiday week {holiday_name}) for {display_room_type}")
            else:
                points_ref = reference_points[resort][season][day_category]
                points = points_ref.get(room_type, 0)
                st.session_state.debug_messages.append(f"Applying {season} {day_category} points for {date_str} for {display_room_type}: {points}")

        entry[display_room_type] = points
        st
