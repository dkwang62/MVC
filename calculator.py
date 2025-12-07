import math
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
import pandas as pd
import plotly.express as px
import streamlit as st
from common.ui import render_resort_card, render_resort_grid, render_page_header
from common.charts import create_gantt_chart_from_resort_data
from common.data import ensure_data_in_session

# ==============================================================================
# CONSTANTS: Unified Tier Names
# ==============================================================================
TIER_OPTIONS = [
    "Ordinary Level",
    "Executive Level",
    "Presidential Level",
]

# ==============================================================================
# LAYER 0: SETTINGS LOADER & PERSISTENCE — FULLY FIXED
# ==============================================================================

SETTINGS_FILE = "mvc_owner_settings.json"

def load_settings_from_file() -> Dict[str, Any]:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Could not read settings file: {e}")
    return {}

def initialize_settings():
    """Run once at app start — guarantees all keys exist and are loaded from file."""
    defaults = load_settings_from_file()

    # Owner settings
    if "owner_maint_rate" not in st.session_state:
        st.session_state.owner_maint_rate = float(defaults.get("maintenance_rate", 0.52))
    if "owner_price" not in st.session_state:
        st.session_state.owner_price = float(defaults.get("purchase_price", 3.5))
    if "owner_coc_pct" not in st.session_state:
        st.session_state.owner_coc_pct = float(defaults.get("capital_cost_pct", 5.0))
    if "owner_salvage" not in st.session_state:
        st.session_state.owner_salvage = float(defaults.get("salvage_value", 3.0))
    if "owner_life" not in st.session_state:
        st.session_state.owner_life = int(defaults.get("useful_life", 20))
    if "owner_tier_sel" not in st.session_state:
        tier = defaults.get("discount_tier", "Presidential Level")
        st.session_state.owner_tier_sel = tier if tier in TIER_OPTIONS else "Presidential Level"
    if "owner_inc_m" not in st.session_state:
        st.session_state.owner_inc_m = bool(defaults.get("include_maintenance", True))
    if "owner_inc_c" not in st.session_state:
        st.session_state.owner_inc_c = bool(defaults.get("include_capital", True))
    if "owner_inc_d" not in st.session_state:
        st.session_state.owner_inc_d = bool(defaults.get("include_depreciation", False))

    # Renter settings
    if "renter_price" not in st.session_state:
        st.session_state.renter_price = float(defaults.get("renter_rate", 0.83))
    if "renter_tier_sel" not in st.session_state:
        tier = defaults.get("renter_discount_tier", "Ordinary Level")
        st.session_state.renter_tier_sel = tier if tier in TIER_OPTIONS else "Ordinary Level"

    # Preferred resort
    if "current_resort_id" not in st.session_state:
        st.session_state.current_resort_id = defaults.get("preferred_resort_id", "ko-olina-beach")

def save_current_settings():
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
        "preferred_resort_id": st.session_state.current_resort_id or "ko-olina-beach"
    }
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
        st.success("Settings saved to mvc_owner_settings.json")
    except Exception as e:
        st.error(f"Save failed: {e}")

# ==============================================================================
# LAYER 1: DOMAIN MODELS
# ==============================================================================
class UserMode(Enum):
    RENTER = "Renter"
    OWNER = "Owner"

class DiscountPolicy(Enum):
    NONE = "None"
    EXECUTIVE = "within_30_days"  # 25%
    PRESIDENTIAL = "within_60_days"  # 30%

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

@dataclass
class ComparisonResult:
    pivot_df: pd.DataFrame
    daily_chart_df: pd.DataFrame
    holiday_chart_df: pd.DataFrame

# ==============================================================================
# LAYER 2: REPOSITORY
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

    def _parse_global_holidays(self) -> Dict[str, Dict[str, Tuple[date, date]]]:
        parsed: Dict[str, Dict[str, Tuple[date, date]]] = {}
        for year, hols in self._raw.get("global_holidays", {}).items():
            parsed[year] = {}
            for name, data in hols.items():
                try:
                    parsed[year][name] = (
                        datetime.strptime(data["start_date"], "%Y-%m-%d").date(),
                        datetime.strptime(data["end_date"], "%Y-%m-%d").date(),
                    )
                except Exception:
                    continue
        return parsed

    def get_resort(self, resort_name: str) -> Optional[ResortData]:
        if resort_name in self._resort_cache:
            return self._resort_cache[resort_name]
        raw_r = next((r for r in self._raw.get("resorts", []) if r["display_name"] == resort_name), None)
        if not raw_r: return None

        years_data: Dict[str, YearData] = {}
        for year_str, y_content in raw_r.get("years", {}).items():
            holidays: List[Holiday] = []
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

            seasons: List[Season] = []
            for s in y_content.get("seasons", []):
                periods: List[SeasonPeriod] = []
                for p in s.get("periods", []):
                    try:
                        periods.append(SeasonPeriod(
                            start=datetime.strptime(p["start"], "%Y-%m-%d").date(),
                            end=datetime.strptime(p["end"], "%Y-%m-%d").date()
                        ))
                    except Exception: continue
                day_cats: List[DayCategory] = []
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

