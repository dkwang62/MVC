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
# SETTINGS PERSISTENCE — BULLETPROOF
# ==============================================================================
SETTINGS_FILE = "mvc_owner_settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_settings():
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
        st.toast("Settings saved!", icon="Success")
    except:
        st.error("Failed to save settings.")

def initialize_settings():
    data = load_settings()
    defaults = {
        "owner_maint_rate": float(data.get("maintenance_rate", 0.83)),
        "owner_price": float(data.get("purchase_price", 3.5)),
        "owner_coc_pct": float(data.get("capital_cost_pct", 5.0)),
        "owner_salvage": float(data.get("salvage_value", 3.0)),
        "owner_life": int(data.get("useful_life", 20)),
        "owner_tier_sel": "Ordinary Level" if data.get("discount_tier", "").lower() in ["no discount", "", None] else data.get("discount_tier", "Ordinary Level"),
        "owner_inc_m": bool(data.get("include_maintenance", True)),
        "owner_inc_c": bool(data.get("include_capital", True)),
        "owner_inc_d": bool(data.get("include_depreciation", False)),
        "renter_price": float(data.get("renter_rate", 0.83)),
        "renter_tier_sel": "Ordinary Level" if data.get("renter_discount_tier", "").lower() in ["no discount", "", None] else data.get("renter_discount_tier  data.get("renter_discount_tier", "Ordinary Level"),
        "current_resort_id": data.get("preferred_resort_id"),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ==============================================================================
# LAYER 1: DOMAIN MODELS
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

    def calculate_breakdown(self, resort_name: str, room: str, checkin: date, nights: int, user_mode: UserMode, rate: float, discount_policy: DiscountPolicy = DiscountPolicy.NONE, owner_config: Optional[dict] = None) -> CalculationResult:
        resort = self.repo.get_resort(resort_name)
        if not resort: return CalculationResult(pd.DataFrame(), 0, 0.0, False, [])

        if user_mode == UserMode.RENTER:
            rate = round(float(rate), 2)

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
                raw, eff = pts_map.get(room, 0), pts_map.get(room, 0)
                h_days = (holiday.end_date - holiday.start_date).days + 1
                days_out = (holiday.start_date - today).days
                is_disc = False

                if is_owner and owner_config:
                    disc_mul = owner_config.get("disc_mul", 1.0)
                    if disc_mul < 1.0 and days_out <= (30 if disc_mul == 0.75 else 60):
                        eff = math.floor(raw * disc_mul)
                        is_disc = True
                else:
                    mul = 0.7 if discount_policy == DiscountPolicy.PRESIDENTIAL else 0.75 if discount_policy == DiscountPolicy.EXECUTIVE else 1.0
                    if (discount_policy == DiscountPolicy.PRESIDENTIAL and days_out <= 60) or (discount_policy == DiscountPolicy.EXECUTIVE and days_out <= 30):
                        eff = math.floor(raw * mul)
                        is_disc = True

                if is_disc:
                    disc_applied = True
                    for j in range(h_days):
                        disc_days.append((holiday.start_date + timedelta(days=j)).strftime("%Y-%m-%d"))

                m = c = dp = 0.0
                if is_owner and owner_config:
                    if owner_config.get("inc_m"): m = math.ceil(round(eff * rate, 8))
                    if owner_config.get("inc_c"): c = math.ceil(round(eff * owner_config.get("cap_rate", 0.0), 8))
                    if owner_config.get("inc_d"): dp = math.ceil(round(eff * owner_config.get("dep_rate", 0.0), 8))
                    holiday_cost = m + c + dp
                else:
                    holiday_cost = math.ceil(round(eff * rate, 8))

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
                raw, eff = pts_map.get(room, 0), pts_map.get(room, 0)
                days_out = (d - today).days
                is_disc = False

                if is_owner and owner_config:
                    disc_mul = owner_config.get("disc_mul", 1.0)
                    if disc_mul < 1.0 and days_out <= (30 if disc_mul == 0.75 else 60):
                        eff = math.floor(raw * disc_mul)
                        is_disc = True
                else:
                    mul = 0.7 if discount_policy == DiscountPolicy.PRESIDENTIAL else 0.75 if discount_policy == DiscountPolicy.EXECUTIVE else 1.0
                    if (discount_policy == DiscountPolicy.PRESIDENTIAL and days_out <= 60) or (discount_policy == DiscountPolicy.EXECUTIVE and days_out <= 30):
                        eff = math.floor(raw * mul)
                        is_disc = True

                if is_disc:
                    disc_applied = True
                    disc_days.append(d.strftime("%Y-%m-%d"))

                m = c = dp = 0.0
                if is_owner and owner_config:
                    if owner_config.get("inc_m"): m = math.ceil(round(eff * rate, 8))
                    if owner_config.get("inc_c"): c = math.ceil(round(eff * owner_config.get("cap_rate", 0.0), 8))
                    if owner_config.get("inc_d"): dp = math.ceil(round(eff * owner_config.get("dep_rate", 0.0), 8))
                    day_cost = m + c + dp
                else:
                    day_cost = math.ceil(round(eff * rate, 8))

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

        if user_mode == UserMode.RENTER:
            tot_financial = math.ceil(round(tot_eff_pts * rate, 8))
        elif is_owner and owner_config:
            tot_m = math.ceil(round(tot_eff_pts * rate, 8)) if owner_config.get("inc_m") else 0.0
            tot_c = math.ceil(round(tot_eff_pts * owner_config.get("cap_rate", 0.0), 8)) if owner_config.get("inc_c") else 0.0
            tot_d = math.ceil(round(tot_eff_pts * owner_config.get("dep_rate", 0.0), 8)) if owner_config.get("inc_d") else 0.0
            tot_financial = tot_m + tot_c + tot_d

        df = pd.DataFrame(rows)
        if is_owner and not df.empty:
            for col in ["Maintenance", "Capital Cost", "Depreciation", "Total Cost"]:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: f"${x:,.0f}" if isinstance(x, (int, float)) else x)
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

def get_all_room_types_for_resort(resort_data: ResortData) -> List[str]:
    rooms = set()
    for year in resort_data.years.values():
        for h in year.holidays:
            rooms.update(h.room_points.keys())
        for s in year.seasons:
            for c in s.day_categories:
                rooms.update(c.room_points.keys())
    return sorted(rooms)

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    initialize_settings()  # ← CRITICAL FIX
    ensure_data_in_session()
    if not st.session_state.data:
        st.warning("Please open the Editor and upload/merge data_v2.json first.")
        return

    with st.sidebar:
        st.divider()
        with st.expander("Settings", expanded=False):
            uploaded = st.file_uploader("Load Config", type="json")
            if uploaded:
                try:
                    data = json.load(uploaded)
                    for k, v in data.items():
                        if k == "maintenance_rate": st.session_state.owner_maint_rate = float(v)
                        if k == "purchase_price": st.session_state.owner_price = float(v)
                        if k == "capital_cost_pct": st.session_state.owner_coc_pct = float(v)
                        if k == "salvage_value": st.session_state.owner_salvage = float(v)
                        if k == "useful_life": st.session_state.owner_life = int(v)
                        if k == "discount_tier": st.session_state.owner_tier_sel = v if v in ["Ordinary Level","Executive Level","Presidential Level"] else "Ordinary Level"
                        if k == "include_maintenance": st.session_state.owner_inc_m = bool(v)
                        if k == "include_capital": st.session_state.owner_inc_c = bool(v)
                        if k == "include_depreciation": st.session_state.owner_inc_d = bool(v)
                        if k == "renter_rate": st.session_state.renter_price = float(v)
                        if k == "renter_discount_tier": st.session_state.renter_tier_sel = v if v in ["Ordinary Level","Executive Level","Presidential Level"] else "Ordinary Level"
                        if k == "preferred_resort_id": st.session_state.current_resort_id = v
                    save_settings()
                    st.success("Config loaded!")
                    st.rerun()
                except: st.error("Invalid JSON")

            if st.button("Save Current Settings"):
                save_settings()

        st.markdown("### User Settings")
        mode = st.selectbox("User Mode", ["Renter", "Owner"], key="mode_sel")

        owner_params = None
        policy = DiscountPolicy.NONE
        active_rate = 0.0
        disc_mul = 1.0

        if mode == "Owner":
            st.markdown("#### Ownership Parameters")
            st.number_input("Maintenance per Point ($)", 0.0, None, key="owner_maint_rate", step=0.01)
            st.radio("Membership Tier", ["Ordinary Level", "Executive Level", "Presidential Level"], key="owner_tier_sel")
            st.number_input("Purchase Price ($)", 0.0, None, key="owner_price", step=0.5)
            st.number_input("Cost of Capital (%)", 0.0, None, key="owner_coc_pct", step=0.1)
            st.number_input("Useful Life (yrs)", 1, None, key="owner_life")
            st.number_input("Salvage ($/pt)", 0.0, None, key="owner_salvage", step=0.1)
            st.checkbox("Include Maintenance", key="owner_inc_m")
            st.checkbox("Include Capital Cost", key="owner_inc_c")
            st.checkbox("Include Depreciation", key="owner_inc_d")

            active_rate = st.session_state.owner_maint_rate
            tier = st.session_state.owner_tier_sel
            disc_mul = 0.75 if tier == "Executive Level" else 0.7 if tier == "Presidential Level" else 1.0

            owner_params = {
                "disc_mul": disc_mul,
                "inc_m": st.session_state.owner_inc_m,
                "inc_c": st.session_state.owner_inc_c,
                "inc_d": st.session_state.owner_inc_d,
                "cap_rate": st.session_state.owner_price * (st.session_state.owner_coc_pct / 100.0),
                "dep_rate": (st.session_state.owner_price - st.session_state.owner_salvage) / st.session_state.owner_life if st.session_state.owner_life else 0
            }
        else:
            st.markdown("#### Rental Parameters")
            st.number_input("Renter Price ($)", 0.0, None, key="renter_price", step=0.01)
            st.radio("Membership Tier", ["Ordinary Level", "Executive Level", "Presidential Level"], key="renter_tier_sel")
            active_rate = st.session_state.renter_price
            tier = st.session_state.renter_tier_sel
            if tier == "Presidential Level": policy = DiscountPolicy.PRESIDENTIAL
            elif tier == "Executive Level": policy = DiscountPolicy.EXECUTIVE

    repo = MVCRepository(st.session_state.data)
    resorts = repo.get_resort_list_full()

    if not st.session_state.get("current_resort_id") and resorts:
        st.session_state.current_resort_id = resorts[0]["id"]

    render_page_header("Calculator", f"{mode} Mode Analysis", icon="Hotel")
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
    adj_in, adj_n, adj = calc.adjust_holiday(r_name, checkin, nights)
    if adj:
        st.info(f"Adjusted to full holiday: {adj_in} ({adj_n} nights)")

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
    # ← FIXED LINE
    result = calc.calculate_breakdown(r_name, sel_room, final_in, final_n, UserMode[mode.upper()], active_rate, policy, owner_params)

    st.metric("Total Points", f"{result.total_points:,}")
    st.metric("Total Cost", f"${result.financial_total:,.0f}")

    with st.expander("Daily Breakdown", expanded=False):
        st.dataframe(result.breakdown_df, use_container_width=True)

    st.markdown("**All Room Types**")
    all_res = []
    for r in rooms:
        rr = calc.calculate_breakdown(r_name, r, final_in, final_n, UserMode[mode.upper()], active_rate, policy, owner_params)
        all_res.append({"Room": r, "Points": f"{rr.total_points:,}", "Cost": f"${rr.financial_total:,.0f}"})
    st.dataframe(pd.DataFrame(all_res), use_container_width=True)

    if mode == "Owner":
        st.divider()
        if st.button("Open Resort Editor"):
            st.session_state.active_tool = "editor"
            st.rerun()

def run():
    main()

if __name__ == "__main__":
    run()
