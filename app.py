import streamlit as st
import math
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

# Initialize session state for debug messages
if "debug_messages" not in st.session_state:
    st.session_state.debug_messages = []

# Hardcoded data from provided input
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

room_view_legend = {
    "GV": "Garden View", "OV": "Ocean View", "OF": "Ocean Front",
    "MA": "Mountain View", "MK": "Ocean View",
    "PH MA": "Penthouse Mountain View", "PH MK": "Penthouse Ocean View"
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

# Function to generate data structure
def generate_data(resort, date):
    date_str = date.strftime("%Y-%m-%d")
    year = date.strftime("%Y")
    day_of_week = date.strftime("%a")
    is_fri_sat = day_of_week in ["Fri", "Sat"]
    day_category = "Fri-Sat" if is_fri_sat else "Sun-Thu"
    entry = {}

    # Check for holiday week
    is_holiday = False
    is_holiday_start = False
    holiday_name = None
    for h_name, [start, end] in holiday_weeks[resort][year].items():
        h_start = datetime.strptime(start, "%Y-%m-%d")
        h_end = datetime.strptime(end, "%Y-%m-%d")
        if h_start <= date <= h_end:
            is_holiday = True
            holiday_name = h_name
            if date == h_start:
                is_holiday_start = True
            break

    # Determine season
    season = "Low Season"
    for s_type in ["Low Season", "High Season"]:
        for [start, end] in season_blocks[resort][year][s_type]:
            s_start = datetime.strptime(start, "%Y-%m-%d")
            s_end = datetime.strptime(end, "%Y-%m-%d")
            if s_start <= date <= s_end:
                season = s_type
                break
        if season == s_type:
            break

    # Assign points
    if is_holiday:
        points_ref = reference_points[resort]["Holiday Week"].get(holiday_name, {})
    else:
        points_ref = reference_points[resort][season][day_category]
    
    for room_type, points in points_ref.items():
        entry[room_type] = points

    # Add flags
    if is_holiday:
        entry["HolidayWeek"] = True
    if is_holiday_start:
        entry["HolidayWeekStart"] = True

    return entry

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
    st.caption("\U0001F4A1 Discount applies only to points. Rent is based on original points.")

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

resort_display = st.selectbox("\U0001F3E8 Select Resort", options=display_resorts, key="resort_select")
resort = reverse_aliases.get(resort_display, resort_display)
st.session_state.debug_messages.append(f"Selected resort: {resort}")

# Get room types
sample_date = datetime(2025, 1, 3)
sample_entry = generate_data(resort, sample_date)
room_types = [k for k in sample_entry if k not in ("HolidayWeek", "HolidayWeekStart")]
if not room_types:
    st.error(f"No room types found for {resort}.")
    st.session_state.debug_messages.append(f"No room types for {resort}")
    st.stop()

room_type = st.selectbox("\U0001F6CF Select Room Type", options=room_types, key="room_type_select")
compare_rooms = st.multiselect("\U0001F4CA Compare With Other Room Types", options=[r for r in room_types if r != room_type])

checkin_date = st.date_input("\U0001F4C5 Check-in Date", min_value=datetime(2024, 12, 27), max_value=datetime(2026, 12, 31), value=datetime(2025, 7, 1))
num_nights = st.number_input("\U0001F319 Number of Nights", min_value=1, max_value=30, value=7)

# Set reference points
reference_entry = generate_data(resort, sample_date)
reference_points_resort = {k: v for k, v in reference_entry.items() if k not in ("HolidayWeek", "HolidayWeekStart")}

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
            "Holiday": "Yes" if entry.get("HolidayWeek", False) else "No"
        })
        total_points += discounted_points
        total_rent += rent

    return breakdown, total_points, total_rent

def compare_room_types(resort, room_types, checkin_date, num_nights, discount_multiplier, discount_percent):
    rate_per_point = 0.81 if checkin_date.year == 2025 else 0.86
    compare_data = []
    chart_data = []
    
    for room in room_types:
        for i in range(num_nights):
            date = checkin_date + timedelta(days=i)
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
                "Date": date_str,
                "Day": day_of_week,
                "Room Type": room,
                "Rent": rent,
                "Points": discounted_points,
                "Holiday": "Yes" if entry.get("HolidayWeek", False) else "No"
            })
    
    compare_df = pd.DataFrame(compare_data)
    compare_df_pivot = compare_df.pivot_table(index="Date", columns="Room Type", values="Estimated Rent ($)", aggfunc="first").reset_index()
    chart_df = pd.DataFrame(chart_data)
    
    st.session_state.debug_messages.append(f"chart_df columns: {chart_df.columns.tolist()}")
    st.session_state.debug_messages.append(f"chart_df head: {chart_df.head().to_dict()}")
    
    return compare_df_pivot, chart_df

# Main Calculation
if st.button("\U0001F4CA Calculate"):
    breakdown, total_points, total_rent = calculate_stay(
        resort, room_type, checkin_date, num_nights, discount_multiplier, discount_percent
    )

    st.subheader("\U0001F4CB Stay Breakdown")
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
            label="\U0001F4C4 Download Breakdown as CSV",
            data=csv_data,
            file_name=f"{resort}_stay_breakdown.csv",
            mime="text/csv"
        )

    if compare_rooms:
        st.subheader("\U0001F6CF Room Type Comparison")
        all_rooms = [room_type] + compare_rooms
        compare_df, chart_df = compare_room_types(
            resort, all_rooms, checkin_date, num_nights, discount_multiplier, discount_percent
        )
        st.dataframe(compare_df, use_container_width=True)

        compare_csv = compare_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="\U0001F4C5 Download Room Comparison as CSV",
            data=compare_csv,
            file_name=f"{resort}_room_comparison.csv",
            mime="text/csv"
        )

        # Bar Chart
        if not chart_df.empty:
            required_columns = ["Date", "Day", "Room Type", "Rent", "Points", "Holiday"]
            if all(col in chart_df.columns for col in required_columns):
                start_date_str = checkin_date.strftime("%B %-d")
                end_date = checkin_date + timedelta(days=num_nights - 1)
                end_date_str = end_date.strftime("%-d, %Y")
                title = f"Rent Comparison ({start_date_str}-{end_date_str})"
                st.subheader("\U0001F4CA " + title)
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
                    categoryarray=[(checkin_date + timedelta(days=i)).strftime("%a") for i in range(num_nights)]
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