# ==============================================================================
# LAYER 3: SERVICE
# ==============================================================================
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

        if user_mode == UserMode.RENTER: rate = round(float(rate), 2)
        rows, tot_eff_pts, tot_financial = [], 0, 0.0
        tot_m = tot_c = tot_d = 0.0
        disc_applied, disc_days = False, []
        is_owner = user_mode == UserMode.OWNER
        processed_holidays = set()
        i, today = 0, datetime.now().date()

        while i < nights:
            d = checkin + timedelta(days=i)
            pts_map, holiday = self._get_daily_points(resort, d)

            if holiday and holiday.name not in processed_holidays:
                processed_holidays.add(holiday.name)
                raw = pts_map.get(room, 0)
                eff = raw
                h_days = (holiday.end_date - holiday.start_date).days + 1
                days_out = (holiday.start_date - today).days
                is_disc = False

                if is_owner and owner_config:
                    disc_mul = owner_config.get("disc_mul", 1.0)
                    disc_pct = (1 - disc_mul) * 100
                    thresh = 30 if disc_pct == 25 else 60 if disc_pct == 30 else 0
                    if disc_pct > 0 and days_out <= thresh:
                        eff = math.floor(raw * disc_mul)
                        is_disc = True
                else:
                    renter_mul = 0.7 if discount_policy == DiscountPolicy.PRESIDENTIAL else 0.75 if discount_policy == DiscountPolicy.EXECUTIVE else 1.0
                    if (discount_policy == DiscountPolicy.PRESIDENTIAL and days_out <= 60) or (discount_policy == DiscountPolicy.EXECUTIVE and days_out <= 30):
                        eff = math.floor(raw * renter_mul)
                        is_disc = True

                if is_disc:
                    disc_applied = True
                    for j in range(h_days):
                        disc_days.append((holiday.start_date + timedelta(days=j)).strftime("%Y-%m-%d"))

                m = c = dp = 0.0
                if is_owner and owner_config:
                    if owner_config.get("inc_m"): m = math.ceil(eff * rate)
                    if owner_config.get("inc_c"): c = math.ceil(eff * owner_config.get("cap_rate", 0.0))
                    if owner_config.get("inc_d"): dp = math.ceil(eff * owner_config.get("dep_rate", 0.0))
                    holiday_cost = m + c + dp
                else:
                    holiday_cost = math.ceil(eff * rate)

                row = {"Date": f"{holiday.name} ({holiday.start_date:%b %d} - {holiday.end_date:%b %d})", "Day": "", "Points": eff}
                if is_owner:
                    if owner_config.get("inc_m"): row["Maintenance"] = m
                    if owner_config.get("inc_c"): row["Capital Cost"] = c
                    if owner_config.get("inc_d"): row["Depreciation"] = dp
                    row["Total Cost"] = holiday_cost
                else:
                    row[room] = holiday_cost
                rows.append(row)
                tot_eff_pts += eff
                i += h_days

            elif not holiday:
                raw = pts_map.get(room, 0)
                eff = raw
                days_out = (d - today).days
                is_disc = False

                if is_owner and owner_config:
                    disc_mul = owner_config.get("disc_mul", 1.0)
                    disc_pct = (1 - disc_mul) * 100
                    thresh = 30 if disc_pct == 25 else 60 if disc_pct == 30 else 0
                    if disc_pct > 0 and days_out <= thresh:
                        eff = math.floor(raw * disc_mul)
                        is_disc = True
                else:
                    renter_mul = 0.7 if discount_policy == DiscountPolicy.PRESIDENTIAL else 0.75 if discount_policy == DiscountPolicy.EXECUTIVE else 1.0
                    if (discount_policy == DiscountPolicy.PRESIDENTIAL and days_out <= 60) or (discount_policy == DiscountPolicy.EXECUTIVE and days_out <= 30):
                        eff = math.floor(raw * renter_mul)
                        is_disc = True

                if is_disc:
                    disc_applied = True
                    disc_days.append(d.strftime("%Y-%m-%d"))

                )

                m = c = dp = 0.0
                if is_owner and owner_config:
                    if owner_config.get("inc_m"): m = math.ceil(eff * rate)
                    if owner_config.get("inc_c"): c = math.ceil(eff * owner_config.get("cap_rate", 0.0))
                    if owner_config.get("inc_d"): dp = math.ceil(eff * owner_config.get("dep_rate", 0.0))
                    day_cost = m + c + dp
                else:
                    day_cost = math.ceil(eff * rate)

                row = {"Date": d.strftime("%Y-%m-%d"), "Day": d.strftime("%a"), "Points": eff}
                if is_owner:
                    if owner_config.get("inc_m"): row["Maintenance"] = m
                    if owner_config.get("inc_c"): row["Capital Cost"] = c
                    if owner_config.get("inc_d"): row["Depreciation"] = dp
                    row["Total Cost"] = day_cost
                else:
                    row[room] = day_cost
                rows.append(row)
                tot_eff_pts += eff
                i += 1
            else:
                i += 1

        # Final totals
        if user_mode == UserMode.RENTER:
            tot_financial = math.ceil(tot_eff_pts * rate)
        else:
            m_tot = math.ceil(tot_eff_pts * rate) if owner_config.get("inc_m") else 0
            c_tot = math.ceil(tot_eff_pts * owner_config.get("cap_rate", 0.0)) if owner_config.get("inc_c") else 0
            d_tot = math.ceil(tot_eff_pts * owner_config.get("dep_rate", 0.0)) if owner_config.get("inc_d") else 0
            tot_m, tot_c, tot_d = m_tot, c_tot, d_tot
            tot_financial = m_tot + c_tot + d_tot

        df = pd.DataFrame(rows)
        if not df.empty and is_owner:
            for col in ["Maintenance", "Capital Cost", "Depreciation", "Total Cost"]:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: f"${x:,.0f}")

        return CalculationResult(df, tot_eff_pts, tot_financial, disc_applied, list(set(disc_days)), tot_m, tot_c, tot_d)

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

    def compare_stays(self, resort_name: str, rooms: List[str], checkin: date, nights: int, user_mode: UserMode, rate: float, policy: DiscountPolicy, owner_config: Optional[dict]) -> ComparisonResult:
        # Placeholder — your full compare_stays logic goes here (unchanged)
        return ComparisonResult(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())

