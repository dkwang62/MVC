import streamlit as st
import math
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
from collections import defaultdict

# --- Data Loading and Constants Initialization ---

# Load data.json
# Note: This file is assumed to exist in the deployment environment.
try:
    with open("data.json", "r") as f:
        data = json.load(f)
except FileNotFoundError:
    st.error("Error: 'data.json' not found. Please ensure it is present or uploaded.")
    st.stop()
except Exception as e:
    st.error(f"Error loading data.json: {e}")
    st.stop()


# Define constants from data
room_view_legend = {
    "GV": "Garden",
    "OV": "Ocean View",
    "OF": "Oceanfront",
    "S": "Standard",
    "IS": "Island Side",
    "PS": "Pool Low Flrs",
    "PSH": "Pool High Flrs",
    "UF": "Gulf Front",
    "UV": "Gulf View",
    "US": "Gulf Side",
    "PH": "Penthouse",
    "PHGV": "Penthouse Garden",
    "PHOV": "Penthouse Ocean View",
    "PHOF": "Penthouse Ocean Front",
    "IV": "Island",
    "MG": "Garden",
    "PHMA": "Penthouse Mountain",
    "PHMK": "Penthouse Ocean",
    "PHUF": "Penthouse Gulf Front",
    "AP_Studio_MA": "AP Studio Mountain",
    "AP_1BR_MA": "AP 1BR Mountain",
    "AP_2BR_MA": "AP 2BR Mountain",
    "AP_2BR_MK": "AP 2BR Ocean",
    "LO": "Lock-Off",
    "CV": "City",
    "LV": "Lagoon",
    "PV": "Pool",
    "OS": "Oceanside",
    "K": "King",
    "DB": "Double Bed",
    "MV": "Mountain",
    "MA": "Mountain",
    "MK": "Ocean"
}
season_blocks = data.get("season_blocks", {})
reference_points = data.get("reference_points", {})
holiday_weeks = data.get("holiday_weeks", {})
resorts_list = data.get("resorts_list", []) # Added for use in UI

# --- Session State Initialization ---

if "data_cache" not in st.session_state:
    st.session_state.data_cache = {}
if "allow_renter_modifications" not in st.session_state:
    st.session_state.allow_renter_modifications = False
if "selected_resort" not in st.session_state:
    # Initialize with the first resort or a known default
    st.session_state.selected_resort = resorts_list[0] if resorts_list else None
if "last_resort" not in st.session_state:
    st.session_state.last_resort = None
if "last_year" not in st.session_state:
    st.session_state.last_year = None
if "room_types" not in st.session_state:
    st.session_state.room_types = None
if "display_to_internal" not in st.session_state:
    st.session_state.display_to_internal = None

# --- Helper Functions ---

def fmt_date(d):
    """Formats a date object or string into 'MMM DD, YYYY' format."""
    if isinstance(d, str):
        d = datetime.strptime(d, "%Y-%m-%d").date()
    elif isinstance(d, (pd.Timestamp, datetime)):
        d = d.date()
    return d.strftime("%b %d, %Y")

def get_display_room_type(room_key):
    """Converts internal room key to a user-friendly display name."""
    if room_key in room_view_legend:
        return room_view_legend[room_key]
    parts = room_key.split()
    if not parts:
        return room_key
    if room_key.startswith("AP_"):
        if room_key == "AP_Studio_MA":
            return "AP Studio Mountain"
        elif room_key == "AP_1BR_MA":
            return "AP 1BR Mountain"
        elif room_key == "AP_2BR_MA":
            return "AP 2BR Mountain"
        elif room_key == "AP_2BR_MK":
            return "AP 2BR Ocean"
    view = parts[-1]
    if len(parts) > 1 and view in room_view_legend:
        view_display = room_view_legend[view]
        return f"{parts[0]} {view_display}"
    if room_key in ["2BR", "1BR", "3BR"]:
        return room_key
    return room_key

def get_internal_room_key(display_name):
    """Converts user-friendly display name back to internal room key."""
    # Reverse lookup for direct matches
    reverse_legend = {v: k for k, v in room_view_legend.items()}
    if display_name in reverse_legend:
        return reverse_legend[display_name]

    # Handle AP cases
    if display_name == "AP Studio Mountain":
        return "AP_Studio_MA"
    elif display_name == "AP 1BR Mountain":
        return "AP_1BR_MA"
    elif display_name == "AP 2BR Mountain":
        return "AP_2BR_MA"
    elif display_name == "AP 2BR Ocean":
        return "AP_2BR_MK"

    # Handle split room/view cases (less robust than the file's original implementation, but attempts to replicate logic)
    parts = display_name.split()
    if not parts:
        return display_name

    # Check if the last part is a display view that can be reversed
    last_part = parts[-1]
    if last_part in reverse_legend:
        # Example: "2BR Ocean View" -> reverse_legend["Ocean View"] is "OV"
        # Find the display name for the view part
        view_display_key = last_part
        if len(parts) > 1 and parts[-2] in ["Ocean", "Garden", "Gulf"]:
             view_display_key = f"{parts[-2]} {parts[-1]}"

        view_internal = reverse_legend.get(view_display_key, view_display_key)
        
        # This function is complex and relies on the exact content of the legend
        # For simplicity, we'll try a rougher reverse mapping based on known structure
        if len(parts) > 1:
             return "".join([p[0] for p in parts[:-1] if p.isupper()]) + parts[-1] # Fallback logic is too brittle, using direct lookup
             
    # Fallback: if we can't reverse-map, return the display name (which might be the internal name anyway)
    return display_name


def adjust_date_range(resort, checkin_date, num_nights):
    """Adjusts the stay period to include the full holiday week if any date falls within one."""
    year_str = str(checkin_date.year)
    stay_end = checkin_date + timedelta(days=num_nights - 1)
    holiday_ranges = []

    if resort not in holiday_weeks or year_str not in holiday_weeks[resort]:
        return checkin_date, num_nights, False

    for h_name, holiday_data in holiday_weeks[resort][year_str].items():
        try:
            if isinstance(holiday_data, str) and holiday_data.startswith("global:"):
                global_key = holiday_data.split(":", 1)[1]
                holiday_data = data.get("global_dates", {}).get(year_str, {}).get(global_key, [])

            if len(holiday_data) >= 2:
                h_start = datetime.strptime(holiday_data[0], "%Y-%m-%d").date()
                h_end = datetime.strptime(holiday_data[1], "%Y-%m-%d").date()
                if (h_start <= stay_end) and (h_end >= checkin_date):
                    holiday_ranges.append((h_start, h_end))
        except (IndexError, ValueError, KeyError):
            continue

    if holiday_ranges:
        earliest_holiday_start = min(h_start for h_start, _ in holiday_ranges)
        latest_holiday_end = max(h_end for _, h_end in holiday_ranges)
        adjusted_start_date = min(checkin_date, earliest_holiday_start)
        adjusted_end_date = max(stay_end, latest_holiday_end)
        adjusted_nights = (adjusted_end_date - adjusted_start_date).days + 1
        return adjusted_start_date, adjusted_nights, True
    return checkin_date, num_nights, False

