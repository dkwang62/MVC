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
# LAYER 0: SETTINGS LOADER & HELPERS
# ==============================================================================
def load_default_settings() -> Dict[str, Any]:
    """Load defaults from mvc_owner_settings.json if it exists."""
    settings_path = "mvc_owner_settings.json"
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def apply_settings_from_dict(data: Dict[str, Any]):
    """
    Update session state variables directly from a dictionary.
    """
    if not data:
        return

    # Helper to safely set state
    def safe_set(key, val):
        st.session_state[key] = val

    # Owner Params
    if "maintenance_rate" in data:
        safe_set("owner_maint_rate", float(data["maintenance_rate"]))
    if "purchase_price" in data:
        safe_set("owner_price", float(data["purchase_price"]))
    if "capital_cost_pct" in data:
        safe_set("owner_coc_pct", float(data["capital_cost_pct"]))
    if "salvage_value" in data:
        safe_set("owner_salvage", float(data["salvage_value"]))
    if "useful_life" in data:
        safe_set("owner_life", int(data["useful_life"]))
    
    # Tier String
    if "discount_tier" in data:
        val = data["discount_tier"]
        if val not in TIER_OPTIONS: val = TIER_OPTIONS[0]
        safe_set("owner_tier_sel", val)
    
    # Owner Checkboxes
    if "include_maintenance" in data:
        safe_set("owner_inc_m", bool(data["include_maintenance"]))
    if "include_capital" in data:
        safe_set("owner_inc_c", bool(data["include_capital"]))
    if "include_depreciation" in data:
        safe_set("owner_inc_d", bool(data["include_depreciation"]))

    # Renter Params
    if "renter_rate" in data:
        safe_set("renter_price", float(data["renter_rate"]))
    if "renter_discount_tier" in data:
        val = data["renter_discount_tier"]
        if val not in TIER_OPTIONS: val = TIER_OPTIONS[0]
        safe_set("renter_tier_sel", val)

    # Preferred Resort
    if "preferred_resort_id" in data:
        safe_set("current_resort_id", data["preferred_resort_id"])

def initialize_session_variables(defaults: Dict[str, Any], force_reset: bool = False):
    """
    Ensure all widget keys exist in session state. 
    This runs ONCE at startup (or on force reset) to populate the state 
    before widgets are rendered.
    """
    
    # Helper to initialize a key if missing
    def init_key(key, default_val):
        if force_reset or key not in st.session_state:
            st.session_state[key] = default_val

    # 1. Owner Defaults
    init_key("owner_maint_rate", float(defaults.get("maintenance_rate", 0.83)))
    
    raw_tier = defaults.get("discount_tier", "Ordinary Level")
    if raw_tier not in TIER_OPTIONS: raw_tier = TIER_OPTIONS[0]
    init_key("owner_tier_sel", raw_tier)
    
    init_key("owner_price", float(defaults.get("purchase_price", 3.5)))
    init_key("owner_coc_pct", float(defaults.get("capital_cost_pct", 5.0)))
    init_key("owner_life", int(defaults.get("useful_life", 20)))
    init_key("owner_salvage", float(defaults.get("salvage_value", 3.0)))
    
    # Checkboxes
    init_key("owner_inc_m", bool(defaults.get("include_maintenance", True)))
    init_key("owner_inc_c", bool(defaults.get("include_capital", True)))
    init_key("owner_inc_d", bool(defaults.get("include_depreciation", False)))

    # 2. Renter Defaults
    init_key("renter_price", float(defaults.get("renter_rate", 0.83)))
    
    raw_renter = defaults.get("renter_discount_tier", "Ordinary Level")
    if raw_renter not in TIER_OPTIONS: raw_renter = TIER_OPTIONS[0]
    init_key("renter_tier_sel", raw_renter)

    # 3. Resort Preference (Only set if not already navigating)
    if "current_resort_id" not in st.session_state:
        st.session_state.current_resort_id = defaults.get("preferred_resort_id", None)