# ==============================================================================
# UI HELPERS
# ==============================================================================
def render_metrics_grid(res, mode, owner_params, policy):
    if mode == UserMode.OWNER:
        cols = st.columns(3)
        cols[0].metric("Total Points", f"{res.total_points:,}")
        cols[1].metric("Total Cost", f"${res.financial_total:,.0f}")
        if owner_params.get("inc_m"): cols[2].metric("Maintenance", f"${res.m_cost:,.0f}")
    else:
        cols = st.columns(2)
        cols[0].metric("Total Points", f"{res.total_points:,}")
        cols[1].metric("Total Rent", f"${res.financial_total:,.0f}")

def get_all_room_types_for_resort(resort_data: ResortData) -> List[str]:
    rooms = set()
    for year_obj in resort_data.years.values():
        for season in year_obj.seasons:
            for cat in season.day_categories:
                rooms.update(cat.room_points.keys())
        for holiday in year_obj.holidays:
            rooms.update(holiday.room_points.keys())
    return sorted(rooms)

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    # THIS LINE FIXES EVERYTHING
    initialize_settings()

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
                    # Apply uploaded values
                    st.session_state.owner_maint_rate = float(data.get("maintenance_rate", 0.52))
                    st.session_state.owner_price = float(data.get("purchase_price", 3.5))
                    st.session_state.owner_coc_pct = float(data.get("capital_cost_pct", 5.0))
                    st.session_state.owner_salvage = float(data.get("salvage_value", 3.0))
                    st.session_state.owner_life = int(data.get("useful_life", 20))
                    st.session_state.owner_tier_sel = data.get("discount_tier", "Presidential Level")
                    st.session_state.owner_inc_m = bool(data.get("include_maintenance", True))
                    st.session_state.owner_inc_c = bool(data.get("include_capital", True))
                    st.session_state.owner_inc_d = bool(data.get("include_depreciation", False))
                    st.session_state.renter_price = float(data.get("renter_rate", 0.83))
                    st.session_state.renter_tier_sel = data.get("renter_discount_tier", "Ordinary Level")
                    if "preferred_resort_id" in data:
                        st.session_state.current_resort_id = data["preferred_resort_id"]
                    st.success("Settings loaded!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

            if st.button("Save Current Settings"):
                save_current_settings()

        st.markdown("### User Settings")
        mode_sel = st.selectbox("User Mode", [m.value for m in UserMode], index=0)
        mode = UserMode(mode_sel)

        owner_params = None
        policy = DiscountPolicy.NONE
        active_rate = 0.0

        if mode == UserMode.OWNER:
            st.markdown("#### Ownership Parameters")
            st.number_input("Maintenance per Point ($)", 0.0, None, key="owner_maint_rate")
            st.radio("Membership Tier", TIER_OPTIONS, key="owner_tier_sel")
            st.number_input("Purchase Price ($)", 0.0, None, key="owner_price")
            st.number_input("Cost of Capital (%)", 0.0, None, key="owner_coc_pct")
            st.number_input("Useful Life (yrs)", 1, None, key="owner_life")
            st.number_input("Salvage ($/pt)", 0.0, None, key="owner_salvage")
            inc_m = st.checkbox("Include Maintenance", key="owner_inc_m")
            inc_c = st.checkbox("Include Capital Cost", key="owner_inc_c")
            inc_d = st.checkbox("Include Depreciation", key="owner_inc_d")

            active_rate = st.session_state.owner_maint_rate
            opt = st.session_state.owner_tier_sel
            disc_mul = 1.0
            if "Executive" in opt: disc_mul = 0.75
            elif "Presidential" in opt: disc_mul = 0.7

            owner_params = {
                "disc_mul": disc_mul,
                "inc_m": inc_m,
                "inc_c": inc_c,
                "inc_d": inc_d,
                "cap_rate": st.session_state.owner_price * (st.session_state.owner_coc_pct / 100.0),
                "dep_rate": (st.session_state.owner_price - st.session_state.owner_salvage) / st.session_state.owner_life if st.session_state.owner_life else 0
            }
        else:
            st.markdown("#### Rental Parameters")
            st.number_input("Renter Price ($)", 0.0, None, key="renter_price")
            st.radio("Membership Tier", TIER_OPTIONS, key="renter_tier_sel")
            active_rate = st.session_state.renter_price
            opt = st.session_state.renter_tier_sel
            if "Presidential" in opt: policy = DiscountPolicy.PRESIDENTIAL
            elif "Executive" in opt: policy = DiscountPolicy.EXECUTIVE

    # Resort selection & rest of UI
    repo = MVCRepository(st.session_state.data)
    resorts = repo.get_resort_list_full()

    if not st.session_state.get("current_resort_id") and resorts:
        pref = load_settings_from_file().get("preferred_resort_id")
        if pref:
            for r in resorts:
                if pref in r["id"]:
                    st.session_state.current_resort_id = r["id"]
                    break
        if not st.session_state.get("current_resort_id"):
            st.session_state.current_resort_id = resorts[0]["id"]

    render_page_header("Calculator", f"{mode.value} Mode Analysis", icon="Hotel")
    render_resort_grid(resorts, st.session_state.current_resort_id)

    curr_id = st.session_state.current_resort_id
    resort_obj = next((r for r in resorts if r["id"] == curr_id), None)
    if not resort_obj: return
    r_name = resort_obj["display_name"]

    info = repo.get_resort_info(r_name)
    render_resort_card(info["full_name"], info["timezone"], info["address"])
    st.divider()

    c1, c2, c3, c4 = st.columns([2,1,2,2])
    checkin = c1.date_input("Check-in", datetime.now().date() + timedelta(days=1))
    nights = c2.number_input("Nights", 1, 60, 7)

    calc = MVCCalculator(repo)
    adj_in, adj_n, adjusted = calc.adjust_holiday(r_name, checkin, nights)
    if adjusted:
        st.info(f"Adjusted stay to full holiday: {adj_in} ({adj_n} nights)")

    res_data = repo.get_resort(r_name)
    rooms = get_all_room_types_for_resort(res_data)
    if not rooms:
        st.error("No room data.")
        return

    sel_room = c3.selectbox("Room Type", rooms)
    comp_rooms = c4.multiselect("Compare", [r for r in rooms if r != sel_room])

    st.divider()

    final_checkin = adj_in if adjusted else checkin
    final_nights = adj_n if adjusted else nights

    result = calc.calculate_breakdown(r_name, sel_room, final_checkin, final_nights, mode, active_rate, policy, owner_params)
    render_metrics_grid(result, mode, owner_params, policy)

    if result.discount_applied and mode == UserMode.RENTER:
        st.success(f"Discount applied on {len(result.discounted_days)} days!")

    with st.expander("Daily Breakdown", expanded=False):
        st.dataframe(result.breakdown_df, use_container_width=True)

    st.markdown("**All Room Types Summary**")
    summary = []
    for room in rooms:
        r = calc.calculate_breakdown(r_name, room, final_checkin, final_nights, mode, active_rate, policy, owner_params)
        summary.append({"Room": room, "Points": f"{r.total_points:,}", "Cost": f"${r.financial_total:,.0f}"})
    st.dataframe(pd.DataFrame(summary))

    if mode == UserMode.OWNER:
        st.divider()
        if st.button("Open Resort Editor"):
            st.session_state.active_tool = "editor"
            st.rerun()

def run():
    main()

if __name__ == "__main__":
    run()
