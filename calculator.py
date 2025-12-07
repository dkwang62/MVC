import math
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
import pandas as pd
import streamlit as st
from common.ui import render_resort_card, render_resort_grid, render_page_header
from common.data import ensure_data_in_session

# ==============================================================================
# OFFICIAL TIER OPTIONS — ONLY THESE THREE
# ==============================================================================
TIER_OPTIONS = [
    "Ordinary Level",
    "Executive Level",
    "Presidential Level",
]

# ==============================================================================
# SETTINGS PERSISTENCE — FINAL & BULLETPROOF
# ==============================================================================
SETTINGS_FILE = "mvc_owner_settings.json"

def load_settings_from_file():
    """Load JSON file if exists, otherwise return empty dict."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_settings_to_file():
    """Save current session values to JSON file."""
    settings = {
        "maintenance_rate": st.session_state.owner_maint_rate,
        "purchase_price": st.session_state.owner_price,
        "capital_cost_pct": st.session_state.owner_coc_pct,
        "salvage_value": st.session_state.owner_salvage,
        "useful_life": st.session_state.owner_life,
        "discount_tier": st.session_state.owner_tier_sel,
        "include_maintenance": st.session_state.owner_inc_m,
        "include_capital": st.session_state.owner_inc_c,
        "include_depreciation": st.session_state.owner_inc_d,
        "renter_rate": st.session_state.renter_price,
        "renter_discount_tier": st.session_state.renter_tier_sel,
        "preferred_resort_id": st.session_state.current_resort_id
    }
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
        st.toast("Settings saved successfully!", icon="Success")
    except Exception as e:
        st.error(f"Failed to save: {e}")

def initialize_persistent_settings():
    """Run once at startup — loads file and initializes all keys."""
    file_data = load_settings_from_file()

    # Helper to safely get tier (maps "No Discount" → Ordinary Level)
    def safe_tier(key, default="Ordinary Level"):
        val = file_data.get(key, default)
        return val if val in TIER_OPTIONS else "Ordinary Level"

    # Owner settings
    if "owner_maint_rate" not in st.session_state:
        st.session_state.owner_maint_rate = float(file_data.get("maintenance_rate", 0.56))
    if "owner_price" not in st.session_state:
        st.session_state.owner_price = float(file_data.get("purchase_price", 18.0))
    if "owner_coc_pct" not in st.session_state:
        st.session_state.owner_coc_pct = float(file_data.get("capital_cost_pct", 5.0))
    if "owner_salvage" not in st.session_state:
        st.session_state.owner_salvage = float(file_data.get("salvage_value", 3.0))
    if "owner_life" not in st.session_state:
        st.session_state.owner_life = int(file_data.get("useful_life", 20))
    if "owner_tier_sel" not in st.session_state:
        st.session_state.owner_tier_sel = safe_tier("discount_tier", "Ordinary Level")
    if "owner_inc_m" not in st.session_state:
        st.session_state.owner_inc_m = bool(file_data.get("include_maintenance", True))
    if "owner_inc_c" not in st.session_state:
        st.session_state.owner_inc_c = bool(file_data.get("include_capital", False))
    if "owner_inc_d" not in st.session_state:
        st.session_state.owner_inc_d = bool(file_data.get("include_depreciation", False))

    # Renter settings
    if "renter_price" not in st.session_state:
        st.session_state.renter_price = float(file_data.get("renter_rate", 0.817))
    if "renter_tier_sel" not in st.session_state:
        st.session_state.renter_tier_sel = safe_tier("renter_discount_tier", "Ordinary Level")

    # Shared
    if "current_resort_id" not in st.session_state:
        st.session_state.current_resort_id = file_data.get("preferred_resort_id", "surfers-paradise")

# ==============================================================================
# DOMAIN MODELS
# ==============================================================================
class UserMode(Enum):
    RENTER = "Renter"
    OWNER = "Owner"

class DiscountPolicy(Enum):
    NONE = "None"
    EXECUTIVE = "within_30_days"
    PRESIDENTIAL = "within_60_days"

@dataclass
class Holiday:
    name: str
    start_date: date
    end_date: date
    room_points: Dict[str, int]

@dataclass
class DayCategory:
    days: List[str]
    room_points: Dict[str, int]

@dataclass
class SeasonPeriod:
    start: date
    end: date

@dataclass
class Season:
    name: str
    periods: List[SeasonPeriod]
    day_categories: List[DayCategory]

@dataclass
class ResortData:
    id: str
    name: str
    years: Dict[str, "YearData"]

@dataclass
class YearData:
    holidays: List[Holiday]
    seasons: List[Season]

@dataclass
class CalculationResult:
    breakdown_df: pd.DataFrame
    total_points: int
    financial_total: float
    discount_applied: bool
    discounted_days: List[str]
    m_cost: float = 0.0
    c_cost: float = 0.0
    d_cost: float = 0.0

# ==============================================================================
# REPOSITORY & CALCULATOR (unchanged from your working version)
# ==============================================================================
class MVCRepository:
    def __init__(self, raw_data: dict):
        self._raw = raw_data
        self._resort_cache: Dict[str, ResortData] = {}
        self._global_holidays = self._parse_global_holidays()

    def get_resort_list(self) -> List[str]:
        return sorted([r["display_name"] for r in self._raw.get("resorts", [])])

    def get_resort_list_full(self) -> List[Dict[str, Any]]:
        return self._raw.get("resorts", [])

    def _parse_global_holidays(self):
        parsed = {}
        for year, hols in self._raw.get("global_holidays", {}).items():
            parsed[year] = {}
            for name, data in hols.items():
                try:
                    parsed[year][name] = (
                        datetime.strptime(data["start_date"], "%Y-%m-%d").date(),
                        datetime.strptime(data["end_date"], "%Y-%m-%d").date(),
                    )
                except: continue
        return parsed

    def get_resort(self, resort_name: str) -> Optional[ResortData]:
        if resort_name in self._resort_cache:
            return self._resort_cache[resort_name]
        raw_r = next((r for r in self._raw.get("resorts", []) if r["display_name"] == resort_name), None)
        if not raw_r: return None

        years_data = {}
        for year_str, y_content in raw_r.get("years", {}).items():
            holidays = []
            for h in y_content.get("holidays", []):
                ref = h.get("global_reference")
                if ref and ref in self._global_holidays.get(year_str, {}):
                    g_dates = self._global_holidays[year_str][ref]
                    holidays.append(Holiday(
                        name=h.get("name", ref),
                        start_date=g_dates[0],
                        end_date=g_dates[1],
                        room_points=h.get("room_points", {})
                    ))

            seasons = []
            for s in y_content.get("seasons", []):
                periods = []
                for p in s.get("periods", []):
                    try:
                        periods.append(SeasonPeriod(
                            start=datetime.strptime(p["start"], "%Y-%m-%d").date(),
                            end=datetime.strptime(p["end"], "%Y-%m-%d").date()
                        ))
                    except: continue
                day_cats = []
                for cat in s.get("day_categories", {}).values():
                    day_cats.append(DayCategory(
                        days=cat.get("day_pattern", []),
                        room_points=cat.get("room_points", {})
                    ))
                seasons.append(Season(name=s["name"], periods=periods, day_categories=day_cats))
            years_data[year_str] = YearData(holidays=holidays, seasons=seasons)

        resort_obj = ResortData(id=raw_r["id"], name=raw_r["display_name"], years=years_data)
        self._resort_cache[resort_name] = resort_obj
        return resort_obj

    def get_resort_info(self, resort_name: str) -> Dict[str, str]:
        raw_r = next((r for r in self._raw.get("resorts", []) if r["display_name"] == resort_name), None)
        if raw_r:
            return {
                "full_name": raw_r.get("resort_name", resort_name),
                "timezone": raw_r.get("timezone", "Unknown"),
                "address": raw_r.get("address", "Address not available"),
            }
        return {"full_name": resort_name, "timezone": "Unknown", "address": "Address not available"}

class MVCCalculator:
    def __init__(self, repo: MVCRepository):
        self.repo = repo

    def _get_daily_points(self, resort: ResortData, day: date) -> Tuple[Dict[str, int], Optional[Holiday]]:
        year_str = str(day.year)
        if year_str not in resort.years: return {}, None
        yd = resort.years[year_str]
        for h in yd.holidays:
            if h.start_date <= day <= h.end_date: return h.room_points, h
        dow_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
        dow = dow_map[day.weekday()]
        for s in yd.seasons:
            for p in s.periods:
                if p.start <= day <= p.end:
                    for cat in s.day_categories:
                        if dow in cat.days: return cat.room_points, None
        return {}, None

    def calculate_breakdown(self, resort_name: str, room: str, checkin: date, nights: int, user_mode: UserMode, rate: float, discount_policy: DiscountPolicy, owner_config: Optional[dict]) -> CalculationResult:
        resort = self.repo.get_resort(resort_name)
        if not resort: return CalculationResult(pd.DataFrame(), 0, 0.0, False, [])

        rows, tot_pts, tot_cost = [], 0, 0.0
        tot_m = tot_c = tot_d = 0.0
        disc_applied, disc_days = False, []
        is_owner = user_mode == UserMode.OWNER
        processed = set()
        i = 0
        today = datetime.now().date()

        while i < nights:
            d = checkin + timedelta(days=i)
            pts_map, holiday = self._get_daily_points(resort, d)

            if holiday and holiday.name not in processed:
                processed.add(holiday.name)
                raw = pts_map.get(room, 0)
                eff = raw
                days_out = (holiday.start_date - today).days

                # Discount logic
                if is_owner and owner_config and owner_config.get("disc_mul", 1.0) < 1.0:
                    eff = math.floor(raw * owner_config["disc_mul"])
                    disc_applied = True
                elif not is_owner:
                    mul = 0.7 if discount_policy == DiscountPolicy.PRESIDENTIAL else 0.75 if discount_policy == DiscountPolicy.EXECUTIVE else 1.0
                    if (discount_policy == DiscountPolicy.PRESIDENTIAL and days_out <= 60) or (discount_policy == DiscountPolicy.EXECUTIVE and days_out <= 30):
                        eff = math.floor(raw * mul)
                        disc_applied = True

                cost = eff * rate
                if is_owner and owner_config:
                    m = eff * rate if owner_config.get("inc_m") else 0
                    c = eff * owner_config.get("cap_rate", 0) if owner_config.get("inc_c") else 0
                    dp = eff * owner_config.get("dep_rate", 0) if owner_config.get("inc_d") else 0
                    cost = m + c + dp
                    tot_m += m; tot_c += c; tot_d += dp

                row = {"Date": f"{holiday.name} ({holiday.start_date:%b %d} - {holiday.end_date:%b %d})", "Points": eff}
                if is_owner:
                    if owner_config.get("inc_m"): row["Maintenance"] = m
                    if owner_config.get("inc_c"): row["Capital Cost"] = c
                    if owner_config.get("inc_d"): row["Depreciation"] = dp
                    row["Total Cost"] = cost
                else:
                    row[room] = cost
                rows.append(row)
                tot_pts += eff
                i += (holiday.end_date - holiday.start_date).days + 1

            elif not holiday:
                raw = pts_map.get(room, 0)
                eff = raw
                days_out = (d - today).days

                if is_owner and owner_config and owner_config.get("disc_mul", 1.0) < 1.0:
                    eff = math.floor(raw * owner_config["disc_mul"])
                    disc_applied = True
                    disc_days.append(d.strftime("%Y-%m-%d"))
                elif not is_owner:
                    mul = 0.7 if discount_policy == DiscountPolicy.PRESIDENTIAL else 0.75 if discount_policy == DiscountPolicy.EXECUTIVE else 1.0
                    if (discount_policy == DiscountPolicy.PRESIDENTIAL and days_out <= 60) or (discount_policy == DiscountPolicy.EXECUTIVE and days_out <= 30):
                        eff = math.floor(raw * mul)
                        disc_applied = True
                        disc_days.append(d.strftime("%Y-%m-%d"))

                cost = eff * rate
                if is_owner and owner_config:
                    m = eff * rate if owner_config.get("inc_m") else 0
                    c = eff * owner_config.get("cap_rate", 0) if owner_config.get("inc_c") else 0
                    dp = eff * owner_config.get("dep_rate", 0) if owner_config.get("inc_d") else 0
                    cost = m + c + dp
                    tot_m += m; tot_c += c; tot_d += dp

                row = {"Date": d.strftime("%Y-%m-%d"), "Day": d.strftime("%a"), "Points": eff}
                if is_owner:
                    if owner_config.get("inc_m"): row["Maintenance"] = m
                    if owner_config.get("inc_c"): row["Capital Cost"] = c
                    if owner_config.get("inc_d"): row["Depreciation"] = dp
                    row["Total Cost"] = cost
                else:
                    row[room] = cost
                rows.append(row)
                tot_pts += eff
                i += 1
            else:
                i += 1

        if is_owner:
            tot_cost = tot_m + tot_c + tot_d
        else:
            tot_cost = math.ceil(tot_pts * rate)

        df = pd.DataFrame(rows)
        return CalculationResult(df, tot_pts, tot_cost, disc_applied, list(set(disc_days)), tot_m, tot_c, tot_d)

    def adjust_holiday(self, resort_name, checkin, nights):
        resort = self.repo.get_resort(resort_name)
        if not resort or str(checkin.year) not in resort.years: return checkin, nights, False
        end = checkin + timedelta(days=nights - 1)
        yd = resort.years[str(checkin.year)]
        overlapping = [h for h in yd.holidays if h.start_date <= end and h.end_date >= checkin]
        if not overlapping: return checkin, nights, False
        start = min(h.start_date for h in overlapping)
        end_adj = max(h.end_date for h in overlapping)
        return start, (end_adj - start).days + 1, True

# ==============================================================================
# MAIN APP
# ==============================================================================
def main():
    # MUST BE FIRST
    initialize_persistent_settings()

    ensure_data_in_session()
    if not st.session_state.data:
        st.warning("Data not loaded. Please use Editor.")
        return

    with st.sidebar:
        st.divider()
        with st.expander("Settings", expanded=False):
            uploaded = st.file_uploader("Load Config", type="json")
            if uploaded:
                try:
                    data = json.load(uploaded)
                    # Apply all values
                    for key in ["maintenance_rate", "purchase_price", "capital_cost_pct", "salvage_value", "useful_life",
                                "include_maintenance", "include_capital", "include_depreciation", "renter_rate"]:
                        if key in data:
                            mapped = key.replace("maintenance_rate", "owner_maint_rate").replace("purchase_price", "owner_price") \
                                .replace("capital_cost_pct", "owner_coc_pct").replace("salvage_value", "owner_salvage") \
                                .replace("useful_life", "owner_life").replace("renter_rate", "renter_price")
                            if mapped in st.session_state:
                                st.session_state[mapped] = float(data[key]) if "rate" in key or "price" in key or "pct" in key or "value" in key or "life" in key else bool(data[key])
                    st.session_state.owner_tier_sel = safe_tier(data.get("discount_tier", "Ordinary Level"))
                    st.session_state.renter_tier_sel = safe_tier(data.get("renter_discount_tier", "Ordinary Level"))
                    if "preferred_resort_id" in data:
                        st.session_state.current_resort_id = data["preferred_resort_id"]
                    save_settings_to_file()
                    st.success("Config loaded!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

            if st.button("Save Current Settings"):
                save_settings_to_file()

        st.markdown("### User Mode")
        mode = st.selectbox("Mode", ["Renter", "Owner"], key="mode_sel")

        owner_params = None
        policy = DiscountPolicy.NONE
        active_rate = 0.0

        if mode == "Owner":
            st.markdown("#### Owner Parameters")
            st.number_input("Maintenance per Point ($)", 0.0, None, key="owner_maint_rate", step=0.01)
            st.radio("Membership Tier", TIER_OPTIONS, key="owner_tier_sel")
            st.number_input("Purchase Price ($)", 0.0, None, key="owner_price", step=0.5)
            st.number_input("Cost of Capital (%)", 0.0, None, key="owner_coc_pct", step=0.1)
            st.number_input("Useful Life (yrs)", 1, None, key="owner_life")
            st.number_input("Salvage Value ($/pt)", 0.0, None, key="owner_salvage", step=0.1)
            st.checkbox("Include Maintenance", key="owner_inc_m")
            st.checkbox("Include Capital Cost", key="owner_inc_c")
            st.checkbox("Include Depreciation", key="owner_inc_d")

            active_rate = st.session_state.owner_maint_rate
            tier = st.session_state.owner_tier_sel
            disc_mul = 1.0
            if tier == "Executive Level": disc_mul = 0.75
            elif tier == "Presidential Level": disc_mul = 0.7

            owner_params = {
                "disc_mul": disc_mul,
                "inc_m": st.session_state.owner_inc_m,
                "inc_c": st.session_state.owner_inc_c,
                "inc_d": st.session_state.owner_inc_d,
                "cap_rate": st.session_state.owner_price * (st.session_state.owner_coc_pct / 100.0),
                "dep_rate": (st.session_state.owner_price - st.session_state.owner_salvage) / st.session_state.owner_life if st.session_state.owner_life else 0
            }
        else:
            st.markdown("#### Renter Parameters")
            st.number_input("Renter Rate ($)", 0.0, None, key="renter_price", step=0.01)
            st.radio("Membership Tier", TIER_OPTIONS, key="renter_tier_sel")
            active_rate = st.session_state.renter_price
            tier = st.session_state.renter_tier_sel
            if tier == "Presidential Level": policy = DiscountPolicy.PRESIDENTIAL
            elif tier == "Executive Level": policy = DiscountPolicy.EXECUTIVE

    # Rest of your UI...
    repo = MVCRepository(st.session_state.data)
    resorts = repo.get_resort_list_full()

    if not st.session_state.get("current_resort_id") and resorts:
        st.session_state.current_resort_id = resorts[0]["id"]

    render_page_header("MVC Calculator", f"{mode} Mode")
    render_resort_grid(resorts, st.session_state.current_resort_id)

    curr_id = st.session_state.current_resort_id
    resort_obj = next((r for r in resorts if r["id"] == curr_id), None)
    if not resort_obj: return
    r_name = resort_obj["display_name"]

    info = repo.get_resort_info(r_name)
    render_resort_card(info["full_name"], info["timezone"], info["address"])
    st.divider()

    c1, c2, c3, c4 = st.columns([2,1,2,2])
    checkin = c1.date_input("Check-in", datetime.now().date() + timedelta(days=30))
    nights = c2.number_input("Nights", 1, 60, 7)

    calc = MVCCalculator(repo)
    adj_in, adj_n, adj = calc.adjust_holiday(r_name, checkin, nights)
    if adj:
        st.info(f"Adjusted to full holiday: {adj_in} → {adj_n} nights")

    final_in = adj_in if adj else checkin
    final_n = adj_n if adj else nights

    res_data = repo.get_resort(r_name)
    rooms = get_all_room_types_for_resort(res_data)
    if not rooms:
        st.error("No room data.")
        return

    sel_room = c3.selectbox("Room Type", rooms)
    comp_rooms = c4.multiselect("Compare", [r for r in rooms if r != sel_room])

    st.divider()
    result = calc.calculate_breakdown(r_name, sel_room, final_in, final_n, UserMode(mode.upper()), active_rate, policy, owner_params)

    st.metric("Total Points", f"{result.total_points:,}")
    st.metric("Total Cost", f"${result.financial_total:,.0f}")

    with st.expander("Daily Breakdown"):
        st.dataframe(result.breakdown_df)

def get_all_room_types_for_resort(resort_data: ResortData) -> List[str]:
    rooms = set()
    for year in resort_data.years.values():
        for h in year.holidays:
            rooms.update(h.room_points.keys())
        for s in year.seasons:
            for c in s.day_categories:
                rooms.update(c.room_points.keys())
    return sorted(rooms)

def run():
    main()

if __name__ == "__main__":
    run()