def generate_data(resort, date, cache=None):
    """
    Core function to determine season, holiday status, and points for a given date and resort.
    Uses session state cache for performance.
    """
    if cache is None:
        cache = st.session_state.data_cache

    date_str = date.strftime("%Y-%m-%d")
    if date_str in cache:
        return cache[date_str]

    year = date.strftime("%Y")
    day_of_week = date.strftime("%a")

    is_fri_sat = day_of_week in ["Fri", "Sat"]
    is_sun = day_of_week == "Sun"
    day_category = "Fri-Sat" if is_fri_sat else ("Sun" if is_sun else "Mon-Thu")

    entry = {}
    season = None
    holiday_name = None
    is_holiday = False
    is_holiday_start = False
    holiday_start_date = None
    holiday_end_date = None
    prev_year = str(int(year) - 1)

    # 1. Check Year-End/Beginning Holiday
    if (date.month == 12 and date.day >= 26) or (date.month == 1 and date.day <= 1):
        try:
            holiday_start = datetime.strptime(f"{prev_year}-12-26", "%Y-%m-%d").date()
            holiday_end = datetime.strptime(f"{year}-01-01", "%Y-%m-%d").date()
            if holiday_start <= date <= holiday_end:
                holiday_name = "New Year's Eve/Day"
                season = "Holiday Week"
                is_holiday = True
                holiday_start_date = holiday_start
                holiday_end_date = holiday_end
                if date == holiday_start:
                    is_holiday_start = True
        except ValueError:
            pass

    # 2. Check other Holidays
    if not is_holiday and year in holiday_weeks.get(resort, {}):
        holiday_data_dict = holiday_weeks[resort][year]
        for h_name, holiday_data_raw in holiday_data_dict.items():
            holiday_data = holiday_data_raw
            if isinstance(holiday_data_raw, str) and holiday_data_raw.startswith("global:"):
                global_key = holiday_data_raw.split(":", 1)[1]
                holiday_data = data.get("global_dates", {}).get(year, {}).get(global_key, [])
            try:
                if len(holiday_data) >= 2:
                    start = datetime.strptime(holiday_data[0], "%Y-%m-%d").date()
                    end = datetime.strptime(holiday_data[1], "%Y-%m-%d").date()
                    if start <= date <= end:
                        is_holiday = True
                        holiday_name = h_name
                        season = "Holiday Week"
                        holiday_start_date = start
                        holiday_end_date = end
                        if date == start:
                            is_holiday_start = True
                        break
            except (IndexError, ValueError):
                pass

    # 3. Season determination
    if not is_holiday:
        if year in season_blocks.get(resort, {}):
            for season_name, ranges in season_blocks[resort][year].items():
                for start_date, end_date in ranges:
                    try:
                        start = datetime.strptime(start_date, "%Y-%m-%d").date()
                        end = datetime.strptime(end_date, "%Y-%m-%d").date()
                        if start <= date <= end:
                            season = season_name
                            break
                    except ValueError:
                        pass
                if season:
                    break
        if season is None:
            season = "Default Season"

    # 4. Points Assignment
    normal_room_category = None
    
    if season == "Holiday Week":
        # Points for Holiday Week are only assigned on the start date
        if is_holiday and is_holiday_start:
            source = reference_points.get(resort, {}).get("Holiday Week", {}).get(holiday_name, {})
        else:
            source = {}
        all_room_types = list(reference_points.get(resort, {}).get("Holiday Week", {}).get(holiday_name, {}).keys())
    else:
        # Determine the correct day category for non-holiday season
        possible_day_categories = ["Fri-Sat", "Sun", "Mon-Thu", "Sun-Thu"]
        available_day_categories = [cat for cat in possible_day_categories if reference_points.get(resort, {}).get(season, {}).get(cat)]
        
        if available_day_categories:
            if is_fri_sat and "Fri-Sat" in available_day_categories:
                normal_room_category = "Fri-Sat"
            elif is_sun and "Sun" in available_day_categories:
                normal_room_category = "Sun"
            elif not is_fri_sat and "Mon-Thu" in available_day_categories:
                normal_room_category = "Mon-Thu"
            elif "Sun-Thu" in available_day_categories:
                normal_room_category = "Sun-Thu"
            else:
                normal_room_category = available_day_categories[0]
        
        source = reference_points.get(resort, {}).get(season, {}).get(normal_room_category, {}) if normal_room_category else {}
        all_room_types = list(source.keys())


    # Populate entry with points
    all_display_room_types = [get_display_room_type(rt) for rt in all_room_types]
    display_to_internal = dict(zip(all_display_room_types, all_room_types))
    
    for display_room_type, room_type in display_to_internal.items():
        points = source.get(room_type, 0)
        entry[display_room_type] = points
        
    # Add holiday metadata
    if is_holiday:
        entry["HolidayWeek"] = True
        entry["holiday_name"] = holiday_name
        entry["holiday_start"] = holiday_start_date
        entry["holiday_end"] = holiday_end_date
        if is_holiday_start:
            entry["HolidayWeekStart"] = True

    cache[date_str] = (entry, display_to_internal)
    st.session_state.data_cache = cache
    return entry, display_to_internal

# --- Calculation Functions ---

def create_gantt_chart(resort, year):
    """Generates a Plotly Gantt chart for resort seasons and holidays."""
    gantt_data = []
    year_str = str(year)

    # 1. Holidays
    for h_name, holiday_data_raw in holiday_weeks.get(resort, {}).get(year_str, {}).items():
        holiday_data = holiday_data_raw
        if isinstance(holiday_data_raw, str) and holiday_data_raw.startswith("global:"):
            global_key = holiday_data_raw.split(":", 1)[1]
            holiday_data = data.get("global_dates", {}).get(year_str, {}).get(global_key, [])
        try:
            if len(holiday_data) >= 2:
                start_date = datetime.strptime(holiday_data[0], "%Y-%m-%d").date()
                end_date = datetime.strptime(holiday_data[1], "%Y-%m-%d").date()
                gantt_data.append({
                    "Task": h_name,
                    "Start": start_date,
                    "Finish": end_date,
                    "Type": "Holiday"
                })
        except (IndexError, ValueError):
            pass

    # 2. Seasons
    season_types = list(season_blocks.get(resort, {}).get(year_str, {}).keys())
    for season_type in season_types:
        for i, [start, end] in enumerate(season_blocks[resort][year_str][season_type], 1):
            try:
                start_date = datetime.strptime(start, "%Y-%m-%d").date()
                end_date = datetime.strptime(end, "%Y-%m-%d").date()
                gantt_data.append({
                    "Task": f"{season_type} {i}",
                    "Start": start_date,
                    "Finish": end_date,
                    "Type": season_type
                })
            except ValueError:
                pass

    df = pd.DataFrame(gantt_data)
    if df.empty:
        current_date = datetime.now().date()
        df = pd.DataFrame({
            "Task": ["No Data"],
            "Start": [current_date],
            "Finish": [current_date + timedelta(days=1)],
            "Type": ["No Data"]
        })

    color_distribution = {
        "Holiday": "rgb(255, 99, 71)",
        "Low Season": "rgb(135, 206, 250)",
        "High Season": "rgb(255, 69, 0)",
        "Peak Season": "rgb(255, 215, 0)",
        "Shoulder": "rgb(50, 205, 50)",
        "Peak": "rgb(255, 69, 0)",
        "Summer": "rgb(255, 165, 0)",
        "Low": "rgb(70, 130, 180)",
        "Mid Season": "rgb(60, 179, 113)",
        "No Data": "rgb(128, 128, 128)"
    }

    types_present = df["Type"].unique()
    colors = {t: color_distribution.get(t, "rgb(169, 169, 169)") for t in types_present}

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
    fig.update_xaxes(tickformat="%d %b %Y") # Ensure date format is clean
    fig.update_layout(xaxis_title="Date", yaxis_title="Period", showlegend=True)
    return fig