# ==============================================================================
# LAYER 1: DOMAIN MODELS (Type-Safe Data Structures)
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
# LAYER 2: REPOSITORY (Data Access Layer)
# ==============================================================================
class MVCRepository:
    def __init__(self, raw_data: dict):
        self._raw = raw_data
        self._resort_cache: Dict[str, ResortData] = {}
        self._global_holidays = self._parse_global_holidays()

    def get_resort_list(self) -> List[str]:
        return sorted([r["display_name"] for r in self._raw.get("resorts", [])])

    def get_resort_list_full(self) -> List[Dict[str, Any]]:
        """Return raw resort dictionaries (used for grid rendering)."""
        return self._raw.get("resorts", [])

    def _parse_global_holidays(
        self,
    ) -> Dict[str, Dict[str, Tuple[date, date]]]:
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
        """Get additional resort information for card display."""
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
# LAYER 3: SERVICE (Pure Business Logic Engine)
# ==============================================================================
class MVCCalculator:
    def __init__(self, repo: MVCRepository):
        self.repo = repo

    def _get_daily_points(
        self,
        resort: ResortData,
        day: date
    ) -> Tuple[Dict[str, int], Optional[Holiday]]:
        year_str = str(day.year)
        if year_str not in resort.years:
            return {}, None
        yd = resort.years[year_str]
        # Check holiday first
        for h in yd.holidays:
            if h.start_date <= day <= h.end_date:
                return h.room_points, h
        # Then regular seasons
        dow_map = {
            0: "Mon",
            1: "Tue",
            2: "Wed",
            3: "Thu",
            4: "Fri",
            5: "Sat",
            6: "Sun",
        }
        dow = dow_map[day.weekday()]
        for s in yd.seasons:
            for p in s.periods:
                if p.start <= day <= p.end:
                    for cat in s.day_categories:
                        if dow in cat.days:
                            return cat.room_points, None
        return {}, None

    def calculate_breakdown(
        self,
        resort_name: str,
        room: str,
        checkin: date,
        nights: int,
        user_mode: UserMode,
        rate: float,
        discount_policy: DiscountPolicy = DiscountPolicy.NONE,
        owner_config: Optional[dict] = None,
    ) -> CalculationResult:
        resort = self.repo.get_resort(resort_name)
        if not resort:
            return CalculationResult(
                breakdown_df=pd.DataFrame(),
                total_points=0,
                financial_total=0.0,
                discount_applied=False,
                discounted_days=[],
            )

        # --- SNAP RENTER RATE TO 2DP ---
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

            # ==============================
            # HOLIDAY BLOCK (once per period)
            # ==============================
            if holiday and holiday.name not in processed_holidays:
                processed_holidays.add(holiday.name)
                raw = pts_map.get(room, 0)
                eff = raw
                holiday_days = (holiday.end_date - holiday.start_date).days + 1
                is_disc_holiday = False
                days_out = (holiday.start_date - today).days

                # --- Discount Logic ---
                if is_owner:
                    disc_mul = owner_config.get("disc_mul", 1.0)
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

                # Cost computation with Float Precision Fix (round to 8dp before ceil)
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

                row: Dict[str, Any] = {
                    "Date": f"{holiday.name} ({holiday.start_date.strftime('%b %d, %Y')} - "
                            f"{holiday.end_date.strftime('%b %d, %Y')})",
                    "Day": "",
                    "Points": eff,
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

            # ==================
            # REGULAR DAY
            # ==================
            elif not holiday:
                raw = pts_map.get(room, 0)
                eff = raw
                is_disc_day = False
                days_out = (d - today).days

                # --- Discount Logic ---
                if is_owner:
                    disc_mul = owner_config.get("disc_mul", 1.0)
                    disc_pct = (1 - disc_mul) * 100
                    thresh = 30 if disc_pct == 25 else 60 if disc_pct == 30 else 0
                    if disc_pct > 0 and days_out <= thresh:
                        eff = math.floor(raw * disc_mul)
                    else:
                        eff = raw
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

                # Cost computation with Float Precision Fix
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

                row = {
                    "Date": d_str,
                    "Day": day_str,
                    "Points": eff,
                }
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

        # ============================================================
        # PRIORITY RULE (ROUND OF SUMS) with FLOAT FIX:
        # We round the product to 8 decimals before Ceiling to handle floating point errors
        # e.g. 8300 * 0.81 = 6723.0000000001 -> ceil would be 6724. 
        # Rounding fixes it to 6723.0 -> ceil is 6723.
        # ============================================================
        if user_mode == UserMode.RENTER:
            tot_financial = math.ceil(round(tot_eff_pts * rate, 8))
            tot_m = tot_c = tot_d = 0.0
        elif user_mode == UserMode.OWNER and owner_config:
            maint_total = math.ceil(round(tot_eff_pts * rate, 8)) if owner_config.get("inc_m", False) else 0.0
            
            cap_total = 0.0
            if owner_config.get("inc_c", False):
                cap_total = math.ceil(round(tot_eff_pts * owner_config.get("cap_rate", 0.0), 8))
                
            dep_total = 0.0
            if owner_config.get("inc_d", False):
                dep_total = math.ceil(round(tot_eff_pts * owner_config.get("dep_rate", 0.0), 8))

            tot_m = maint_total
            tot_c = cap_total
            tot_d = dep_total
            tot_financial = maint_total + cap_total + dep_total
        # ============================================================

        # Format currency columns
        if is_owner and not df.empty:
            for col in ["Maintenance", "Capital Cost", "Depreciation", "Total Cost"]:
                if col in df.columns:
                    df[col] = df[col].apply(
                        lambda x: f"${x:,.0f}" if isinstance(x, (int, float)) else x
                    )
        else:
            for col in df.columns:
                if col not in ["Date", "Day", "Points"]:
                    df[col] = df[col].apply(
                        lambda x: f"${x:,.0f}" if isinstance(x, (int, float)) else x
                    )

        return CalculationResult(
            breakdown_df=df,
            total_points=tot_eff_pts,
            financial_total=tot_financial,
            discount_applied=disc_applied,
            discounted_days=list(set(disc_days)),
            m_cost=tot_m,
            c_cost=tot_c,
            d_cost=tot_d,
        )

    def compare_stays(
        self,
        resort_name: str,
        rooms: List[str],
        checkin: date,
        nights: int,
        user_mode: UserMode,
        rate: float,
        policy: DiscountPolicy,
        owner_config: Optional[dict],
    ) -> ComparisonResult:
        daily_data: List[Dict[str, Any]] = []
        holiday_data: Dict[str, Dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )

        is_owner = user_mode == UserMode.OWNER
        if user_mode == UserMode.RENTER:
            rate = round(float(rate), 2)

        disc_mul = owner_config["disc_mul"] if owner_config else 1.0
        renter_mul = 1.0
        if not is_owner:
            if policy == DiscountPolicy.PRESIDENTIAL:
                renter_mul = 0.7
            elif policy == DiscountPolicy.EXECUTIVE:
                renter_mul = 0.75

        val_key = "TotalCostValue" if is_owner else "RentValue"
        resort = self.repo.get_resort(resort_name)
        if not resort:
            return ComparisonResult(
                pivot_df=pd.DataFrame(),
                daily_chart_df=pd.DataFrame(),
                holiday_chart_df=pd.DataFrame(),
            )

        processed_holidays: Dict[str, set[str]] = {room: set() for room in rooms}
        today = datetime.now().date()
        total_pts_by_room: Dict[str, int] = defaultdict(int)

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

                    if is_owner:
                        disc_pct = (1 - disc_mul) * 100
                        thresh = 30 if disc_pct == 25 else 60 if disc_pct == 30 else 0
                        if disc_pct > 0 and days_out <= thresh:
                            eff = math.floor(raw * disc_mul)
                    else:
                        if (
                            policy == DiscountPolicy.PRESIDENTIAL and days_out <= 60
                        ) or (
                            policy == DiscountPolicy.EXECUTIVE and days_out <= 30
                        ):
                            eff = math.floor(raw * renter_mul)

                    total_pts_by_room[room] += eff

                    # Daily/Block calc with float fix
                    if is_owner:
                        m = c = dp = 0.0
                        if owner_config and owner_config.get("inc_m", False):
                            m = math.ceil(round(eff * rate, 8))
                        if owner_config and owner_config.get("inc_c", False):
                            c = math.ceil(round(eff * owner_config.get("cap_rate", 0.0), 8))
                        if owner_config and owner_config.get("inc_d", False):
                            dp = math.ceil(round(eff * owner_config.get("dep_rate", 0.0), 8))
                        cost = m + c + dp
                    else:
                        cost = math.ceil(round(eff * rate, 8))

                    holiday_data[room][h.name] += cost
                    holiday_days = (h.end_date - h.start_date).days + 1
                    i += holiday_days

                elif not h:
                    raw = pts_map.get(room, 0)
                    eff = raw
                    days_out = (d - today).days

                    if is_owner:
                        disc_pct = (1 - disc_mul) * 100
                        thresh = 30 if disc_pct == 25 else 60 if disc_pct == 30 else 0
                        if disc_pct > 0 and days_out <= thresh:
                            eff = math.floor(raw * disc_mul)
                        else:
                            eff = raw
                    else:
                        if (
                            policy == DiscountPolicy.PRESIDENTIAL and days_out <= 60
                        ) or (
                            policy == DiscountPolicy.EXECUTIVE and days_out <= 30
                        ):
                            eff = math.floor(raw * renter_mul)

                    total_pts_by_room[room] += eff

                    if is_owner:
                        m = c = dp = 0.0
                        if owner_config and owner_config.get("inc_m", False):
                            m = math.ceil(round(eff * rate, 8))
                        if owner_config and owner_config.get("inc_c", False):
                            c = math.ceil(round(eff * owner_config.get("cap_rate", 0.0), 8))
                        if owner_config and owner_config.get("inc_d", False):
                            dp = math.ceil(round(eff * owner_config.get("dep_rate", 0.0), 8))
                        cost = m + c + dp
                    else:
                        cost = math.ceil(round(eff * rate, 8))

                    daily_data.append(
                        {
                            "Day": d.strftime("%a"),
                            "Date": d,
                            "Room Type": room,
                            val_key: cost,
                            "Holiday": "No",
                        }
                    )
                    i += 1
                else:
                    i += 1

        template_res = self.calculate_breakdown(
            resort_name,
            rooms[0],
            checkin,
            nights,
            user_mode,
            rate,
            policy,
            owner_config,
        )
        pivot_rows: List[Dict[str, Any]] = []
        for _, tmpl_row in template_res.breakdown_df.iterrows():
            new_row: Dict[str, Any] = {"Date": tmpl_row["Date"]}
            for room in rooms:
                if "(" in str(tmpl_row["Date"]):
                    h_name = str(tmpl_row["Date"]).split(" (")[0]
                    val = holiday_data[room].get(h_name, 0.0)
                else:
                    try:
                        d_obj = datetime.strptime(
                            str(tmpl_row["Date"]), "%Y-%m-%d"
                        ).date()
                    except Exception:
                        d_obj = None
                    if d_obj is not None:
                        val = next(
                            (
                                x[val_key]
                                for x in daily_data
                                if x["Date"] == d_obj and x["Room Type"] == room
                            ),
                            0.0,
                        )
                    else:
                        val = 0.0
                new_row[room] = f"${val:,.0f}"
            pivot_rows.append(new_row)

        # TOTAL ROW with float fix
        total_label = "Total Cost" if is_owner else "Total Rent"
        tot_row: Dict[str, Any] = {"Date": total_label}
        for r in rooms:
            pts = total_pts_by_room[r]
            if is_owner and owner_config:
                maint_total = (
                    math.ceil(round(pts * rate, 8)) if owner_config.get("inc_m", False) else 0.0
                )
                cap_total = (
                    math.ceil(round(pts * owner_config.get("cap_rate", 0.0), 8))
                    if owner_config.get("inc_c", False)
                    else 0.0
                )
                dep_total = (
                    math.ceil(round(pts * owner_config.get("dep_rate", 0.0), 8))
                    if owner_config.get("inc_d", False)
                    else 0.0
                )
                tot_sum = maint_total + cap_total + dep_total
            else:
                tot_sum = math.ceil(round(pts * rate, 8))

            tot_row[r] = f"${tot_sum:,.0f}"
        pivot_rows.append(tot_row)

        h_chart_rows: List[Dict[str, Any]] = []
        for r, h_map in holiday_data.items():
            for h_name, val in h_map.items():
                h_chart_rows.append(
                    {"Holiday": h_name, "Room Type": r, val_key: val}
                )

        return ComparisonResult(
            pivot_df=pd.DataFrame(pivot_rows),
            daily_chart_df=pd.DataFrame(daily_data),
            holiday_chart_df=pd.DataFrame(h_chart_rows),
        )

    def adjust_holiday(
        self, resort_name: str, checkin: date, nights: int
    ) -> Tuple[date, int, bool]:
        """If stay overlaps holidays, expand to full holiday span."""
        resort = self.repo.get_resort(resort_name)
        if not resort or str(checkin.year) not in resort.years:
            return checkin, nights, False
        end = checkin + timedelta(days=nights - 1)
        yd = resort.years[str(checkin.year)]
        overlapping: List[Holiday] = []
        for h in yd.holidays:
            if h.start_date <= end and h.end_date >= checkin:
                overlapping.append(h)
        if not overlapping:
            return checkin, nights, False
        earliest_start = min(h.start_date for h in overlapping)
        latest_end = max(h.end_date for h in overlapping)
        adjusted_start = min(checkin, earliest_start)
        adjusted_end = max(end, latest_end)
        adjusted_nights = (adjusted_end - adjusted_start).days + 1
        return adjusted_start, adjusted_nights, True

# ==============================================================================
# LAYER 4: UI HELPERS
# ==============================================================================
def render_metrics_grid(
    result: CalculationResult,
    mode: UserMode,
    owner_params: Optional[dict],
    policy: DiscountPolicy,
) -> None:
    """Render summary metrics in a responsive grid."""
    owner_params = owner_params or {}
    if mode == UserMode.OWNER:
        num_components = sum(
            [
                owner_params.get("inc_m", False),
                owner_params.get("inc_c", False),
                owner_params.get("inc_d", False),
            ]
        )
        cols = st.columns(2 + max(num_components, 0))
        with cols[0]:
            st.metric(
                label="📊 Total Points",
                value=f"{result.total_points:,}",
                help="Total vacation points required for this stay",
            )
        with cols[1]:
            st.metric(
                label="💰 Total Cost",
                value=f"${result.financial_total:,.0f}",
                help="Total ownership cost including all selected components",
            )
        col_idx = 2
        if owner_params.get("inc_m"):
            with cols[col_idx]:
                st.metric(
                    label="🔧 Maintenance",
                    value=f"${result.m_cost:,.0f}",
                    help="Annual Maintenance attributable to this stay",
                )
            col_idx += 1
        if owner_params.get("inc_c"):
            with cols[col_idx]:
                st.metric(
                    label="💼 Capital Cost",
                    value=f"${result.c_cost:,.0f}",
                    help="Opportunity cost of capital tied up in ownership",
                )
            col_idx += 1
        if owner_params.get("inc_d"):
            with cols[col_idx]:
                st.metric(
                    label="📉 Depreciation",
                    value=f"${result.d_cost:,.0f}",
                    help="Share of asset depreciation for this usage",
                )
            col_idx += 1
    else:
        if result.discount_applied:
            cols = st.columns(3)
            pct = "30%" if policy == DiscountPolicy.PRESIDENTIAL else "25%"
            with cols[0]:
                st.metric(
                    label="📊 Total Points",
                    value=f"{result.total_points:,}",
                    help="Tier-adjusted points required",
                )
            with cols[1]:
                st.metric(
                    label="💰 Total Rent",
                    value=f"${result.financial_total:,.0f}",
                    help="Total rental cost (based on tier benefits)",
                )
            with cols[2]:
                st.metric(
                    label="🎉 Membership Tier",
                    value=pct,
                    delta=f"{len(result.discounted_days)} days",
                    help="Points benefit for membership tier",
                )
        else:
            cols = st.columns(2)
            with cols[0]:
                st.metric(
                    label="📊 Total Points",
                    value=f"{result.total_points:,}",
                    help="Total vacation points required",
                )
            with cols[1]:
                st.metric(
                    label="💰 Total Rent",
                    value=f"${result.financial_total:,.0f}",
                    help="Total rental cost (standard points)",
                )

# ==============================================================================
# NEW HELPERS FOR TABLES
# ==============================================================================
def get_all_room_types_for_resort(resort_data: ResortData) -> List[str]:
    rooms = set()
    for year_obj in resort_data.years.values():
        for season in year_obj.seasons:
            for cat in season.day_categories:
                if isinstance(cat.room_points, dict):
                    rooms.update(cat.room_points.keys())
        for holiday in year_obj.holidays:
            if isinstance(holiday.room_points, dict):
                rooms.update(holiday.room_points.keys())
    return sorted(rooms)

def build_rental_cost_table(
    resort_data: ResortData,
    year: int,
    rate: float,
    discount_mul: float = 1.0,
    mode: UserMode = UserMode.RENTER,
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
        weekly_totals = {}
        has_data = False

        for dow in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            for cat in season.day_categories:
                if dow in cat.days:
                    rp = cat.room_points
                    for room in room_types:
                        pts = rp.get(room, 0)
                        if pts:
                            has_data = True
                        weekly_totals[room] = weekly_totals.get(room, 0) + pts
                    break

        if has_data:
            row = {"Season": name}
            for room in room_types:
                raw_pts = weekly_totals.get(room, 0)
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
    for holiday in yd.holidays:
        hname = holiday.name.strip() or "Unnamed Holiday"
        rp = holiday.room_points or {}
        row = {"Season": f"Holiday – {hname}"}
        any_value = False
        for room in room_types:
            raw = rp.get(room, 0)
            if raw:
                any_value = True
            eff = math.floor(raw * discount_mul) if discount_mul < 1 else raw
            if mode == UserMode.RENTER:
                cost = math.ceil(eff * rate) if raw else 0
            else:
                m = math.ceil(eff * rate) if owner_params.get("inc_m", False) else 0
                c = math.ceil(eff * owner_params.get("cap_rate", 0.0)) if owner_params.get("inc_c", False) else 0
                d = math.ceil(eff * owner_params.get("dep_rate", 0.0)) if owner_params.get("inc_d", False) else 0
                cost = m + c + d if raw else 0
            row[room] = f"${cost:,}" if raw else "—"
        if any_value:
            rows.append(row)

    if not rows:
        return None

    return pd.DataFrame(rows, columns=["Season"] + room_types)

# ==============================================================================
# MAIN PAGE LOGIC
# ==============================================================================
def main() -> None:
    # 0) Load User Settings first
    default_settings = load_default_settings()

    # 1) Shared data auto-load (must happen BEFORE session state init so we can check IDs)
    ensure_data_in_session()

    # 2) If no data, bail out early
    if not st.session_state.data:
        st.warning("⚠️ Please open the Editor and upload/merge data_v2.json first.")
        st.info(
            "The calculator reads the same in-memory data as the Editor. "
            "Once the Editor has loaded your JSON file, you can use the calculator here."
        )
        return

    # 3) Initialize Resort Selection (with Fuzzy Matching for Preference)
    repo = MVCRepository(st.session_state.data)
    resorts_full = repo.get_resort_list_full()

    if "current_resort_id" not in st.session_state or st.session_state.current_resort_id is None:
        pref_id = default_settings.get("preferred_resort_id")
        found_id = None
        
        if pref_id:
            # Normalize preference
            norm_pref = str(pref_id).lower().strip()
            
            # Fuzzy Search through all loaded resorts
            for r in resorts_full:
                rid_raw = r.get("id", "")
                rid_norm = str(rid_raw).lower().strip()
                
                # Check for substring match in either direction
                if norm_pref == rid_norm or norm_pref in rid_norm or rid_norm in norm_pref:
                    found_id = rid_raw  # Grab the ACTUAL ID from the data
                    break
        
        # Set found ID, or fallback to first available
        if found_id:
            st.session_state.current_resort_id = found_id
        elif resorts_full:
            st.session_state.current_resort_id = resorts_full[0].get("id")

    # Initialise other keys if missing
    if "current_resort" not in st.session_state:
        st.session_state.current_resort = None
    if "show_help" not in st.session_state:
        st.session_state.show_help = False
        
    # --- Initialize Variables for Calculator Inputs ---
    # This ensures the Save button can always find these values in Session State
    initialize_session_variables(default_settings)

    # 4) Sidebar: user settings only
    with st.sidebar:
        st.divider()

        # --- NEW: SAVE/LOAD SETTINGS ---
        with st.expander("Your Calculator Settings", expanded=False):
            st.info("**Save time by saving your profile.** Store your costs, membership tier, and resort preference to a file. Upload it anytime to instantly restore your setup.")
            st.markdown("###### Load/Save Settings")
            
            # LOAD
            config_file = st.file_uploader("Load Settings (JSON)", type="json", key="user_cfg_upload")
            if config_file:
                file_sig = f"{config_file.name}_{config_file.size}"
                if "last_loaded_cfg" not in st.session_state or st.session_state.last_loaded_cfg != file_sig:
                    config_file.seek(0)
                    data = json.load(config_file)
                    apply_settings_from_dict(data)
                    st.session_state.last_loaded_cfg = file_sig
                    st.toast("✅ Settings loaded successfully!", icon="📂")
                    st.rerun()

            # SAVE
            # Construct dictionary from current session state
            current_pref_resort = st.session_state.current_resort_id if st.session_state.current_resort_id else ""
            
            current_settings = {
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
                "preferred_resort_id": current_pref_resort
            }
            st.download_button("Save Settings", json.dumps(current_settings, indent=2), "mvc_owner_settings.json", "application/json", use_container_width=True)

        st.markdown("### 👤 User Settings")
        # --- User mode selection & parameters ---
        mode_sel = st.selectbox(
            "User Mode",
            [m.value for m in UserMode],
            index=0,
            help="Select whether you're renting points or own them.",
        )
        mode = UserMode(mode_sel)
        
        owner_params: Optional[dict] = None
        policy: DiscountPolicy = DiscountPolicy.NONE
        
        # --- ISOLATED VARIABLES FOR MODES ---
        active_rate = 0.0  # This will hold the final rate passed to calculator
        opt_str = "Ordinary Level" # Default display string

        if mode == UserMode.OWNER:
            st.markdown("#### 💰 Ownership Parameters")
            
            # Using key=... automatically binds to session state
            st.number_input(
                "Maintenance per Point ($)",
                step=0.01,
                min_value=0.0,
                key="owner_maint_rate"
            )
            
            st.radio(
                "Membership Tier",
                TIER_OPTIONS,
                key="owner_tier_sel",
                help="Select membership tier.",
            )
            
            cap = st.number_input(
                "Purchase Price per Point ($)",
                step=1.0,
                min_value=0.0,
                help="Initial purchase price per MVC point.",
                key="owner_price"
            )
            
            coc_input = st.number_input(
                "Cost of Capital (%)",
                step=0.5,
                min_value=0.0,
                help="Expected return on alternative investments.",
                key="owner_coc_pct"
            )
            coc = coc_input / 100.0

            life = st.number_input(
                "Useful Life (yrs)", min_value=1, key="owner_life"
            )
            salvage = st.number_input(
                "Salvage ($/pt)",
                step=0.5,
                min_value=0.0,
                key="owner_salvage"
            )
            inc_m = st.checkbox(
                "Include Maintenance",
                help="Annual Maintenance.",
                key="owner_inc_m"
            )
            inc_c = st.checkbox(
                "Include Capital Cost",
                help="Opportunity cost of capital invested.",
                key="owner_inc_c"
            )
            inc_d = st.checkbox(
                "Include Depreciation",
                help="Asset depreciation over time.",
                key="owner_inc_d"
            )
            
            # Set Active Rate for Owner
            active_rate = st.session_state.owner_maint_rate
            opt_str = st.session_state.owner_tier_sel

            owner_params = {
                "disc_mul": 1.0,  # Will be set below
                "inc_m": inc_m,
                "inc_c": inc_c,
                "inc_d": inc_d,
                "cap_rate": cap * coc,
                "dep_rate": (cap - salvage) / life if life > 0 else 0.0,
            }
        else:
            # RENTER MODE
            st.markdown("#### 🏨 Rental Parameters")
            
            st.number_input(
                "Renter Price per Point ($)",
                step=0.01,
                min_value=0.0,
                key="renter_price"
            )
            
            st.radio(
                "Membership Tier",
                TIER_OPTIONS,
                key="renter_tier_sel",
                help="Select membership tier.",
            )
            
            # Set Active Rate for Renter
            active_rate = st.session_state.renter_price
            opt_str = st.session_state.renter_tier_sel

            if "Presidential" in opt_str:
                policy = DiscountPolicy.PRESIDENTIAL
            elif "Executive" in opt_str:
                policy = DiscountPolicy.EXECUTIVE
            # "Ordinary Level" uses NONE

        # Set disc_mul for owners (isolated logic)
        disc_mul = 1.0
        if "Executive" in opt_str:
            disc_mul = 0.75
        elif "Presidential" in opt_str:
            disc_mul = 0.7

        if owner_params:  # Only for owners
            owner_params["disc_mul"] = disc_mul

    # ===== Core calculator objects =====
    calc = MVCCalculator(repo)

    # ===== Main content =====
    render_page_header(
        "Calculator",
        f"👤 {mode.value} Mode: {'Ownership' if mode == UserMode.OWNER else 'Rental'} Cost Analysis",
        icon="🏨",
        badge_color="#059669" if mode == UserMode.OWNER else "#2563eb"
    )

    current_resort_id = st.session_state.current_resort_id

    # Shared grid (column-first) from common.ui
    render_resort_grid(resorts_full, current_resort_id)

    # Resolve selected resort object
    resort_obj = next(
        (r for r in resorts_full if r.get("id") == current_resort_id),
        None,
    )
    if not resort_obj:
        return
    r_name = resort_obj.get("display_name")
    if not r_name:
        return

    # Resort info card
    resort_info = repo.get_resort_info(r_name)
    render_resort_card(
        resort_info["full_name"],
        resort_info["timezone"],
        resort_info["address"],
    )
    st.divider()

    # ===== Booking details =====
    input_cols = st.columns([2, 1, 2, 2])
    with input_cols[0]:
        checkin = st.date_input(
            "Check-in Date",
            datetime.now().date() + timedelta(days=1),
            format="YYYY/MM/DD",
            help="Your arrival date.",
        )
    with input_cols[1]:
        nights = st.number_input(
            "Nights",
            min_value=1,
            max_value=60,
            value=7,
            help="Number of nights to stay.",
        )

    # Holiday adjustment (extend stay to full holiday span)
    adj_in, adj_n, adj = calc.adjust_holiday(r_name, checkin, nights)
    if adj:
        end_date = adj_in + timedelta(days=adj_n - 1)
        st.info(
            f"ℹ️ **Adjusted to full holiday period:** "
            f"{adj_in.strftime('%b %d, %Y')} — {end_date.strftime('%b %d, %Y')} "
            f"({adj_n} nights)"
        )

    # Derive available room types from daily points for adjusted start
    res_data = calc.repo.get_resort(r_name)
    room_types = get_all_room_types_for_resort(res_data)
    if not room_types:
        st.error("❌ No room data available for selected dates.")
        return

    with input_cols[2]:
        room_sel = st.selectbox(
            "Room Type",
            room_types,
            help="Select your primary room type.",
        )
    with input_cols[3]:
        comp_rooms = st.multiselect(
            "Compare With",
            [r for r in room_types if r != room_sel],
            help="Select additional room types to compare.",
        )
    st.divider()

    # ===== Calculation =====
    # Use active_rate which is strictly separated by mode
    res = calc.calculate_breakdown(
        r_name, room_sel, adj_in, adj_n, mode, active_rate, policy, owner_params
    )
    render_metrics_grid(res, mode, owner_params, policy)

    if res.discount_applied and mode == UserMode.RENTER:
        pct = "30%" if policy == DiscountPolicy.PRESIDENTIAL else "25%"
        st.success(
            f"🎉 **Tier Benefit Applied!** {pct} off points for {len(res.discounted_days)} day(s)."
        )
    st.divider()

    # Detailed breakdown (renamed and expanded)
    with st.expander("📋 Daily Breakdown", expanded=False):
        st.dataframe(
            res.breakdown_df,
            use_container_width=True,
            hide_index=True,
            height=min(400, (len(res.breakdown_df) + 1) * 35 + 50),
        )

    # All Room Types – This Stay (below breakdown)
    st.markdown("**All Room Types – This Stay**")
    comp_data = []
    for rm in room_types:
        # Use active_rate here as well
        room_res = calc.calculate_breakdown(r_name, rm, adj_in, adj_n, mode, active_rate, policy, owner_params)
        comp_data.append({"Room Type": rm, "Points": f"{room_res.total_points:,}", "Cost": f"${room_res.financial_total:,.0f}"})
    st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

    # Actions
    col1, col2, _ = st.columns([1, 1, 2])
    with col1:
        csv_data = res.breakdown_df.to_csv(index=False)
        st.download_button(
            "⬇️ Download CSV",
            csv_data,
            f"{r_name}_{room_sel}_{'rental' if mode == UserMode.RENTER else 'cost'}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col2:
        if st.button("ℹ️ How it is calculated", use_container_width=True):
            st.session_state.show_help = not st.session_state.show_help

    # Comparison section
    if comp_rooms:
        st.divider()
        st.markdown("### 🔍 Room Type Comparison")
        all_rooms = [room_sel] + comp_rooms
        comp_res = calc.compare_stays(
            r_name, all_rooms, adj_in, adj_n, mode, active_rate, policy, owner_params
        )
        st.dataframe(
            comp_res.pivot_df,
            use_container_width=True,
            hide_index=True,
        )
        # Visual analysis
        st.markdown("#### 📈 Visual Analysis")
        chart_cols = st.columns(2)
        with chart_cols[0]:
            if not comp_res.daily_chart_df.empty:
                y_col = "TotalCostValue" if mode == UserMode.OWNER else "RentValue"
                clean_df = comp_res.daily_chart_df[
                    comp_res.daily_chart_df["Holiday"] == "No"
                ]
                if not clean_df.empty:
                    fig = px.bar(
                        clean_df,
                        x="Day",
                        y=y_col,
                        color="Room Type",
                        barmode="group",
                        text=y_col,
                        category_orders={
                            "Day": ["Fri", "Sat", "Sun", "Mon", "Tue", "Wed", "Thu"]
                        },
                        title="Daily Costs by Day of Week",
                        color_discrete_sequence=px.colors.qualitative.Set2,
                    )
                    fig.update_traces(
                        texttemplate="$%{text:.0f}",
                        textposition="outside",
                    )
                    fig.update_layout(
                        height=450,
                        xaxis_title="Day of Week",
                        yaxis_title="Cost ($)",
                        legend_title="Room Type",
                        hovermode="x unified",
                    )
                    st.plotly_chart(fig, use_container_width=True)
        with chart_cols[1]:
            if not comp_res.holiday_chart_df.empty:
                y_col = "TotalCostValue" if mode == UserMode.OWNER else "RentValue"
                h_fig = px.bar(
                    comp_res.holiday_chart_df,
                    x="Holiday",
                    y=y_col,
                    color="Room Type",
                    barmode="group",
                    text=y_col,
                    title="Holiday Period Costs",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                h_fig.update_traces(
                    texttemplate="$%{text:.0f}",
                    textposition="outside",
                )
                h_fig.update_layout(
                    height=450,
                    xaxis_title="Holiday Period",
                    yaxis_title="Cost ($)",
                    legend_title="Room Type",
                    hovermode="x unified",
                )
                st.plotly_chart(h_fig, use_container_width=True)

    # Season / Holiday timeline
    year_str = str(adj_in.year)
    res_data = calc.repo.get_resort(r_name)
    if res_data and year_str in res_data.years:
        st.divider()
        with st.expander("📅 Season and Holiday Calendar", expanded=False):
            gantt_fig = create_gantt_chart_from_resort_data(
                res_data,
                year_str,
                global_holidays=st.session_state.data.get("global_holidays", {}),
                height=500,
            )
            st.plotly_chart(gantt_fig, use_container_width=True)

            # Rental/Cost table in expander
            year = adj_in.year
            # Use active_rate here
            cost_df = build_rental_cost_table(res_data, year, active_rate, disc_mul, mode, owner_params)
            if cost_df is not None:
                title = "7-Night Rental Costs" if mode == UserMode.RENTER else "7-Night Ownership Costs"
                note = " — Tier benefit applied" if disc_mul < 1 else ""
                st.markdown(f"**{title}** @ ${active_rate:.2f}/pt{note}")
                st.dataframe(cost_df, use_container_width=True, hide_index=True)
            else:
                st.info("No season or holiday pricing data available for this year.")

    # Help section
    if st.session_state.show_help:
        st.divider()
        with st.expander("ℹ️ How the Calculation Works", expanded=True):
            if mode == UserMode.OWNER:
                st.markdown(
                    f"""
                    ### 💰 Owner Cost Calculation
                    **Maintenance**
                    - Formula: Maintenance per point × points used
                    - Current Maintenance: **${active_rate:.2f}** per point
                    - Covers: Property upkeep, utilities, staff, amenities
                    **Capital Cost**
                    - Formula: Purchase price × cost of capital rate × points used
                    - Represents: Opportunity cost of capital invested in ownership
                    **Depreciation Cost**
                    - Formula: (Purchase price − salvage value) ÷ useful life × points used
                    - Represents: Asset value decline over time
                    **Points Calculation**
                    - Effective points may be adjusted by membership tier benefits.
                    - Holiday periods are priced as whole blocks rather than per-night averages.
                    """
                )
            else:
                if policy == DiscountPolicy.PRESIDENTIAL:
                    discount_text = (
                        "**Presidential 30% points benefit:** when booked "
                        "within 60 days of check-in."
                    )
                elif policy == DiscountPolicy.EXECUTIVE:
                    discount_text = (
                        "**Executive 25% points benefit:** when booked "
                        "within 30 days of check-in."
                    )
                else:
                    discount_text = "**Standard points applied (Ordinary Level).**"
                st.markdown(
                    f"""
                    ### 🏨 Rent Calculation
                    **Current Maintenance:** **${active_rate:.2f}** per point.
                    {discount_text}
                    - The **Points** column may show adjusted points if tier benefits apply.
                    - 💰 Rent is always computed from the **adjusted** points.
                    - Holiday periods are treated as full blocks for pricing.
                    """
                )
                
    # --- Bottom of Owner Mode: Access to Editor ---
    if mode == UserMode.OWNER:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.divider()
        col_e1, col_e2 = st.columns([4, 1])
        with col_e2:
            if st.button("🔧 Open Resort Editor", use_container_width=True):
                st.session_state.active_tool = "editor"
                st.rerun()

def run() -> None:
    main()
