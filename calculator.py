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
# CONSTANTS
# ==============================================================================
TIER_NO_DISCOUNT = "Ordinary"
TIER_EXECUTIVE = "Executive"
TIER_PRESIDENTIAL = "Presidential"

# ==============================================================================
# INITIALIZATION (Moved inside a function to run on every script execution)
# ==============================================================================
def initialize_state():
    """Ensure all session state variables exist before the app runs."""
    
    # 1. Define Defaults
    defaults = {
        "pref_maint_rate": 0.83,
        "pref_purchase_price": 3.5,
        "pref_capital_cost_pct": 5.0,
        "pref_salvage_value": 3.0,
        "pref_useful_life": 20,
        "pref_discount_tier": TIER_NO_DISCOUNT,
        "pref_inc_m": True,
        "pref_inc_c": True,
        "pref_inc_d": False,
        "renter_rate_val": 0.83,
        "renter_discount_tier": TIER_NO_DISCOUNT,
        "preferred_resort_id": None,
        # Calculator specific
        "calc_checkin": datetime.now().date() + timedelta(days=1),
        "calc_initial_default": datetime.now().date() + timedelta(days=1),
        "calc_checkin_user_set": False
    }

    # 2. Apply Defaults (if key missing)
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # 3. Auto-load Local Settings (Only once per session)
    if "profile_auto_loaded" not in st.session_state:
        local_path = "mvc_owner_settings.json"
        if os.path.exists(local_path):
            try:
                with open(local_path, "r") as f:
                    data = json.load(f)
                    
                    if "maintenance_rate" in data: st.session_state.pref_maint_rate = float(data["maintenance_rate"])
                    if "purchase_price" in data: st.session_state.pref_purchase_price = float(data["purchase_price"])
                    if "capital_cost_pct" in data: st.session_state.pref_capital_cost_pct = float(data["capital_cost_pct"])
                    if "salvage_value" in data: st.session_state.pref_salvage_value = float(data["salvage_value"])
                    if "useful_life" in data: st.session_state.pref_useful_life = int(data["useful_life"])
                    
                    if "discount_tier" in data:
                        t = str(data["discount_tier"])
                        st.session_state.pref_discount_tier = TIER_EXECUTIVE if "Exec" in t else TIER_PRESIDENTIAL if "Pres" in t or "Chair" in t else TIER_NO_DISCOUNT
                    
                    if "include_maintenance" in data: st.session_state.pref_inc_m = bool(data["include_maintenance"])
                    if "include_capital" in data: st.session_state.pref_inc_c = bool(data["include_capital"])
                    if "include_depreciation" in data: st.session_state.pref_inc_d = bool(data["include_depreciation"])
                    
                    if "renter_rate" in data: st.session_state.renter_rate_val = float(data["renter_rate"])
                    
                    if "renter_discount_tier" in data:
                        t = str(data["renter_discount_tier"])
                        st.session_state.renter_discount_tier = TIER_EXECUTIVE if "Exec" in t else TIER_PRESIDENTIAL if "Pres" in t or "Chair" in t else TIER_NO_DISCOUNT
                    
                    if "preferred_resort_id" in data:
                        st.session_state.preferred_resort_id = str(data["preferred_resort_id"])
                        st.session_state.current_resort_id = str(data["preferred_resort_id"])
                        
                st.toast("Auto-loaded mvc_owner_settings.json", icon="⚙️")
            except Exception as e:
                st.warning(f"Failed to auto-load settings: {e}")
        
        # Mark as loaded so we don't overwrite user changes on next rerun
        st.session_state.profile_auto_loaded = True

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
        raw_r = next(
            (r for r in self._raw.get("resorts", []) if r["display_name"] == resort_name),
            None,
        )
        if not raw_r:
            return None
        years_data: Dict[str, YearData] = {}
        for year_str, y_content in raw_r.get("years", {}).items():
            holidays: List[Holiday] = []
            for h in y_content.get("holidays", []):
                ref = h.get("global_reference")
                if ref and ref in self._global_holidays.get(year_str, {}):
                    g_dates = self._global_holidays[year_str][ref]
                    holidays.append(
                        Holiday(
                            name=h.get("name", ref),
                            start_date=g_dates[0],
                            end_date=g_dates[1],
                            room_points=h.get("room_points", {}),
                        )
                    )
            seasons: List[Season] = []
            for s in y_content.get("seasons", []):
                periods: List[SeasonPeriod] = []
                for p in s.get("periods", []):
                    try:
                        periods.append(
                            SeasonPeriod(
                                start=datetime.strptime(p["start"], "%Y-%m-%d").date(),
                                end=datetime.strptime(p["end"], "%Y-%m-%d").date(),
                            )
                        )
                    except Exception:
                        continue

                day_cats: List[DayCategory] = []
                for cat in s.get("day_categories", {}).values():
                    day_cats.append(
                        DayCategory(
                            days=cat.get("day_pattern", []),
                            room_points=cat.get("room_points", {}),
                        )
                    )
                seasons.append(Season(name=s["name"], periods=periods, day_categories=day_cats))

            years_data[year_str] = YearData(holidays=holidays, seasons=seasons)
        resort_obj = ResortData(
            id=raw_r["id"], name=raw_r["display_name"], years=years_data
        )
        self._resort_cache[resort_name] = resort_obj
        return resort_obj

    def get_resort_info(self, resort_name: str) -> Dict[str, str]:
        raw_r = next(
            (r for r in self._raw.get("resorts", []) if r["display_name"] == resort_name),
            None,
        )
        if raw_r:
            return {
                "full_name": raw_r.get("resort_name", resort_name),
                "timezone": raw_r.get("timezone", "Unknown"),
                "address": raw_r.get("address", "Address not available"),
            }
        return {
            "full_name": resort_name,
            "timezone": "Unknown",
            "address": "Address not available",
        }