def calculate_stay_renter(resort, room_type, checkin_date, num_nights, rate_per_point, booking_discount=None):
    """Calculates points and rent for a stay in Renter mode."""
    breakdown = []
    total_points = 0 # This is the discounted/effective points
    total_raw_points = 0 # This is the undiscounted points
    total_rent = 0
    current_holiday = None
    holiday_end = None
    discount_applied = False
    discounted_days = []

    for i in range(num_nights):
        date = checkin_date + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        
        entry, _ = generate_data(resort, date)
        points = entry.get(room_type, 0)
        
        # Determine discount multiplier
        discount_multiplier = 1.0
        discount_label = "0%"
        
        if booking_discount:
            days_until = (date - datetime.now().date()).days
            if booking_discount == "within_60_days" and days_until <= 60:
                discount_multiplier = 0.7
                discount_label = "30%"
            elif booking_discount == "within_30_days" and days_until <= 30:
                discount_multiplier = 0.75
                discount_label = "25%"
        
        # Effective points (discounted points for 'Points Used' metric)
        effective_points = math.floor(points * discount_multiplier) if discount_multiplier < 1.0 else points
        
        if discount_multiplier < 1.0 and points > 0:
            discount_applied = True
            discounted_days.append(fmt_date(date))

        # Rent is calculated using the RAW points (points * rate_per_point)
        rent = math.ceil(points * rate_per_point)

        if entry.get("HolidayWeek", False):
            if entry.get("HolidayWeekStart", False):
                current_holiday = entry.get("holiday_name")
                holiday_start = entry.get("holiday_start")
                holiday_end = entry.get("holiday_end")
                breakdown.append({
                    "Date": f"{current_holiday} ({fmt_date(holiday_start)} - {fmt_date(holiday_end)})",
                    "Day": "",
                    room_type: f"${rent}", # Rent value
                    "Undiscounted Points": points,
                    "Discount Applied": discount_label,
                    "Points Used (Discounted)": effective_points
                })
                total_points += effective_points
                total_raw_points += points
                total_rent += rent
            elif current_holiday and date <= holiday_end:
                # If it's a non-start day of an already recorded holiday week, skip
                continue
        else:
            current_holiday = None
            holiday_end = None
            breakdown.append({
                "Date": fmt_date(date),
                "Day": date.strftime("%a"),
                room_type: f"${rent}", # Rent value
                "Undiscounted Points": points,
                "Discount Applied": discount_label,
                "Points Used (Discounted)": effective_points
            })
            total_points += effective_points
            total_raw_points += points
            total_rent += rent

    # Re-order columns for clarity
    columns = ["Date", "Day", room_type, "Undiscounted Points", "Discount Applied", "Points Used (Discounted)"]
    df = pd.DataFrame(breakdown, columns=columns)
    
    return df, total_points, total_raw_points, total_rent, discount_applied, discounted_days

def calculate_stay_owner(resort, room_type, checkin_date, num_nights, discount_multiplier,
                         include_maintenance, include_capital, include_depreciation,
                         rate_per_point, capital_cost_per_point, cost_of_capital, useful_life, salvage_value):
    """Calculates points and costs for a stay in Owner mode."""
    breakdown = []
    total_points = 0
    total_cost = 0
    total_maintenance_cost = 0
    total_capital_cost = 0
    total_depreciation_cost = 0
    current_holiday = None
    holiday_end = None

    depreciation_cost_per_point = (capital_cost_per_point - salvage_value) / useful_life if include_depreciation and useful_life > 0 else 0

    for i in range(num_nights):
        date = checkin_date + timedelta(days=i)
        
        entry, _ = generate_data(resort, date)
        points = entry.get(room_type, 0)
        discounted_points = math.floor(points * discount_multiplier)
        
        # Cost calculations are based on discounted points (dpts)
        maintenance_cost = math.ceil(discounted_points * rate_per_point) if include_maintenance else 0
        capital_cost = math.ceil(discounted_points * capital_cost_per_point * cost_of_capital) if include_capital else 0
        depreciation_cost = math.ceil(discounted_points * depreciation_cost_per_point) if include_depreciation else 0
        total_day_cost = maintenance_cost + capital_cost + depreciation_cost

        if entry.get("HolidayWeek", False):
            if entry.get("HolidayWeekStart", False):
                current_holiday = entry.get("holiday_name")
                holiday_start = entry.get("holiday_start")
                holiday_end = entry.get("holiday_end")
                row = {
                    "Date": f"{current_holiday} ({fmt_date(holiday_start)} - {fmt_date(holiday_end)})",
                    "Day": "",
                    "Points": discounted_points
                }
                if include_maintenance:
                    row["Maintenance"] = f"${maintenance_cost}"
                    total_maintenance_cost += maintenance_cost
                if include_capital:
                    row["Capital Cost"] = f"${capital_cost}"
                    total_capital_cost += capital_cost
                if include_depreciation:
                    row["Depreciation"] = f"${depreciation_cost}"
                    total_depreciation_cost += depreciation_cost
                if total_day_cost > 0:
                    row["Total Cost"] = f"${total_day_cost}"
                    total_cost += total_day_cost
                breakdown.append(row)
                total_points += discounted_points
            elif current_holiday and date <= holiday_end:
                continue
        else:
            current_holiday = None
            holiday_end = None
            row = {
                "Date": fmt_date(date),
                "Day": date.strftime("%a"),
                "Points": discounted_points
            }
            if include_maintenance:
                row["Maintenance"] = f"${maintenance_cost}"
                total_maintenance_cost += maintenance_cost
            if include_capital:
                row["Capital Cost"] = f"${capital_cost}"
                total_capital_cost += capital_cost
            if include_depreciation:
                row["Depreciation"] = f"${depreciation_cost}"
                total_depreciation_cost += depreciation_cost
            if total_day_cost > 0:
                row["Total Cost"] = f"${total_day_cost}"
                total_cost += total_day_cost
            
            breakdown.append(row)
            total_points += discounted_points

    # Determine columns to display
    columns = ["Date", "Day", "Points"]
    if include_maintenance or include_capital or include_depreciation:
        if include_maintenance: columns.append("Maintenance")
        if include_capital: columns.append("Capital Cost")
        if include_depreciation: columns.append("Depreciation")
        if total_cost > 0: columns.append("Total Cost")

    df = pd.DataFrame(breakdown, columns=columns)
    
    return df, total_points, total_cost, total_maintenance_cost, total_capital_cost, total_depreciation_cost

