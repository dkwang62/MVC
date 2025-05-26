import streamlit as st
import math
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

# Season and holiday data
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

# Room view legend
room_view_legend = {
    "GV": "Garden View", "OV": "Ocean View", "OF": "Ocean Front",
    "MA": "Mountain View", "MK": "Ocean View",
    "PH MA": "Penthouse Mountain View", "PH MK": "Penthouse Ocean View"
}

# Points reference with corrected Unicode
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
import streamlit as st
import math
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

# --- Configuration ---
st.set_page_config(page_title="Marriott Points Calculator", layout="wide")
st.title("Marriott Vacation Club Points Calculator (Rules-Based)")

# --- Room View Descriptions ---
room_view_legend = {
    "GV": "Garden View", "OV": "Ocean View", "OF": "Ocean Front",
    "MA": "Mountain View", "MK": "Ocean View",
    "PH MA": "Penthouse Mountain View", "PH MK": "Penthouse Ocean View"
}

def describe_room_type(code):
    for k, label in room_view_legend.items():
        if code.endswith(" " + k):
            return f"{code} ({label})"
        elif code == k:
            return f"{code} ({label})"
    return code

def get_day_type(date_obj):
    return "Fri-Sat" if date_obj.weekday() in [4, 5] else "Sun-Thu"

# --- Season and Holiday Data ---
# [Use your full season_blocks and holiday_weeks dictionaries from previous code. They're too long to repeat here.]

# To save space, define `season_blocks` and `holiday_weeks` exactly as you did in your last message above.

# --- Reference Point Table (Trimmed Here for Brevity) ---
# Paste your entire `reference_points` dictionary from your full code here.

# --- Date Classification ---
def classify_date(resort, date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    year = str(date_obj.year)
    for holiday, (start, end) in holiday_weeks.get(resort, {}).get(year, {}).items():
        if datetime.strptime(start, "%Y-%m-%d") <= date_obj <= datetime.strptime(end, "%Y-%m-%d"):
            return {"season": "Holiday Week", "holiday": holiday}
    for season in ["High Season", "Low Season"]:
        for start, end in season_blocks.get(resort, {}).get(year, {}).get(season, []):
            if datetime.strptime(start, "%Y-%m-%d") <= date_obj <= datetime.strptime(end, "%Y-%m-%d"):
                return {"season": season, "holiday": None}
    return {"season": "Unknown", "holiday": None}

def lookup_points(resort, room, date_str):
    tag = classify_date(resort, date_str)
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    if tag["season"] == "Holiday Week":
        return reference_points[resort]["Holiday Week"].get(tag["holiday"], {}).get(room)
    elif tag["season"] in ["High Season", "Low Season"]:
        day_type = get_day_type(dt)
        return reference_points[resort][tag["season"]][day_type].get(room)
    return None

# --- User Inputs ---
resort = st.selectbox("Select Resort", list(reference_points.keys()))
room_set = set()
for day_rates in reference_points[resort]["Low Season"].values():
    room_set.update(day_rates.keys())
room_type_display = st.selectbox("Room Type", [describe_room_type(r) for r in sorted(room_set)])
room_code = room_type_display.split(" (")[0]

checkin_date = st.date_input("Check-in Date", value=datetime(2025, 7, 1))
nights = st.number_input("Number of Nights", min_value=1, max_value=30, value=7)

with st.sidebar:
    discount = st.selectbox("Points Discount", [0, 25, 30], index=0)
discount_multiplier = 1 - (discount / 100)

# --- Main Calculation ---
results = []
total_points = 0
total_rent = 0

for i in range(nights):
    date = checkin_date + timedelta(days=i)
    date_str = date.strftime("%Y-%m-%d")
    rate = lookup_points(resort, room_code, date_str)
    tag = classify_date(resort, date_str)
    if rate is None:
        results.append({
            "Date": date_str, "Day": date.strftime("%a"), "Season": "Unknown",
            "Holiday": "-", "Points": 0, "Rent ($)": 0
        })
        continue
    discount_pts = math.floor(rate * discount_multiplier)
    rent = math.ceil(rate * (0.81 if date.year == 2025 else 0.86))
    results.append({
        "Date": date_str,
        "Day": date.strftime("%a"),
        "Season": tag["season"],
        "Holiday": tag["holiday"] or "-",
        "Points": discount_pts,
        "Rent ($)": rent
    })
    total_points += discount_pts
    total_rent += rent

df = pd.DataFrame(results)
st.dataframe(df, use_container_width=True)
st.success(f"Total Points: {total_points}")
st.success(f"Estimated Rent: ${total_rent}")
st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), "stay_breakdown.csv")

# --- Holiday Summary ---
holiday_rows = [r for r in results if r["Season"] == "Holiday Week"]
if holiday_rows:
    st.subheader("🎉 Holiday Week Summary")
    st.dataframe(pd.DataFrame(holiday_rows), use_container_width=True)

# --- Rent Breakdown Chart ---
st.subheader("📊 Rent Breakdown by Day")
fig = px.bar(df, x="Day", y="Rent ($)", color="Season", barmode="group", text="Rent ($)")
fig.update_traces(texttemplate="$%{text}", textposition="outside")
st.plotly_chart(fig, use_container_width=True)

# --- Season and Holiday Timeline ---
def create_timeline_df(resort, year):
    data = []
    for season, blocks in season_blocks[resort][year].items():
        for start, end in blocks:
            data.append({"Task": season, "Start": datetime.strptime(start, "%Y-%m-%d"), "End": datetime.strptime(end, "%Y-%m-%d"), "Type": "Season"})
    for holiday, (start, end) in holiday_weeks[resort][year].items():
        data.append({"Task": holiday, "Start": datetime.strptime(start, "%Y-%m-%d"), "End": datetime.strptime(end, "%Y-%m-%d"), "Type": "Holiday"})
    return pd.DataFrame(data)