# ==============================================================================
# LAYER 3: SERVICE
# ==============================================================================
class MVCCalculator:
    def __init__(self, repo: MVCRepository):
        self.repo = repo

    def _get_daily_points(self, resort: ResortData, day: date) -> Tuple[Dict[str, int], Optional[Holiday]]:
        year_str = str(day.year)
        if year_str not in resort.years:
            return {}, None

        yd = resort.years[year_str]

        # Check Holidays
        for h in yd.holidays:
            if h.start_date <= day <= h.end_date:
                return h.room_points, h

        # Check Seasons
        dow_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
        dow = dow_map[day.weekday()]

        for s in yd.seasons:
            for p in s.periods:
                if p.start <= day <= p.end:
                    for cat in s.day_categories:
                        if dow in cat.days:
                            return cat.room_points, None
        return {}, None

    def calculate_breakdown(
        self, resort_name: str, room: str, checkin: date, nights: int,
        user_mode: UserMode, rate: float, discount_policy: DiscountPolicy = DiscountPolicy.NONE,
        owner_config: Optional[dict] = None,
    ) -> CalculationResult:
        resort = self.repo.get_resort(resort_name)
        if not resort:
            return CalculationResult(pd.DataFrame(), 0, 0.0, False, [])

        if user_mode == UserMode.RENTER:
            rate = round(float(rate), 2)

        rows: List[Dict[str, Any]] = []
        tot_eff_pts = 0
        tot_financial = 0.0
        tot_m = tot_c = tot_d = 0.0
        disc_applied = False
        disc_days: List[str] = []
        is_owner = user_mode == UserMode.OWNER
        processed_holidays: set[str] = set()
        i = 0
        today = datetime.now().date()

        while i < nights:
            d = checkin + timedelta(days=i)
            d_str = d.strftime("%Y-%m-%d")
            day_str = d.strftime("%a")
            
            pts_map, holiday = self._get_daily_points(resort, d)

            if holiday and holiday.name not in processed_holidays:
                processed_holidays.add(holiday.name)
                raw = pts_map.get(room, 0)
                eff = raw
                holiday_days = (holiday.end_date - holiday.start_date).days + 1
                is_disc_holiday = False
                days_out = (holiday.start_date - today).days

                if is_owner:
                    disc_mul = owner_config.get("disc_mul", 1.0) if owner_config else 1.0
                    disc_pct = (1 - disc_mul) * 100
                    thresh = 30 if disc_pct == 25 else 60 if disc_pct == 30 else 0
                    if disc_pct > 0 and days_out <= thresh:
                        eff = math.floor(raw * disc_mul)
                        is_disc_holiday = True
                else:
                    renter_disc_mul = 1.0
                    if discount_policy == DiscountPolicy.PRESIDENTIAL:
                        renter_disc_mul = 0.7
                    elif discount_policy == DiscountPolicy.EXECUTIVE:
                        renter_disc_mul = 0.75
                    if (
                        discount_policy == DiscountPolicy.PRESIDENTIAL and days_out <= 60
                    ) or (
                        discount_policy == DiscountPolicy.EXECUTIVE and days_out <= 30
                    ):
                        eff = math.floor(raw * renter_disc_mul)
                        is_disc_holiday = True

                if is_disc_holiday:
                    disc_applied = True
                    for j in range(holiday_days):
                        disc_date = holiday.start_date + timedelta(days=j)
                        disc_days.append(disc_date.strftime("%Y-%m-%d"))

                holiday_cost = 0.0
                m = c = dp = 0.0
                if is_owner and owner_config:
                    if owner_config.get("inc_m", False):
                        m = math.ceil(round(eff * rate, 8))
                    if owner_config.get("inc_c", False):
                        c = math.ceil(round(eff * owner_config.get("cap_rate", 0.0), 8))
                    if owner_config.get("inc_d", False):
                        dp = math.ceil(round(eff * owner_config.get("dep_rate", 0.0), 8))
                    holiday_cost = m + c + dp
                else:
                    holiday_cost = math.ceil(round(eff * rate, 8))

                row = {
                    "Date": f"{holiday.name} ({holiday.start_date.strftime('%b %d, %Y')} - {holiday.end_date.strftime('%b %d, %Y')})",
                    "Day": "", "Points": eff
                }

                if is_owner:
                    if owner_config and owner_config.get("inc_m", False):
                        row["Maintenance"] = m
                    if owner_config and owner_config.get("inc_c", False):
                        row["Capital Cost"] = c
                    if owner_config and owner_config.get("inc_d", False):
                        row["Depreciation"] = dp
                    row["Total Cost"] = holiday_cost
                else:
                    row[room] = holiday_cost

                rows.append(row)
                tot_eff_pts += eff
                i += holiday_days

            elif not holiday:
                raw = pts_map.get(room, 0)
                eff = raw
                is_disc_day = False
                days_out = (d - today).days

                if is_owner:
                    disc_mul = owner_config.get("disc_mul", 1.0) if owner_config else 1.0
                    disc_pct = (1 - disc_mul) * 100
                    thresh = 30 if disc_pct == 25 else 60 if disc_pct == 30 else 0
                    if disc_pct > 0 and days_out <= thresh:
                        eff = math.floor(raw * disc_mul)
                        is_disc_day = True
                else:
                    renter_disc_mul = 1.0
                    if discount_policy == DiscountPolicy.PRESIDENTIAL:
                        renter_disc_mul = 0.7
                    elif discount_policy == DiscountPolicy.EXECUTIVE:
                        renter_disc_mul = 0.75
                    if (
                        discount_policy == DiscountPolicy.PRESIDENTIAL and days_out <= 60
                    ) or (
                        discount_policy == DiscountPolicy.EXECUTIVE and days_out <= 30
                    ):
                        eff = math.floor(raw * renter_disc_mul)
                        is_disc_day = True

                if is_disc_day:
                    disc_applied = True
                    disc_days.append(d_str)

                day_cost = 0.0
                m = c = dp = 0.0
                if is_owner and owner_config:
                    if owner_config.get("inc_m", False):
                        m = math.ceil(round(eff * rate, 8))
                    if owner_config.get("inc_c", False):
                        c = math.ceil(round(eff * owner_config.get("cap_rate", 0.0), 8))
                    if owner_config.get("inc_d", False):
                        dp = math.ceil(round(eff * owner_config.get("dep_rate", 0.0), 8))
                    day_cost = m + c + dp
                else:
                    day_cost = math.ceil(round(eff * rate, 8))

                row = {"Date": d_str, "Day": day_str, "Points": eff}

                if is_owner:
                    if owner_config and owner_config.get("inc_m", False):
                        row["Maintenance"] = m
                    if owner_config and owner_config.get("inc_c", False):
                        row["Capital Cost"] = c
                    if owner_config and owner_config.get("inc_d", False):
                        row["Depreciation"] = dp
                    row["Total Cost"] = day_cost
                else:
                    row[room] = day_cost
                rows.append(row)
                tot_eff_pts += eff
                i += 1
            else:
                i += 1

        df = pd.DataFrame(rows)

        if user_mode == UserMode.RENTER:
            tot_financial = math.ceil(round(tot_eff_pts * rate, 8))
        elif user_mode == UserMode.OWNER and owner_config:
            raw_maint = math.ceil(round(tot_eff_pts * rate, 8)) if owner_config.get("inc_m", False) else 0.0
            raw_cap = math.ceil(round(tot_eff_pts * owner_config.get("cap_rate", 0.0), 8)) if owner_config.get("inc_c", False) else 0.0
            raw_dep = math.ceil(round(tot_eff_pts * owner_config.get("dep_rate", 0.0), 8)) if owner_config.get("inc_d", False) else 0.0
            
            tot_m = raw_maint
            tot_c = raw_cap
            tot_d = raw_dep
            tot_financial = raw_maint + raw_cap + raw_dep

        if not df.empty:
            fmt_cols = [c for c in df.columns if c not in ["Date", "Day", "Points"]]
            for col in fmt_cols:
                df[col] = df[col].apply(lambda x: f"${x:,.0f}" if isinstance(x, (int, float)) else x)

        return CalculationResult(df, tot_eff_pts, tot_financial, disc_applied, list(set(disc_days)), tot_m, tot_c, tot_d)

    def compare_stays(self, resort_name, rooms, checkin, nights, user_mode, rate, policy, owner_config):
        daily_data = []
        holiday_data = defaultdict(lambda: defaultdict(float))
        val_key = "TotalCostValue" if user_mode == UserMode.OWNER else "RentValue"
        resort = self.repo.get_resort(resort_name)
        if not resort:
            return ComparisonResult(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
        
        processed_holidays = {room: set() for room in rooms}
        disc_mul = owner_config["disc_mul"] if owner_config else 1.0
        renter_mul = 1.0
        if not user_mode == UserMode.OWNER:
            if policy == DiscountPolicy.PRESIDENTIAL: renter_mul = 0.7
            elif policy == DiscountPolicy.EXECUTIVE: renter_mul = 0.75
        
        rate = round(float(rate), 2)
        today = datetime.now().date()

        for room in rooms:
            i = 0
            while i < nights:
                d = checkin + timedelta(days=i)
                pts_map, h = self._get_daily_points(resort, d)
                if h and h.name not in processed_holidays[room]:
                    processed_holidays[room].add(h.name)
                    raw = pts_map.get(room, 0)
                    eff = raw
                    days_out = (h.start_date - today).days

                    if user_mode == UserMode.OWNER:
                        disc_pct = (1 - disc_mul) * 100
                        thresh = 30 if disc_pct == 25 else 60 if disc_pct == 30 else 0
                        if disc_pct > 0 and days_out <= thresh:
                            eff = math.floor(raw * disc_mul)
                    else:
                        r_mul = 1.0
                        if (policy == DiscountPolicy.PRESIDENTIAL and days_out <= 60) or \
                           (policy == DiscountPolicy.EXECUTIVE and days_out <= 30):
                             r_mul = renter_mul
                        if r_mul < 1.0:
                             eff = math.floor(raw * r_mul)

                    cost = 0.0
                    if user_mode == UserMode.OWNER and owner_config:
                         m = math.ceil(round(eff * rate, 8)) if owner_config.get("inc_m") else 0
                         c = math.ceil(round(eff * owner_config.get("cap_rate", 0.0), 8)) if owner_config.get("inc_c") else 0
                         dp = math.ceil(round(eff * owner_config.get("dep_rate", 0.0), 8)) if owner_config.get("inc_d") else 0
                         cost = m + c + dp
                    else:
                         cost = math.ceil(round(eff * rate, 8))
                    
                    holiday_data[room][h.name] += cost
                    i += (h.end_date - h.start_date).days + 1
                elif not h:
                    raw = pts_map.get(room, 0)
                    eff = raw
                    days_out = (d - today).days

                    if user_mode == UserMode.OWNER:
                        disc_pct = (1 - disc_mul) * 100
                        thresh = 30 if disc_pct == 25 else 60 if disc_pct == 30 else 0
                        if disc_pct > 0 and days_out <= thresh:
                             eff = math.floor(raw * disc_mul)
                    else:
                        r_mul = 1.0
                        if (policy == DiscountPolicy.PRESIDENTIAL and days_out <= 60) or \
                           (policy == DiscountPolicy.EXECUTIVE and days_out <= 30):
                             r_mul = renter_mul
                        if r_mul < 1.0:
                             eff = math.floor(raw * r_mul)

                    cost = 0.0
                    if user_mode == UserMode.OWNER and owner_config:
                         m = math.ceil(round(eff * rate, 8)) if owner_config.get("inc_m") else 0
                         c = math.ceil(round(eff * owner_config.get("cap_rate", 0.0), 8)) if owner_config.get("inc_c") else 0
                         dp = math.ceil(round(eff * owner_config.get("dep_rate", 0.0), 8)) if owner_config.get("inc_d") else 0
                         cost = m + c + dp
                    else:
                         cost = math.ceil(round(eff * rate, 8))
                    
                    daily_data.append({
                        "Day": d.strftime("%a"),
                        "Date": d,
                        "Room Type": room,
                        val_key: cost,
                        "Holiday": "No"
                    })
                    i += 1
                else:
                    i += 1

        template_res = self.calculate_breakdown(resort_name, rooms[0], checkin, nights, user_mode, rate, policy, owner_config)
        final_pivot = []
        for _, tmpl_row in template_res.breakdown_df.iterrows():
            d_str = tmpl_row["Date"]
            new_row = {"Date": d_str}
            for room in rooms:
                val = 0.0
                if "(" in str(d_str):
                    h_name = str(d_str).split(" (")[0]
                    val = holiday_data[room].get(h_name, 0.0)
                else:
                    try:
                        d_obj = datetime.strptime(str(d_str), "%Y-%m-%d").date()
                        val = next((x[val_key] for x in daily_data if x["Date"] == d_obj and x["Room Type"] == room), 0.0)
                    except: pass
                new_row[room] = f"${val:,.0f}"
            final_pivot.append(new_row)

        tot_row = {"Date": "Total Cost" if user_mode == UserMode.OWNER else "Total Rent"}
        for r in rooms:
            room_res = self.calculate_breakdown(
                resort_name, r, checkin, nights, user_mode, rate, policy, owner_config
            )
            tot_row[r] = f"${room_res.financial_total:,.0f}"
        final_pivot.append(tot_row)
        
        h_chart_rows = []
        for r, h_map in holiday_data.items():
            for h_name, val in h_map.items():
                h_chart_rows.append({"Holiday": h_name, "Room Type": r, val_key: val})

        return ComparisonResult(pd.DataFrame(final_pivot), pd.DataFrame(daily_data), pd.DataFrame(h_chart_rows))

    def adjust_holiday(self, resort_name, checkin, nights):
        resort = self.repo.get_resort(resort_name)
        if not resort or str(checkin.year) not in resort.years:
            return checkin, nights, False

        end = checkin + timedelta(days=nights - 1)
        yd = resort.years[str(checkin.year)]
        overlapping = [h for h in yd.holidays if h.start_date <= end and h.end_date >= checkin]

        if not overlapping:
            return checkin, nights, False
        s = min(h.start_date for h in overlapping)
        e = max(h.end_date for h in overlapping)
        adj_s = min(checkin, s)
        adj_e = max(end, e)
        return adj_s, (adj_e - adj_s).days + 1, True

# ==============================================================================
# HELPER: SEASON COST TABLE
# ==============================================================================
def get_all_room_types_for_resort(resort_data: ResortData) -> List[str]:
    rooms = set()
    for year_obj in resort_data.years.values():
        for season in year_obj.seasons:
            for cat in season.day_categories:
                rooms.update(cat.room_points.keys())
        for holiday in year_obj.holidays:
            rooms.update(holiday.room_points.keys())
    return sorted(rooms)

def build_rental_cost_table(
    resort_data: ResortData,
    year: int,
    rate: float,
    discount_mul: float,
    mode: UserMode,
    owner_params: Optional[dict] = None
) -> Optional[pd.DataFrame]:
    yd = resort_data.years.get(str(year))
    if not yd:
        return None

    room_types = get_all_room_types_for_resort(resort_data)
    if not room_types:
        return None

    rows = []

    # Seasons
    for season in yd.seasons:
        name = season.name.strip() or "Unnamed Season"
        weekly = {}
        has_data = False

        for dow in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            for cat in season.day_categories:
                if dow in cat.days:
                    rp = cat.room_points
                    for room in room_types:
                        pts = rp.get(room, 0)
                        if pts:
                            has_data = True
                        weekly[room] = weekly.get(room, 0) + pts
                    break

        if has_data:
            row = {"Season": name}
            for room in room_types:
                raw_pts = weekly.get(room, 0)
                eff_pts = math.floor(raw_pts * discount_mul) if discount_mul < 1 else raw_pts
                if mode == UserMode.RENTER:
                    cost = math.ceil(eff_pts * rate)
                else:
                    m = math.ceil(eff_pts * rate) if owner_params.get("inc_m", False) else 0
                    c = math.ceil(eff_pts * owner_params.get("cap_rate", 0.0)) if owner_params.get("inc_c", False) else 0
                    d = math.ceil(eff_pts * owner_params.get("dep_rate", 0.0)) if owner_params.get("inc_d", False) else 0
                    cost = m + c + d
                row[room] = f"${cost:,}"
            rows.append(row)

    # Holidays
    for h in yd.holidays:
        name = h.name.strip() or "Holiday"
        rp = h.room_points
        row = {"Season": f"Holiday – {name}"}
        for room in room_types:
            raw = rp.get(room, 0)
            if not raw:
                row[room] = "—"
                continue
            eff = math.floor(raw * discount_mul) if discount_mul < 1 else raw
            if mode == UserMode.RENTER:
                cost = math.ceil(eff * rate)
            else:
                m = math.ceil(eff * rate) if owner_params.get("inc_m", False) else 0
                c = math.ceil(eff * owner_params.get("cap_rate", 0.0)) if owner_params.get("inc_c", False) else 0
                d = math.ceil(eff * owner_params.get("dep_rate", 0.0)) if owner_params.get("inc_d", False) else 0
                cost = m + c + d
            row[room] = f"${cost:,}"
        rows.append(row)

    return pd.DataFrame(rows, columns=["Season"] + room_types) if rows else None

# ==============================================================================
# UI HELPERS
# ==============================================================================
def render_metrics_grid(result: CalculationResult, mode: UserMode, owner_params: Optional[dict], policy: DiscountPolicy) -> None:
    owner_params = owner_params or {}
    if mode == UserMode.OWNER:
        num_components = sum([owner_params.get("inc_m", False), owner_params.get("inc_c", False), owner_params.get("inc_d", False)])
        cols = st.columns(2 + max(num_components, 0))
        with cols[0]:
            st.metric(label="📊 Total Points", value=f"{result.total_points:,}")
        with cols[1]:
            st.metric(label="💰 Total Cost", value=f"${result.financial_total:,.0f}")
        col_idx = 2
        if owner_params.get("inc_m"):
            with cols[col_idx]: st.metric(label="🔧 Maintenance", value=f"${result.m_cost:,.0f}")
            col_idx += 1
        if owner_params.get("inc_c"):
            with cols[col_idx]: st.metric(label="💼 Capital Cost", value=f"${result.c_cost:,.0f}")
            col_idx += 1
        if owner_params.get("inc_d"):
            with cols[col_idx]: st.metric(label="📉 Depreciation", value=f"${result.d_cost:,.0f}")
            col_idx += 1
    else:
        if result.discount_applied:
            cols = st.columns(3)
            pct = "30%" if policy == DiscountPolicy.PRESIDENTIAL else "25%"
            with cols[0]: st.metric(label="📊 Total Points", value=f"{result.total_points:,}")
            with cols[1]: st.metric(label="💰 Total Rent", value=f"${result.financial_total:,.0f}")
            with cols[2]: st.metric(label="🎉 Membership Tier", value=pct, delta=f"{len(result.discounted_days)} days")
        else:
            cols = st.columns(2)
            with cols[0]: st.metric(label="📊 Total Points", value=f"{result.total_points:,}")
            with cols[1]: st.metric(label="💰 Total Rent", value=f"${result.financial_total:,.0f}")

# ==============================================================================
# MAIN PAGE LOGIC
# ==============================================================================
def get_tier_index(tier_string: str) -> int:
    """Map JSON string (Short or Long) to UI Radio index."""
    s = str(tier_string).lower()
    if "presidential" in s or "chairman" in s:
        return 2
    if "executive" in s:
        return 1
    return 0

def get_short_tier_name(tier_string: str) -> str:
    """Map UI Radio string back to short JSON value."""
    s = str(tier_string).lower()
    if "presidential" in s or "chairman" in s:
        return "Presidential"
    if "executive" in s:
        return "Executive"
    return "Ordinary"

def main(forced_mode: str = "Renter") -> None:
    # --- 1. INITIALIZE SESSION STATE ---
    initialize_state()

    ensure_data_in_session()
    if not st.session_state.data:
        st.warning("Please open the Editor and upload/merge data_v2.json first.")
        return

    repo = MVCRepository(st.session_state.data)
    calc = MVCCalculator(repo)
    resorts_full = repo.get_resort_list_full()

    # --- SAFETY CHECK FOR PREFERRED RESORT ---
    if "current_resort_id" not in st.session_state or not st.session_state.current_resort_id:
        preferred_id = st.session_state.get("preferred_resort_id")
        if preferred_id and any(r["id"] == preferred_id for r in resorts_full):
            st.session_state.current_resort_id = preferred_id
        elif resorts_full:
            st.session_state.current_resort_id = resorts_full[0].get("id")

    mode = UserMode(forced_mode)
    render_page_header(title="Calculator", subtitle=f"{mode.value}", icon="🏨", badge_color="#059669" if mode == UserMode.OWNER else "#2563eb")

    # SETTINGS EXPANDER
    with st.expander("⚙️ Settings", expanded=False):
        owner_params = None
        policy = DiscountPolicy.NONE
        active_rate = 0.0
        disc_mul = 1.0

        if mode == UserMode.OWNER:
            st.markdown("#### Ownership Parameters")
            c1, c2 = st.columns(2)
            with c1:
                maint_rate = st.number_input("Maintenance per Point ($)", value=st.session_state.pref_maint_rate, step=0.01, key="owner_maint")
                st.session_state.pref_maint_rate = maint_rate
                active_rate = maint_rate
            with c2:
                tier = st.radio("Membership Tier", ["Ordinary", "Executive", "Presidential"],
                                index=get_tier_index(st.session_state.pref_discount_tier),
                                key="owner_tier")
                st.session_state.pref_discount_tier = tier

            chk1, chk2, chk3 = st.columns(3)
            with chk1: inc_m = st.checkbox("Include Maintenance", value=st.session_state.pref_inc_m, key="owner_inc_m"); st.session_state.pref_inc_m = inc_m
            with chk2: inc_c = st.checkbox("Include Capital Cost", value=st.session_state.pref_inc_c, key="owner_inc_c"); st.session_state.pref_inc_c = inc_c
            with chk3: inc_d = st.checkbox("Include Depreciation", value=st.session_state.pref_inc_d, key="owner_inc_d"); st.session_state.pref_inc_d = inc_d

            cap_rate = dep_rate = 0.0
            purchase = st.session_state.pref_purchase_price
            coc_pct = st.session_state.pref_capital_cost_pct
            life = st.session_state.pref_useful_life
            salvage = st.session_state.pref_salvage_value

            if inc_c or inc_d:
                st.markdown("---")
                rc1, rc2, rc3, rc4 = st.columns(4)
                with rc1: purchase = st.number_input("Purchase Price ($/pt)", value=st.session_state.pref_purchase_price, key="owner_purchase"); st.session_state.pref_purchase_price = purchase
                with rc2: 
                    if inc_c: coc_pct = st.number_input("Cost of Capital (%)", value=st.session_state.pref_capital_cost_pct, key="owner_coc"); st.session_state.pref_capital_cost_pct = coc_pct
                with rc3: 
                    if inc_d: life = st.number_input("Useful Life (yrs)", value=st.session_state.pref_useful_life, min_value=1, key="owner_life"); st.session_state.pref_useful_life = life
                with rc4: 
                    if inc_d: salvage = st.number_input("Salvage ($/pt)", value=st.session_state.pref_salvage_value, key="owner_salvage"); st.session_state.pref_salvage_value = salvage
                
            if inc_c: cap_rate = purchase * (coc_pct / 100.0)
            if inc_d: dep_rate = (purchase - salvage) / life if life > 0 else 0.0

            disc_mul = 0.75 if "Executive" in tier else 0.7 if "Presidential" in tier else 1.0
            owner_params = {"disc_mul": disc_mul, "inc_m": inc_m, "inc_c": inc_c, "inc_d": inc_d, "cap_rate": cap_rate, "dep_rate": dep_rate}

        else:
            st.markdown("#### Rental Parameters")
            c1, c2 = st.columns(2)
            with c1:
                renter_rate = st.number_input("Rent per Point ($)", value=st.session_state.renter_rate_val, step=0.01, key="renter_rate")
                st.session_state.renter_rate_val = renter_rate
                active_rate = renter_rate
            with c2:
                tier = st.radio("Membership Tier", ["Ordinary", "Executive", "Presidential"],
                                index=get_tier_index(st.session_state.renter_discount_tier),
                                key="renter_tier")
                st.session_state.renter_discount_tier = tier

            if "Presidential" in tier: policy = DiscountPolicy.PRESIDENTIAL; disc_mul = 0.7
            elif "Executive" in tier: policy = DiscountPolicy.EXECUTIVE; disc_mul = 0.75

        # SAVE / LOAD PROFILE
        st.markdown("---")
        col_load, col_save = st.columns([3, 1])
        with col_load:
            uploaded = st.file_uploader("Load Profile", type="json", key="profile_upload")
            if uploaded:
                try:
                    data = json.load(uploaded)
                    # Manually update session keys
                    if "maintenance_rate" in data: st.session_state.pref_maint_rate = float(data["maintenance_rate"])
                    if "purchase_price" in data: st.session_state.pref_purchase_price = float(data["purchase_price"])
                    if "capital_cost_pct" in data: st.session_state.pref_capital_cost_pct = float(data["capital_cost_pct"])
                    if "salvage_value" in data: st.session_state.pref_salvage_value = float(data["salvage_value"])
                    if "useful_life" in data: st.session_state.pref_useful_life = int(data["useful_life"])
                    if "discount_tier" in data: st.session_state.pref_discount_tier = str(data["discount_tier"])
                    if "include_maintenance" in data: st.session_state.pref_inc_m = bool(data["include_maintenance"])
                    if "include_capital" in data: st.session_state.pref_inc_c = bool(data["include_capital"])
                    if "include_depreciation" in data: st.session_state.pref_inc_d = bool(data["include_depreciation"])
                    if "renter_rate" in data: st.session_state.renter_rate_val = float(data["renter_rate"])
                    if "renter_discount_tier" in data: st.session_state.renter_discount_tier = str(data["renter_discount_tier"])
                    if "preferred_resort_id" in data: st.session_state.preferred_resort_id = str(data["preferred_resort_id"])
                    st.success("Profile loaded!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Invalid file: {e}")

        with col_save:
            config = {
                "maintenance_rate": round(st.session_state.pref_maint_rate, 2),
                "purchase_price": st.session_state.pref_purchase_price,
                "capital_cost_pct": st.session_state.pref_capital_cost_pct,
                "salvage_value": st.session_state.pref_salvage_value,
                "useful_life": st.session_state.pref_useful_life,
                "discount_tier": get_short_tier_name(st.session_state.pref_discount_tier),
                "include_maintenance": st.session_state.pref_inc_m,
                "include_capital": st.session_state.pref_inc_c,
                "include_depreciation": st.session_state.pref_inc_d,
                "renter_rate": round(st.session_state.renter_rate_val, 2),
                "renter_discount_tier": get_short_tier_name(st.session_state.renter_discount_tier),
                "preferred_resort_id": st.session_state.current_resort_id or ""
            }
            st.download_button("💾 Save Profile", data=json.dumps(config, indent=2), file_name="mvc_owner_settings.json", mime="application/json", use_container_width=True)

    # RESORT GRID
    render_resort_grid(resorts_full, st.session_state.current_resort_id)
    resort_obj = next((r for r in resorts_full if r.get("id") == st.session_state.current_resort_id), None)
    if not resort_obj: return
    r_name = resort_obj.get("display_name")
    info = repo.get_resort_info(r_name)
    render_resort_card(info["full_name"], info["timezone"], info["address"])
    st.divider()

    # INPUTS
    c1, c2, c3, c4 = st.columns([2, 1, 2, 2])
    with c1:
        checkin = st.date_input("Check-in", value=st.session_state.calc_checkin, key="calc_checkin_widget")
        st.session_state.calc_checkin = checkin
    if not st.session_state.calc_checkin_user_set and checkin != st.session_state.calc_initial_default:
        st.session_state.calc_checkin_user_set = True
    with c2: nights = st.number_input("Nights", 1, 60, 7)
    
    if st.session_state.calc_checkin_user_set:
        adj_in, adj_n, adj = calc.adjust_holiday(r_name, checkin, nights)
    else:
        adj_in, adj_n, adj = checkin, nights, False
    
    if adj:
        st.info(f"Adjusted to holiday: {adj_in.strftime('%b %d')} - {(adj_in+timedelta(days=adj_n-1)).strftime('%b %d')}")
    
    pts, _ = calc._get_daily_points(calc.repo.get_resort(r_name), adj_in)
    if not pts:
        rd = calc.repo.get_resort(r_name)
        if rd and str(adj_in.year) in rd.years:
             yd = rd.years[str(adj_in.year)]
             if yd.seasons: pts = yd.seasons[0].day_categories[0].room_points

    room_types = sorted(pts.keys()) if pts else []
    if not room_types:
        st.error("No room data available.")
        return

    with c3: room_sel = st.selectbox("Room Type", room_types)
    with c4: comp_rooms = st.multiselect("Compare With", [r for r in room_types if r != room_sel])
    st.divider()

    # RESULTS
    discount_display = "None"
    if disc_mul < 1.0:
        pct = int((1.0 - disc_mul) * 100)
        policy_label = "Executive" if disc_mul == 0.75 else "Presidential" if disc_mul == 0.7 else "Custom"
        discount_display = f"✅ {pct}% Off ({policy_label})"
    
    rate_label = "Maintenance Fee Rate" if mode == UserMode.OWNER else "Rental Rate"
    st.caption(f"ℹ️ **Calculation Basis:** {rate_label}: **${active_rate:.2f}/pt** • Discount Setting: **{discount_display}**")

    res = calc.calculate_breakdown(r_name, room_sel, adj_in, adj_n, mode, active_rate, policy, owner_params)
    render_metrics_grid(res, mode, owner_params, policy)

    if res.discount_applied and mode == UserMode.RENTER:
        pct = "30%" if policy == DiscountPolicy.PRESIDENTIAL else "25%"
        st.success(f"🎉 **Tier Benefit Applied!** {pct} off points for {len(res.discounted_days)} day(s).")
    
    st.divider()

    # EXPANDER 1: Daily Breakdown (Collapsed by default, Download inside)
    with st.expander("📋 Daily Breakdown", expanded=False):
        st.dataframe(res.breakdown_df, use_container_width=True, hide_index=True)
        csv_data = res.breakdown_df.to_csv(index=False)
        st.download_button("⬇️ Download CSV", csv_data, f"{r_name}_{room_sel}_{'rental' if mode == UserMode.RENTER else 'cost'}.csv", mime="text/csv", use_container_width=True)

    # EXPANDER 2: All Room Types
    with st.expander("All Room Types – This Stay", expanded=False):
        comp_data = []
        all_room_types = get_all_room_types_for_resort(calc.repo.get_resort(r_name))
        for rm in all_room_types:
            room_res = calc.calculate_breakdown(r_name, rm, adj_in, adj_n, mode, active_rate, policy, owner_params)
            cost_label = "Rent" if mode == UserMode.RENTER else "Cost"
            comp_data.append({"Room Type": rm, "Points": f"{room_res.total_points:,}", "Cost": f"${room_res.financial_total:,.0f}"})
        st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

    if comp_rooms:
        st.divider()
        st.markdown("### Comparison")
        comp_res = calc.compare_stays(r_name, [room_sel] + comp_rooms, adj_in, adj_n, mode, active_rate, policy, owner_params)
        st.dataframe(comp_res.pivot_df, use_container_width=True)
        c1, c2 = st.columns(2)
        if not comp_res.daily_chart_df.empty:
             with c1: st.plotly_chart(px.bar(comp_res.daily_chart_df, x="Day", y="TotalCostValue" if mode==UserMode.OWNER else "RentValue", color="Room Type", barmode="group", title="Daily Cost"), use_container_width=True)
        if not comp_res.holiday_chart_df.empty:
             with c2: st.plotly_chart(px.bar(comp_res.holiday_chart_df, x="Holiday", y="TotalCostValue" if mode==UserMode.OWNER else "RentValue", color="Room Type", barmode="group", title="Holiday Cost"), use_container_width=True)

    year_str = str(adj_in.year)
    res_data = calc.repo.get_resort(r_name)
    if res_data and year_str in res_data.years:
        st.divider()
        with st.expander("📅 Season and Holiday Calendar", expanded=False):
            gantt_fig = create_gantt_chart_from_resort_data(res_data, year_str, st.session_state.data.get("global_holidays", {}), height=500)
            st.plotly_chart(gantt_fig, use_container_width=True)
            cost_df = build_rental_cost_table(res_data, int(year_str), active_rate, disc_mul, mode, owner_params)
            if cost_df is not None:
                title = "7-Night Rental Costs" if mode == UserMode.RENTER else "7-Night Ownership Costs"
                note = " — Tier benefit applied" if disc_mul < 1 else ""
                st.markdown(f"**{title}** @ ${active_rate:.2f}/pt{note}")
                st.dataframe(cost_df, use_container_width=True, hide_index=True)
            else:
                st.info("No season or holiday pricing data available for this year.")

    # --- Bottom of Owner Mode: Access to Editor ---
    if mode == UserMode.OWNER:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.divider()
        col_e1, col_e2 = st.columns([4, 1])
        with col_e2:
            if st.button("🔧 Open Resort Editor", use_container_width=True):
                st.session_state.app_phase = "editor"
                st.rerun()

def run(forced_mode: str = "Renter") -> None:
    main(forced_mode)