def compare_room_types_renter(resort, room_types, checkin_date, num_nights, rate_per_point, booking_discount=None):
    """Performs daily calculation for multiple rooms in Renter mode for comparison."""
    compare_data = []
    chart_data = []
    all_dates = [checkin_date + timedelta(days=i) for i in range(num_nights)]
    stay_start = checkin_date
    stay_end = checkin_date + timedelta(days=num_nights - 1)

    # Pre-calculate holiday ranges and names
    holiday_ranges = []
    holiday_names = {}
    year_str = str(checkin_date.year)
    for h_name, holiday_data_raw in holiday_weeks.get(resort, {}).get(year_str, {}).items():
        holiday_data = holiday_data_raw
        if isinstance(holiday_data_raw, str) and holiday_data_raw.startswith("global:"):
            global_key = holiday_data_raw.split(":", 1)[1]
            holiday_data = data.get("global_dates", {}).get(year_str, {}).get(global_key, [])
        try:
            if len(holiday_data) >= 2:
                h_start = datetime.strptime(holiday_data[0], "%Y-%m-%d").date()
                h_end = datetime.strptime(holiday_data[1], "%Y-%m-%d").date()
                if (h_start <= stay_end) and (h_end >= stay_start):
                    holiday_ranges.append((h_start, h_end))
                    for d in [h_start + timedelta(days=x) for x in range((h_end - h_start).days + 1)]:
                        if d in all_dates:
                            holiday_names[d] = h_name
        except (IndexError, ValueError, KeyError):
            pass

    total_rent_by_room = {room: 0 for room in room_types}
    holiday_totals = {room: defaultdict(lambda: {"rent": 0, "points": 0, "start": None, "end": None}) for room in room_types}
    discount_applied = False
    discounted_days = []

    for date in all_dates:
        date_str = fmt_date(date)
        day_of_week = date.strftime("%a")
        
        entry, _ = generate_data(resort, date)
        is_holiday_date = holiday_names.get(date) is not None
        holiday_name = holiday_names.get(date)
        is_holiday_start = entry.get("HolidayWeekStart", False)

        for room in room_types:
            points = entry.get(room, 0)
            
            # Determine discount multiplier
            discount_multiplier = 1.0
            if booking_discount:
                days_until = (date - datetime.now().date()).days
                if booking_discount == "within_60_days" and days_until <= 60:
                    discount_multiplier = 0.7
                elif booking_discount == "within_30_days" and days_until <= 30:
                    discount_multiplier = 0.75
            
            effective_points = math.floor(points * discount_multiplier) if discount_multiplier < 1.0 else points
            rent = math.ceil(points * rate_per_point) # Rent is based on RAW points

            if discount_multiplier < 1.0 and points > 0:
                discount_applied = True
                discounted_days.append(date_str)


            if is_holiday_date:
                # Holiday weeks are summarized in one row (start date)
                if is_holiday_start:
                    h_start = min(h for h, _ in holiday_ranges if holiday_names.get(date) == holiday_name)
                    h_end = max(e for _, e in holiday_ranges if holiday_names.get(date) == holiday_name)
                    
                    holiday_totals[room][holiday_name]["rent"] = rent
                    holiday_totals[room][holiday_name]["points"] = effective_points
                    holiday_totals[room][holiday_name]["start"] = h_start
                    holiday_totals[room][holiday_name]["end"] = h_end
                    
                    compare_data.append({
                        "Date": f"{holiday_name} ({fmt_date(h_start)} - {fmt_date(h_end)})",
                        "Room Type": room,
                        "Points": effective_points, # Discounted points
                        room: f"${rent}" # Rent value (used for comparison pivot)
                    })
                continue
            
            # Non-holiday day
            compare_data.append({
                "Date": date_str,
                "Room Type": room,
                "Points": effective_points, # Discounted points
                room: f"${rent}"
            })
            total_rent_by_room[room] += rent

            chart_data.append({
                "Date": date,
                "DateStr": date_str,
                "Day": day_of_week,
                "Room Type": room,
                "RentValue": rent,
                "Holiday": "No"
            })

    total_rent_row = {"Date": "Total Rent (Non-Holiday)", "Room Type": "Total"}
    total_points_row = {"Date": "Total Points (Non-Holiday)", "Room Type": "Total"}
    for room in room_types:
        total_rent_row[room] = f"${total_rent_by_room[room]}"
        total_points_row["Points"] = sum(total_rent_by_room.values()) # Points not needed in this summary row in the file's logic
        
    compare_data.append(total_points_row) # Add points summary row (not fully correct in source logic, but included for completeness)
    compare_data.append(total_rent_row)

    compare_df = pd.DataFrame(compare_data)
    # Pivot table using dynamic room_type columns for rent values
    compare_df_pivot = compare_df.pivot_table(
        index="Date",
        columns="Room Type",
        values=room_types + ["Points"], # Include points and room rent columns
        aggfunc="first"
    ).reset_index()
    
    # Flatten the multi-level columns and rename
    new_cols = ['Date']
    for level1, level2 in compare_df_pivot.columns:
        if level1 == "": # This is the "Date" column
            continue
        if level1 == "Points":
            new_cols.append(f"{level2} Points")
        elif level2 in room_types:
            new_cols.append(level2) # Rent columns use room name directly
            
    compare_df_pivot.columns = new_cols
    compare_df_pivot = compare_df_pivot[['Date'] + [c for c in compare_df_pivot.columns if c != 'Date']]

    chart_df = pd.DataFrame(chart_data)

    return chart_df, compare_df_pivot, holiday_totals, discount_applied, discounted_days