st.subheader("📅 Season and Holiday Timeline")
timeline_df = create_timeline_df(resort, str(checkin_date.year))
timeline_fig = px.timeline(timeline_df, x_start="Start", x_end="End", y="Task", color="Type",
                           color_discrete_map={"Season": "#636EFA", "Holiday": "#EF553B"})
timeline_fig.update_yaxes(categoryorder="category descending")
st.plotly_chart(timeline_fig, use_container_width=True)
#   ttttttttttttttt
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

    # Check if the date falls in any holiday week
    for holiday_name, (start_str, end_str) in holiday_weeks.get(resort, {}).get(year, {}).items():
        start = datetime.strptime(start_str, "%Y-%m-%d")
        end = datetime.strptime(end_str, "%Y-%m-%d")
        if start <= date_obj <= end:
            return {"season": "Holiday Week", "holiday": holiday_name}

    # Then check high and low season
    for season_type in ["High Season", "Low Season"]:
        for start_str, end_str in season_blocks.get(resort, {}).get(year, {}).get(season_type, []):
            start = datetime.strptime(start_str, "%Y-%m-%d")
            end = datetime.strptime(end_str, "%Y-%m-%d")
            if start <= date_obj <= end:
                return {"season": season_type, "holiday": None}

    # Default to unknown
    return {"season": "Unknown", "holiday": None}

def lookup_points(resort, room_type, date_str):
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

# Streamlit App UI
st.set_page_config(page_title="Marriott Points Calculator", layout="wide")
st.title("Marriott Vacation Club Points Calculator (Rules-Based)")

resort = st.selectbox("Select Resort", list(reference_points.keys()))
room_set = set()
for s in reference_points[resort]["Low Season"].values():
    room_set.update(s.keys())
room_type_display = st.selectbox("Room Type", [describe_room_type(r) for r in sorted(room_set)])
room_code = room_type_display.split(" (")[0]
checkin_date = st.date_input("Check-in Date", value=datetime(2025, 7, 1))
nights = st.number_input("Number of Nights", min_value=1, max_value=30, value=7)

with st.sidebar:
    discount = st.selectbox("Points Discount", [0, 25, 30], index=0)
discount_multiplier = 1 - (discount / 100)

# Run Calculation
results = []
total_points = 0
total_rent = 0

for i in range(nights):
    date = checkin_date + timedelta(days=i)
    date_str = date.strftime("%Y-%m-%d")
    rate = lookup_points(resort, room_code, date_str)
    if rate is None:
        results.append({
            "Date": date_str,
            "Day": date.strftime("%a"),
            "Season": "Unknown",
            "Holiday": "-",
            "Points": 0,
            "Rent ($)": 0
        })
        continue
    discount_rate = math.floor(rate * discount_multiplier)
    rent = math.ceil(rate * (0.81 if date.year == 2025 else 0.86))
    tag = classify_date(resort, date_str)
    results.append({
        "Date": date_str,
        "Day": date.strftime("%a"),
        "Season": tag["season"],
        "Holiday": tag["holiday"] or "-",
        "Points": discount_rate,
        "Rent ($)": rent
    })
    total_points += discount_rate
    total_rent += rent

df = pd.DataFrame(results)
st.dataframe(df, use_container_width=True)
st.success(f"Total Points: {total_points}")
st.success(f"Estimated Rent: ${total_rent}")
st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), "stay_breakdown.csv")

# Holiday Week Summary
holiday_rows = [r for r in results if r["Season"] == "Holiday Week"]
if holiday_rows:
    st.subheader("🎉 Holiday Week Summary")
    st.dataframe(pd.DataFrame(holiday_rows), use_container_width=True)

# Rent Comparison Chart
st.subheader("📊 Rent Breakdown by Day")
fig = px.bar(
    df, x="Day", y="Rent ($)", color="Season", barmode="group",
    text="Rent ($)", title="Rent per Day (Non-Holiday and Holiday)"
)
fig.update_traces(texttemplate="$%{text}", textposition="outside")
st.plotly_chart(fig, use_container_width=True)

# Timeline Visualization
st.subheader("📅 Season and Holiday Timeline")
def create_timeline_df(resort, year):
    data = []
    for season, ranges in season_blocks[resort][year].items():
        for start, end in ranges:
            data.append({
                "Task": season,
                "Start": datetime.strptime(start, "%Y-%m-%d"),
                "End": datetime.strptime(end, "%Y-%m-%d"),
                "Type": "Season"
            })
    for holiday, dates in holiday_weeks[resort][year].items():
        data.append({
            "Task": holiday,
            "Start": datetime.strptime(dates[0], "%Y-%m-%d"),
            "End": datetime.strptime(dates[1], "%Y-%m-%d"),
            "Type": "Holiday"
        })
    return pd.DataFrame(data)

year = str(checkin_date.year)
timeline_df = create_timeline_df(resort, year)
fig_timeline = px.timeline(
    timeline_df,
    x_start="Start",
    x_end="End",
    y="Task",
    color="Type",
    title=f"{resort} - {year} Seasons and Holidays",
    color_discrete_map={"Season": "#636EFA", "Holiday": "#EF553B"}
)
fig_timeline.update_yaxes(categoryorder="category descending")
st.plotly_chart(fig_timeline, use_container_width=True)