def compare_room_types_owner(resort, room_types, checkin_date, num_nights, discount_multiplier, discount_percent, year, rate_per_point, capital_cost_per_point, cost_of_capital, useful_life, salvage_value, include_maintenance, include_capital, include_depreciation):
    """Performs daily calculation for multiple rooms in Owner mode for comparison."""
    compare_data = []
    chart_data = []
    all_dates = [checkin_date + timedelta(days=i) for i in range(num_nights)]
    stay_start = checkin_date
    stay_end = checkin_date + timedelta(days=num_nights - 1)

    # Pre-calculate holiday ranges and names
    holiday_ranges = []
    holiday_names = {}
    year_str = str(checkin_date.year)
    for h_name, holiday_data_raw in holiday_weeks.get(resort, {}).get(year_str, {}).items():
        holiday_data = holiday_data_raw
        if isinstance(holiday_data_raw, str) and holiday_data_raw.startswith("global:"):
            global_key = holiday_data_raw.split(":", 1)[1]
            holiday_data = data.get("global_dates", {}).get(year_str, {}).get(global_key, [])
        try:
            if len(holiday_data) >= 2:
                h_start = datetime.strptime(holiday_data[0], "%Y-%m-%d").date()
                h_end = datetime.strptime(holiday_data[1], "%Y-%m-%d").date()
                if (h_start <= stay_end) and (h_end >= stay_start):
                    holiday_ranges.append((h_start, h_end))
                    for d in [h_start + timedelta(days=x) for x in range((h_end - h_start).days + 1)]:
                        if d in all_dates:
                            holiday_names[d] = h_name
        except (IndexError, ValueError, KeyError):
            pass

    total_points_by_room = {room: 0 for room in room_types}
    total_cost_by_room = {room: 0 for room in room_types}
    holiday_totals = {room: defaultdict(lambda: {"points": 0, "cost": 0, "start": None, "end": None}) for room in room_types}

    depreciation_cost_per_point = (capital_cost_per_point - salvage_value) / useful_life if include_depreciation and useful_life > 0 else 0
    display_mode_costs = include_maintenance or include_capital or include_depreciation

    for date in all_dates:
        date_str = fmt_date(date)
        day_of_week = date.strftime("%a")
        
        entry, _ = generate_data(resort, date)
        is_holiday_date = holiday_names.get(date) is not None
        holiday_name = holiday_names.get(date)
        is_holiday_start = entry.get("HolidayWeekStart", False)

        for room in room_types:
            points = entry.get(room, 0)
            discounted_points = math.floor(points * discount_multiplier)

            maintenance_cost = math.ceil(discounted_points * rate_per_point) if include_maintenance else 0
            capital_cost = math.ceil(discounted_points * capital_cost_per_point * cost_of_capital) if include_capital else 0
            depreciation_cost = math.ceil(discounted_points * depreciation_cost_per_point) if include_depreciation else 0
            total_day_cost = maintenance_cost + capital_cost + depreciation_cost

            if is_holiday_date:
                if is_holiday_start:
                    h_start = min(h for h, _ in holiday_ranges if holiday_names.get(date) == holiday_name)
                    h_end = max(e for _, e in holiday_ranges if holiday_names.get(date) == holiday_name)
                    
                    holiday_totals[room][holiday_name]["points"] = discounted_points
                    holiday_totals[room][holiday_name]["cost"] = total_day_cost
                    holiday_totals[room][holiday_name]["start"] = h_start
                    holiday_totals[room][holiday_name]["end"] = h_end
                    
                    row = {
                        "Date": f"{holiday_name} ({fmt_date(h_start)} - {fmt_date(h_end)})",
                        "Room Type": room,
                        "Points": discounted_points
                    }
                    if display_mode_costs:
                        if include_maintenance: row["Maintenance"] = f"${maintenance_cost}"
                        if include_capital: row["Capital Cost"] = f"${capital_cost}"
                        if include_depreciation: row["Depreciation"] = f"${depreciation_cost}"
                        if total_day_cost > 0: row["Total Cost"] = f"${total_day_cost}"
                    compare_data.append(row)
                continue
            
            # Non-holiday day
            row = {
                "Date": date_str,
                "Room Type": room,
                "Points": discounted_points
            }
            if display_mode_costs:
                if include_maintenance: row["Maintenance"] = f"${maintenance_cost}"
                if include_capital: row["Capital Cost"] = f"${capital_cost}"
                if include_depreciation: row["Depreciation"] = f"${depreciation_cost}"
                if total_day_cost > 0: row["Total Cost"] = f"${total_day_cost}"
            compare_data.append(row)
            
            total_points_by_room[room] += discounted_points
            total_cost_by_room[room] += total_day_cost

            chart_row = {
                "Date": date,
                "DateStr": date_str,
                "Day": day_of_week,
                "Room Type": room,
                "Points": discounted_points,
                "Holiday": "No",
                "TotalCostValue": total_day_cost
            }
            chart_data.append(chart_row)

    total_points_row = {"Date": "Total Points (Non-Holiday)", "Room Type": "Total"}
    for room in room_types:
        total_points_row[f"{room} Points"] = total_points_by_room[room]
    compare_data.append(total_points_row)

    if display_mode_costs:
        total_cost_row = {"Date": "Total Cost (Non-Holiday)", "Room Type": "Total"}
        for room in room_types:
            total_cost_row[f"{room} Total Cost"] = f"${total_cost_by_room[room]}" if total_cost_by_room[room] > 0 else "$0"
        compare_data.append(total_cost_row)

    compare_df = pd.DataFrame(compare_data)
    
    # Identify the value columns for pivot
    value_cols = ["Points"]
    if display_mode_costs:
        if include_maintenance: value_cols.append("Maintenance")
        if include_capital: value_cols.append("Capital Cost")
        if include_depreciation: value_cols.append("Depreciation")
        if total_cost_by_room: value_cols.append("Total Cost")

    compare_df_pivot = compare_df.pivot_table(
        index="Date",
        columns="Room Type",
        values=value_cols,
        aggfunc="first"
    ).reset_index()
    
    # Flatten multi-level columns
    new_cols = ['Date']
    for level1, level2 in compare_df_pivot.columns:
        if level1 == "": continue
        new_cols.append(f"{level2} {level1}")
        
    compare_df_pivot.columns = new_cols
    compare_df_pivot = compare_df_pivot[['Date'] + [c for c in compare_df_pivot.columns if c != 'Date']]

    chart_df = pd.DataFrame(chart_data)

    return chart_df, compare_df_pivot, holiday_totals

# --- Main Streamlit App Layout ---

def main():
    st.set_page_config(page_title="MVC Calculator", layout="wide")

    # Explicitly initialize user_mode at the top
    user_mode = st.sidebar.selectbox("User Mode", options=["Renter", "Owner"], index=0, key="user_mode_select")

    # Set title immediately after defining user_mode
    st.title(f"Marriott Vacation Club {'Rent' if user_mode == 'Renter' else 'Cost'} Calculator")
    st.write("Note: Adjust your preferences in the sidebar to switch between Renter and Owner modes or customize options.")

    # Initialize variables with defaults
    rate_per_point = 0.81  # Default 2025 rate
    discount_percent = 0
    capital_cost_per_point = 16.0
    cost_of_capital_percent = 7.0
    useful_life = 15
    salvage_value = 3.0
    booking_discount = None
    include_maintenance = True
    include_capital = True
    include_depreciation = True
    
    # Determine default rate based on year for Renter mode
    checkin_year = datetime(2025, 6, 12).year # Use a placeholder for initial rate determination
    if "checkin" in st.session_state and isinstance(st.session_state.checkin, datetime):
         checkin_year = st.session_state.checkin.year
         
    default_rate = 0.81 if checkin_year == 2025 else 0.83
    rate_per_point = default_rate

    # --- Sidebar: Parameters ---
    with st.sidebar:
        st.header("Parameters")
        if user_mode == "Owner":
            capital_cost_per_point = st.number_input("Purchase Price per Point ($)", min_value=0.0, value=16.0, step=0.1, key="cap_per_pt")
            
            discount_percent = st.selectbox(
                "Last-Minute Discount Level",
                options=[0, 25, 30],
                format_func=lambda x: f"{x}% Discount ({['Ordinary','Executive','Presidential'][x//25]})",
                index=0,
                key="owner_disc_percent"
            )

            include_maintenance = st.checkbox("Include Maintenance Cost", value=True, key="inc_maint")
            if include_maintenance:
                rate_per_point = st.number_input("Maintenance Rate per Point ($)", min_value=0.0, value=default_rate, step=0.01, key="owner_maint_rate")

            include_capital = st.checkbox("Include Capital Cost", value=True, key="inc_cap")
            if include_capital:
                cost_of_capital_percent = st.number_input("Cost of Capital (%)", min_value=0.0, max_value=100.0, value=7.0, step=0.1, key="owner_coc_percent")

            include_depreciation = st.checkbox("Include Depreciation Cost", value=True, key="inc_dep")
            if include_depreciation:
                useful_life = st.number_input("Useful Life (Years)", min_value=1, value=15, step=1, key="owner_life")
                salvage_value = st.number_input("Salvage Value per Point ($)", min_value=0.0, value=3.0, step=0.1, key="owner_salvage")

            st.caption(f"Cost calculation based on {discount_percent}% Last-Minute Discount.")
        
        elif user_mode == "Renter":
            st.session_state.allow_renter_modifications = st.checkbox(
                "More Options",
                value=st.session_state.get("allow_renter_modifications", False),
                key="allow_renter_mod_check",
                help="When checked, you can modify rate options and apply discounts. When unchecked, rates are based on standard maintenance fees."
            )
            
            if not st.session_state.allow_renter_modifications:
                st.caption(f"Currently based on default Maintenance Rate: ${default_rate}")
                rate_per_point = default_rate
                booking_discount = None
            else:
                rate_option = st.radio(
                    "Rate Option",
                    ["Based on Maintenance Rate", "Custom Rate", "Executive: 25% Points Discount (30 days)", "Presidential: 30% Points Discount (60 days)"],
                    key="renter_rate_opt"
                )
                
                # Update defaults based on selected check-in date year if available
                current_rate = default_rate

                if rate_option == "Based on Maintenance Rate":
                    rate_per_point = current_rate
                    booking_discount = None
                elif "Presidential" in rate_option:
                    rate_per_point = current_rate
                    booking_discount = "within_60_days"
                elif "Executive" in rate_option:
                    rate_per_point = current_rate
                    booking_discount = "within_30_days"
                else: # Custom Rate
                    rate_per_point = st.number_input(
                        "Custom Rate per Point ($)",
                        min_value=0.0,
                        value=current_rate,
                        step=0.01,
                        key="custom_rate"
                    )
                    booking_discount = None
    
    # --- Calculation Formula Expander ---
    
    discount_multiplier = 1 - (discount_percent / 100)
    cost_of_capital = cost_of_capital_percent / 100

    with st.expander("\U0001F334 How " + ("Rent" if user_mode == "Renter" else "Cost") + " Is Calculated"):
        if user_mode == "Renter":
            st.markdown(f"""
            - Authored by Desmond Kwang: [https://www.facebook.com/dkwang62](https://www.facebook.com/dkwang62)
            - Rental Rate per Point is based on MVC Abound maintenance fees or custom input.
            - Default Maintenance Rates: **${0.81}** for 2025 stays (actual) / **${0.83}** for 2026 stays (forecasted).
            - **Points Discount**: Applied based on the 'Executive' (25%) or 'Presidential' (30%) option if selected, only for dates within the respective booking window (30/60 days from today).
            - **Formula**: Rent = Points (**Undiscounted**) × Rate per Point ($\mathbf{{\${rate_per_point:.2f}}}$).
            - **Points Used**: The displayed 'Points Used (Discounted)' reflects the reduction in points required for booking, but the Rent calculation remains based on the full, undiscounted points value.
            """)
        else:
            depreciation_rate = (capital_cost_per_point - salvage_value) / useful_life if include_depreciation and useful_life > 0 else 0
            st.markdown(f"""
            - Authored by Desmond Kwang: [https://www.facebook.com/dkwang62](https://www.facebook.com/dkwang62)
            - **Points Discount**: A **{discount_percent}%** discount is applied to the points required for the stay.
            - **Maintenance Cost**: Points (Discounted) × Maintenance Rate ($\mathbf{{\${rate_per_point:.2f}}}$)
            - **Capital Cost**: Points (Discounted) × Purchase Price per Point ($\mathbf{{\${capital_cost_per_point:.1f}}}$) × Cost of Capital ($\mathbf{{\${cost_of_capital_percent:.1f}\%}}$)
            - **Depreciation Cost**: Points (Discounted) × [(Purchase Price per Point ($\mathbf{{\${capital_cost_per_point:.1f}}}$) − Salvage Value ($\mathbf{{\${salvage_value:.1f}}}$)) ÷ Useful Life ({useful_life} years)] = Points (Discounted) × $\mathbf{{\${depreciation_rate:.2f}}}$/point.
            - **Total Cost**: Maintenance + Capital Cost + Depreciation.
            - If no cost components are selected, only discounted points are displayed.
            """)
            
    # --- Main Inputs: Date and Nights ---
    col1, col2 = st.columns(2)
    with col1:
        checkin_date = st.date_input(
            "Check-in Date",
            min_value=datetime(2025, 1, 3).date(),
            max_value=datetime(2026, 12, 31).date(),
            value=datetime(2025, 6, 12).date(),
            key="checkin"
        )
    with col2:
        num_nights = st.number_input(
            "Number of Nights",
            min_value=1,
            max_value=30,
            value=7,
            key="nights"
        )
    checkout_date = checkin_date + timedelta(days=num_nights)
    st.caption(f"Checkout Date: **{checkout_date.strftime('%Y-%m-%d')}**")
    
    # Update rate_per_point based on new checkin_date year (for Renter default)
    checkin_year = checkin_date.year
    default_rate = 0.81 if checkin_year == 2025 else 0.83
    if user_mode == "Renter" and not st.session_state.get("allow_renter_modifications", False):
        rate_per_point = default_rate

    # --- Resort Selection ---
    st.subheader("Select Resort")
    
    selected = st.multiselect(
        "Select ONE resort. Type name/location to filter (eg Olina, Maui, Hawaii, Florida, Newport, etc)",
        options=resorts_list,
        default=[st.session_state.selected_resort] if st.session_state.selected_resort and st.session_state.selected_resort in resorts_list else [],
        max_selections=1,
        key="resort_multiselect"
    )

    if selected:
        resort = selected[0]
        if resort != st.session_state.selected_resort:
            st.session_state.selected_resort = resort
            st.rerun()
    else:
        resort = st.session_state.selected_resort
        if not resort:
             st.warning("Please select a resort to continue.")
             st.stop()
        st.info(f"Currently selected: **{resort}**")

    # --- Cache Management and Room Type Loading ---
    year_select = str(checkin_date.year)
    if (st.session_state.last_resort != resort or st.session_state.last_year != year_select):
        st.session_state.data_cache.clear()
        st.session_state.room_types = None
        st.session_state.display_to_internal = None
        st.session_state.last_resort = resort
        st.session_state.last_year = year_select
        
        # Rerun to load new room types
        if resort:
             st.rerun() 

    if st.session_state.room_types is None:
        try:
            # Need to get a full list of rooms by checking a default date (e.g., the checkin date)
            sample_entry, display_to_internal = generate_data(resort, checkin_date)
            room_types = sorted(
                [
                    k
                    for k in sample_entry
                    if k not in ["HolidayWeek", "HolidayWeekStart", "holiday_name", "holiday_start", "holiday_end"]
                ]
            )
            if not room_types:
                st.error(f"No room types found for {resort}. Please ensure reference_points data is available for a non-holiday week.")
                st.stop()
            st.session_state.room_types = room_types
            st.session_state.display_to_internal = display_to_internal
        except Exception as e:
            st.error(f"Error loading room types for {resort}: {e}")
            st.stop()
    else:
        room_types = st.session_state.room_types
        display_to_internal = st.session_state.display_to_internal
        
    # --- Room Selection and Comparison ---
    col3, col4 = st.columns(2)
    with col3:
        room_type = st.selectbox(
            "Select Room Type",
            options=room_types,
            key="room_type_select"
        )
    with col4:
        compare_rooms = st.multiselect(
            "Compare With Other Room Types",
            options=[r for r in room_types if r != room_type]
        )

    # --- Date Range Adjustment ---
    original_checkin_date = checkin_date
    adjusted_checkin_date, adjusted_nights, was_adjusted = adjust_date_range(resort, checkin_date, num_nights)
    if was_adjusted:
        adjusted_end_date = adjusted_checkin_date + timedelta(days=adjusted_nights - 1)
        st.info(
            f"\U0001F384 Date range adjusted to include full holiday week: **{fmt_date(adjusted_checkin_date)}** to "
            f"**{fmt_date(adjusted_end_date)}** ({adjusted_nights} nights)."
        )

    # --- Calculation Button ---
    if st.button("Calculate"):
        
        # Generate the Gantt chart (for display at the bottom)
        gantt_fig = create_gantt_chart(resort, checkin_year)

        # ----------------------------------------------------------------------
        # RENTER MODE CALCULATIONS
        # ----------------------------------------------------------------------
        if user_mode == "Renter":
            breakdown, total_points, total_raw_points, total_rent, discount_applied, discounted_days = calculate_stay_renter(
                resort, room_type, adjusted_checkin_date, adjusted_nights, rate_per_point, booking_discount
            )
            
            st.subheader(f"1. {resort} Rental Breakdown")

            colA, colB, colC = st.columns(3)
            with colA:
                st.metric("Total Points Required (Discounted)", f"{total_points:,}")
            with colB:
                st.metric("Total Rent (Based on Raw Points)", f"${total_rent:,}", delta=f"Raw Points: {total_raw_points:,}")
            with colC:
                rate_effective = (total_rent / total_points) if total_points > 0 else 0
                st.metric("Effective Rent Rate / Point", f"${rate_effective:.2f}")

            # Discount Info
            if st.session_state.get("allow_renter_modifications", False):
                if booking_discount == "within_60_days":
                    disc_label = "30% (Presidential)"
                elif booking_discount == "within_30_days":
                    disc_label = "25% (Executive)"
                else:
                    disc_label = "No"

                if discount_applied:
                    st.info(f"\U0001F3C6 **{disc_label}** discount applied to **{len(discounted_days)}** day(s) within the booking window.")
                    st.caption("Rent is calculated based on the **Undiscounted Points** value.")
                elif booking_discount:
                    st.warning(f"\U000026A0 No **{disc_label}** discount applied. Stay dates are outside the required booking window from today ({fmt_date(datetime.now().date())}).")

            st.dataframe(breakdown, use_container_width=True, hide_index=True)

            if not breakdown.empty:
                csv_data = breakdown.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Breakdown for Excel",
                    data=csv_data,
                    file_name=f"{resort}_stay_breakdown_renter.csv",
                    mime="text/csv"
                )

            # Renter Comparison
            if compare_rooms:
                st.subheader(f"2. {resort} Room Type Comparison (Rent)")
                all_rooms = [room_type] + compare_rooms
                chart_df, compare_df_pivot, holiday_totals, _, _ = compare_room_types_renter(
                    resort, all_rooms, adjusted_checkin_date, adjusted_nights, rate_per_point, booking_discount
                )

                st.dataframe(compare_df_pivot, use_container_width=True, hide_index=True)

                if not chart_df.empty:
                    non_holiday_df = chart_df[chart_df["Holiday"] == "No"]
                    
                    # Daily Rent Chart (Non-Holiday)
                    if not non_holiday_df.empty:
                        day_order = ["Fri", "Sat", "Sun", "Mon", "Tue", "Wed", "Thu"]
                        fig_daily = px.bar(
                            non_holiday_df,
                            x="Day",
                            y="RentValue",
                            color="Room Type",
                            barmode="group",
                            labels={"RentValue": "Rent ($)", "Day": "Day of Week"},
                            height=500,
                            text_auto=True,
                            category_orders={"Day": day_order}
                        )
                        fig_daily.update_traces(texttemplate="$%{text:.0f}", textposition="auto")
                        fig_daily.update_layout(xaxis_title="Day of Week", yaxis_title="Rent ($)", legend_title_text="Room Type")
                        st.markdown("#### Daily Rent Comparison (Non-Holiday)")
                        st.plotly_chart(fig_daily, use_container_width=True)

                    # Holiday Rent Chart
                    holiday_data = []
                    for room in all_rooms:
                        for holiday_name, totals in holiday_totals[room].items():
                            if totals["rent"] > 0:
                                holiday_data.append({
                                    "Holiday": holiday_name,
                                    "Room Type": room,
                                    "RentValue": totals["rent"],
                                })
                    holiday_df = pd.DataFrame(holiday_data)
                    
                    if not holiday_df.empty:
                        fig_holiday = px.bar(
                            holiday_df,
                            x="Holiday",
                            y="RentValue",
                            color="Room Type",
                            barmode="group",
                            labels={"RentValue": "Rent ($)"},
                            height=500,
                            text_auto=True
                        )
                        fig_holiday.update_traces(texttemplate="$%{text:.0f}", textposition="auto")
                        fig_holiday.update_layout(xaxis_title="Holiday Week", yaxis_title="Rent ($)", legend_title_text="Room Type")
                        st.markdown("#### Holiday Week Rent Comparison")
                        st.plotly_chart(fig_holiday, use_container_width=True)
                
                compare_csv = compare_df_pivot.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Room Comparison for Excel",
                    data=compare_csv,
                    file_name=f"{resort}_room_comparison_renter.csv",
                    mime="text/csv"
                )

        # ----------------------------------------------------------------------
        # OWNER MODE CALCULATIONS
        # ----------------------------------------------------------------------
        else: # Owner mode
            
            breakdown, total_points, total_cost, total_maintenance_cost, total_capital_cost, total_depreciation_cost = calculate_stay_owner(
                resort, room_type, adjusted_checkin_date, adjusted_nights, discount_multiplier,
                include_maintenance, include_capital, include_depreciation, rate_per_point, capital_cost_per_point,
                cost_of_capital, useful_life, salvage_value
            )
            
            st.subheader(f"1. {resort} Owner Cost Breakdown")

            colA, colB, colC = st.columns(3)
            with colA:
                st.metric("Total Points Used (Discounted)", f"{total_points:,}")
            
            # Conditionally display cost metrics
            if include_maintenance or include_capital or include_depreciation:
                with colB:
                    st.metric("Estimated Total Cost", f"${total_cost:,}")
                with colC:
                    cost_per_pt = (total_cost / total_points) if total_points > 0 else 0
                    st.metric("Effective Cost / Point", f"${cost_per_pt:.2f}")

                with st.expander("Detailed Cost Components"):
                    comp_cols = st.columns(3)
                    if include_maintenance: comp_cols[0].metric("Maintenance Cost", f"${total_maintenance_cost:,}")
                    if include_capital: comp_cols[1].metric("Capital Cost", f"${total_capital_cost:,}")
                    if include_depreciation: comp_cols[2].metric("Depreciation Cost", f"${total_depreciation_cost:,}")
            
            else:
                 # Only show points if no cost components are selected
                with colB:
                    st.metric("Points Used (Discounted)", f"{total_points:,}")
                with colC:
                    st.caption("Select cost components in the sidebar to view cost metrics.")

            st.dataframe(breakdown, use_container_width=True, hide_index=True)

            if not breakdown.empty:
                csv_data = breakdown.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Breakdown for Excel",
                    data=csv_data,
                    file_name=f"{resort}_stay_breakdown_owner.csv",
                    mime="text/csv"
                )

            # Owner Comparison
            if compare_rooms:
                st.subheader(f"2. {resort} Room Type Comparison ({'Costs' if include_maintenance or include_capital or include_depreciation else 'Points'})")
                all_rooms = [room_type] + compare_rooms
                chart_df, compare_df_pivot, holiday_totals = compare_room_types_owner(
                    resort, all_rooms, adjusted_checkin_date, adjusted_nights, discount_multiplier,
                    discount_percent, year_select, rate_per_point,
                    capital_cost_per_point, cost_of_capital, useful_life, salvage_value,
                    include_maintenance, include_capital, include_depreciation
                )
                
                # Filter columns for display
                display_columns = ["Date"]
                if display_mode_costs:
                     # Filter for columns that contain the relevant cost/points
                     for room in all_rooms:
                         display_columns.append(f"{room} Points")
                         if include_maintenance: display_columns.append(f"{room} Maintenance")
                         if include_capital: display_columns.append(f"{room} Capital Cost")
                         if include_depreciation: display_columns.append(f"{room} Depreciation")
                         display_columns.append(f"{room} Total Cost")
                else:
                    for room in all_rooms:
                         display_columns.append(f"{room} Points")

                # Ensure columns exist before subsetting
                final_display_cols = [col for col in display_columns if col in compare_df_pivot.columns]
                
                st.dataframe(compare_df_pivot[final_display_cols], use_container_width=True, hide_index=True)

                if not chart_df.empty:
                    non_holiday_df = chart_df[chart_df["Holiday"] == "No"]
                    
                    # Daily Chart (Non-Holiday) - Points or Cost
                    if not non_holiday_df.empty:
                        day_order = ["Fri", "Sat", "Sun", "Mon", "Tue", "Wed", "Thu"]
                        y_col = "TotalCostValue" if display_mode_costs else "Points"
                        y_label = "Total Cost ($)" if display_mode_costs else "Points"
                        
                        fig_daily = px.bar(
                            non_holiday_df,
                            x="Day",
                            y=y_col,
                            color="Room Type",
                            barmode="group",
                            labels={y_col: y_label, "Day": "Day of Week"},
                            height=500,
                            text_auto=True,
                            category_orders={"Day": day_order}
                        )
                        text_template = "$%{text:.0f}" if display_mode_costs else "%{text}"
                        fig_daily.update_traces(texttemplate=text_template, textposition="auto")
                        fig_daily.update_layout(xaxis_title="Day of Week", yaxis_title=y_label, legend_title_text="Room Type")
                        st.markdown("#### Daily Comparison (Non-Holiday)")
                        st.plotly_chart(fig_daily, use_container_width=True)

                    # Holiday Chart - Points or Cost
                    holiday_data = []
                    for room in all_rooms:
                        for holiday_name, totals in holiday_totals[room].items():
                            if totals["points"] > 0:
                                holiday_data.append({
                                    "Holiday": holiday_name,
                                    "Room Type": room,
                                    "Value": totals["cost"] if display_mode_costs else totals["points"],
                                })
                    holiday_df = pd.DataFrame(holiday_data)
                    
                    if not holiday_df.empty:
                        fig_holiday = px.bar(
                            holiday_df,
                            x="Holiday",
                            y="Value",
                            color="Room Type",
                            barmode="group",
                            labels={"Value": y_label},
                            height=500,
                            text_auto=True
                        )
                        fig_holiday.update_traces(texttemplate=text_template, textposition="auto")
                        fig_holiday.update_layout(xaxis_title="Holiday Week", yaxis_title=y_label, legend_title_text="Room Type")
                        st.markdown("#### Holiday Week Comparison")
                        st.plotly_chart(fig_holiday, use_container_width=True)

                compare_csv = compare_df_pivot.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Room Comparison for Excel",
                    data=compare_csv,
                    file_name=f"{resort}_room_comparison_owner.csv",
                    mime="text/csv"
                )

        # ----------------------------------------------------------------------
        # GANTT CHART (Always at the end)
        # ----------------------------------------------------------------------
        st.subheader(f"3. {resort} Seasons and Holidays ({year_select})")
        st.plotly_chart(gantt_fig, use_container_width=True)

if __name__ == "__main__":
    main()
