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
# SETTINGS PERSISTENCE – FULLY WORKING
# ==============================================================================

def init_session_defaults():
    defaults = {
        "maintenance_rate": 0.83,
        "purchase_price": 3.5,
        "capital_cost_pct": 5.0,
        "useful_life": 20,
        "salvage_value": 3.0,
        "discount_tier": 0,
        "include_maintenance": True,
        "include_capital": True,
        "include_depreciation": False,
        "renter_rate": 0.83,
        "renter_discount_tier": 0,
        "preferred_resort_id": None,
        "settings_loaded": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def apply_settings_from_json(data: dict):
    try:
        st.session_state.maintenance_rate     = float(data.get("maintenance_rate", st.session_state.maintenance_rate))
        st.session_state.purchase_price       = float(data.get("purchase_price", st.session_state.purchase_price))
        st.session_state.capital_cost_pct     = float(data.get("capital_cost_pct", st.session_state.capital_cost_pct))
        st.session_state.useful_life          = int(data.get("useful_life", st.session_state.useful_life))
        st.session_state.salvage_value        = float(data.get("salvage_value", st.session_state.salvage_value))

        t = str(data.get("discount_tier", "")).lower()
        st.session_state.discount_tier = 2 if ("presidential" in t or "chairman" in t) else 1 if "executive" in t else 0

        st.session_state.include_maintenance  = bool(data.get("include_maintenance", True))
        st.session_state.include_capital      = bool(data.get("include_capital", True))
        st.session_state.include_depreciation = bool(data.get("include_depreciation", False))

        st.session_state.renter_rate          = float(data.get("renter_rate", st.session_state.renter_rate))
        t2 = str(data.get("renter_discount_tier", "")).lower()
        st.session_state.renter_discount_tier = 2 if ("presidential" in t2 or "chairman" in t2) else 1 if "executive" in t2 else 0

        if "preferred_resort_id" in data:
            st.session_state.preferred_resort_id = str(data["preferred_resort_id"])
    except Exception:
        st.error("Some settings failed to load")

def load_persistent_settings():
    if not st.session_state.get("settings_loaded", False):
        path = "mvc_owner_settings.json"
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    apply_settings_from_json(json.load(f))
                st.success("Auto-loaded mvc_owner_settings.json")
            except Exception:
                pass
        st.session_state.settings_loaded = True

    with st.sidebar:
        st.divider()
        st.markdown("###### Load Settings")
        uploaded = st.file_uploader("Upload JSON settings", type=["json"], key="cfg_uploader")
        if uploaded:
            try:
                apply_settings_from_json(json.load(uploaded))
                st.success(f"Loaded {uploaded.name}")
                st.rerun()
            except Exception:
                st.error("Invalid file")

def get_current_settings_json() -> str:
    settings = {
        "maintenance_rate": st.session_state.maintenance_rate,
        "purchase_price": st.session_state.purchase_price,
        "capital_cost_pct": st.session_state.capital_cost_pct,
        "useful_life": st.session_state.useful_life,
        "salvage_value": st.session_state.salvage_value,
        "discount_tier": ["ordinary", "executive", "presidential"][st.session_state.discount_tier],
        "include_maintenance": st.session_state.include_maintenance,
        "include_capital": st.session_state.include_capital,
        "include_depreciation": st.session_state.include_depreciation,
        "renter_rate": st.session_state.renter_rate,
        "renter_discount_tier": ["ordinary", "executive", "presidential"][st.session_state.renter_discount_tier],
        "preferred_resort_id": st.session_state.get("current_resort_id", ""),
    }
    return json.dumps(settings, indent=2)

# ==============================================================================
# ORIGINAL CODE – UNCHANGED
# ==============================================================================

def get_tier_index(tier_string: str) -> int:
    s = str(tier_string).lower()
    if "presidential" in s or "chairman" in s:
        return 2
    if "executive" in s:
        return 1
    return 0

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
        if not raw_r:
            return None
        years_data: Dict[str, YearData] = {}
        for year_str, y_content in raw_r.get("years", {}).items():
            holidays: List[Holiday] = []
            for h in y_content.get("holidays", []):
                ref = h.get("global_reference")
                if ref and ref in self._global_holidays.get(year_str, {}):
                    g_dates = self._global_holidays[year_str][ref]
                    holidays.append(Holiday(name=h.get("name", ref), start_date=g_dates[0], end_date=g_dates[1], room_points=h.get("room_points", {})))
            seasons: List[Season] = []
            for s in y_content.get("seasons", []):
                periods: List[SeasonPeriod] = []
                for p in s.get("periods", []):
                    try:
                        periods.append(SeasonPeriod(start=datetime.strptime(p["start"], "%Y-%m-%d").date(),
                                                   end=datetime.strptime(p["end"], "%Y-%m-%d").date()))
                    except Exception:
                        continue
                day_cats: List[DayCategory] = []
                for cat in s.get("day_categories", {}).values():
                    day_cats.append(DayCategory(days=cat.get("day_pattern", []), room_points=cat.get("room_points", {})))
                seasons.append(Season(name=s["name"], periods=periods, day_categories=day_cats))
            years_data[year_str] = YearData(holidays=holidays, seasons=seasons)
        resort_obj = ResortData(id=raw_r["id"], name=raw_r["display_name"], years=years_data)
        self._resort_cache[resort_name] = resort_obj
        return resort_obj

    def get_resort_info(self, resort_name: str) -> Dict[str, str]:
        raw_r = next((r for r in self._raw.get("resorts", []) if r["display_name"] == resort_name), None)
        if raw_r:
            return {"full_name": raw_r.get("resort_name", resort_name), "timezone": raw_r.get("timezone", "Unknown"), "address": raw_r.get("address", "Address not available")}
        return {"full_name": resort_name, "timezone": "Unknown", "address": "Address not available"}

class MVCCalculator:
    def __init__(self, repo: MVCRepository):
        self.repo = repo

    def _get_daily_points(self, resort: ResortData, day: date) -> Tuple[Dict[str, int], Optional[Holiday]]:
        year_str = str(day.year)
        if year_str not in resort.years:
            return {}, None
        yd = resort.years[year_str]
        for h in yd.holidays:
            if h.start_date <= day <= h.end_date:
                return h.room_points, h
        dow_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
        dow = dow_map[day.weekday()]
        for s in yd.seasons:
            for p in s.periods:
                if p.start <= day <= p.end:
                    for cat in s.day_categories:
                        if dow in cat.days:
                            return cat.room_points, None
        return {}, None

    def calculate_breakdown(self, resort_name: str, room: str, checkin: date, nights: int,
                            user_mode: UserMode, rate: float, discount_policy: DiscountPolicy = DiscountPolicy.NONE,
                            owner_config: Optional[dict] = None) -> CalculationResult:
        resort = self.repo.get_resort(resort_name)
        if not resort:
            return CalculationResult(pd.DataFrame(), 0, 0.0, False, [])

        if user_mode == UserMode.RENTER:
            rate = round(float(rate), 2)

        rows: List[Dict[str, Any]] = []
        tot_eff_pts = 0
        tot_financial = 0.0
        tot_m = tot_c = tot_d = 0.0  # ← Fixed the typo here
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
                    if (discount_policy == DiscountPolicy.PRESIDENTIAL and days_out <= 60) or \
                       (discount_policy == DiscountPolicy.EXECUTIVE and days_out <= 30):
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
                    "Day": "",
                    "Points": eff,
                }
                if is_owner:
                    if owner_config and owner_config.get("inc_m", False): row["Maintenance"] = m
                    if owner_config and owner_config.get("inc_c", False): row["Capital Cost"] = c
                    if owner_config and owner_config.get("inc_d", False): row["Depreciation"] = dp
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
                    disc_mul = owner_config.get("disc_mul", 1.0)
                    disc_pct = (1 - disc_mul) * 100
                    thresh = 30 if disc_pct == 25 else 60 if disc_pct == 30 else 0
                    if disc_pct > 0 and days_out <= thresh:
                        eff = math.floor(raw * disc_mul)
                else:
                    renter_disc_mul = 1.0
                    if discount_policy == DiscountPolicy.PRESIDENTIAL:
                        renter_disc_mul = 0.7
                    elif discount_policy == DiscountPolicy.EXECUTIVE:
                        renter_disc_mul = 0.75
                    if (discount_policy == DiscountPolicy.PRESIDENTIAL and days_out <= 60) or \
                       (discount_policy == DiscountPolicy.EXECUTIVE and days_out <= 30):
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
                    if owner_config and owner_config.get("inc_m", False): row["Maintenance"] = m
                    if owner_config and owner_config.get("inc_c", False): row["Capital Cost"] = c
                    if owner_config and owner_config.get("inc_d", False): row["Depreciation"] = dp
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
            maint_total = math.ceil(round(tot_eff_pts * rate, 8)) if owner_config.get("inc_m", False) else 0.0
            cap_total = math.ceil(round(tot_eff_pts * owner_config.get("cap_rate", 0.0), 8)) if owner_config.get("inc_c", False) else 0.0
            dep_total = math.ceil(round(tot_eff_pts * owner_config.get("dep_rate", 0.0), 8)) if owner_config.get("inc_d", False) else 0.0
            tot_m, tot_c, tot_d = maint_total, cap_total, dep_total
            tot_financial = maint_total + cap_total + dep_total

        if is_owner and not df.empty:
            for col in ["Maintenance", "Capital Cost", "Depreciation", "Total Cost"]:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: f"${x:,.0f}" if isinstance(x, (int, float)) else x)
        else:
            for col in df.columns:
                if col not in ["Date", "Day", "Points"]:
                    df[col] = df[col].apply(lambda x: f"${x:,.0f}" if isinstance(x, (int, float)) else x)

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

# ... rest of your functions (render_metrics_grid, get_all_room_types_for_resort, etc.) are unchanged ...

def main() -> None:
    init_session_defaults()
    load_persistent_settings()

    ensure_data_in_session()
    if not st.session_state.data:
        st.warning("Please open the Editor and upload/merge data_v2.json first.")
        st.info("The calculator reads the same in-memory data as the Editor.")
        return

    repo = MVCRepository(st.session_state.data)
    calc = MVCCalculator(repo)
    resorts_full = repo.get_resort_list_full()

    if "current_resort_id" not in st.session_state or st.session_state.current_resort_id is None:
        pref = st.session_state.get("preferred_resort_id")
        found = next((r["id"] for r in resorts_full if r["id"] == pref), None)
        st.session_state.current_resort_id = found or (resorts_full[0]["id"] if resorts_full else None)

    if "show_help" not in st.session_state:
        st.session_state.show_help = False

    with st.sidebar:
        st.divider()
        st.markdown("### User Settings")
        mode = UserMode(st.selectbox("User Mode", [m.value for m in UserMode], index=0))

        owner_params: Optional[dict] = None
        policy: DiscountPolicy = DiscountPolicy.NONE
        active_rate = 0.0

        if mode == UserMode.OWNER:
            st.markdown("#### Ownership Parameters")
            maintenance_rate = st.number_input("Maintenance per Point ($)", value=st.session_state.maintenance_rate, step=0.01, min_value=0.0, key="owner_maint")
            tier_option = st.radio("Membership Tier",
                ["Ordinary Level", "Executive: 25% Points Benefit (within 30 days)", "Presidential: 30% Points Benefit (within 60 days)"],
                index=st.session_state.discount_tier, key="owner_tier")

            purchase_price = st.number_input("Purchase Price per Point ($)", value=st.session_state.purchase_price, step=1.0, key="owner_purchase")
            coc_pct = st.number_input("Cost of Capital (%)", value=st.session_state.capital_cost_pct, step=0.5, key="owner_coc")
            useful_life = st.number_input("Useful Life (yrs)", value=st.session_state.useful_life, min_value=1, key="owner_life")
            salvage = st.number_input("Salvage ($/pt)", value=st.session_state.salvage_value, step=0.5, key="owner_salvage")

            inc_m = st.checkbox("Include Maintenance", value=st.session_state.include_maintenance, key="owner_inc_m")
            inc_c = st.checkbox("Include Capital Cost", value=st.session_state.include_capital, key="owner_inc_c")
            inc_d = st.checkbox("Include Depreciation", value=st.session_state.include_depreciation, key="owner_inc_d")

            active_rate = maintenance_rate
            disc_mul = 0.75 if "Executive" in tier_option else 0.7 if "Presidential" in tier_option else 1.0

            owner_params = {
                "disc_mul": disc_mul,
                "inc_m": inc_m,
                "inc_c": inc_c,
                "inc_d": inc_d,
                "cap_rate": purchase_price * (coc_pct / 100.0),
                "dep_rate": (purchase_price - salvage) / useful_life if useful_life > 0 else 0.0,
            }
        else:
            st.markdown("#### Rental Parameters")
            renter_rate = st.number_input("Renter Price per Point ($)", value=st.session_state.renter_rate, step=0.01, min_value=0.0, key="renter_rate")
            tier_option = st.radio("Membership Tier",
                ["Ordinary Level", "Executive: 25% Points Benefit (within 30 days)", "Presidential: 30% Points Benefit (within 60 days)"],
                index=st.session_state.renter_discount_tier, key="renter_tier")

            active_rate = renter_rate
            if "Presidential" in tier_option:
                policy = DiscountPolicy.PRESIDENTIAL
            elif "Executive" in tier_option:
                policy = DiscountPolicy.EXECUTIVE

        st.divider()
        st.markdown("###### Save Settings")
        st.download_button(
            label="Download mvc_owner_settings.json",
            data=get_current_settings_json(),
            file_name="mvc_owner_settings.json",
            mime="application/json",
            use_container_width=True
        )

    render_page_header("Calculator", f"{mode.value} Mode: {'Ownership' if mode == UserMode.OWNER else 'Rental'} Cost Analysis", icon="hotel", badge_color="#059669" if mode == UserMode.OWNER else "#2563eb")

    current_resort_id = st.session_state.current_resort_id
    render_resort_grid(resorts_full, current_resort_id)

    resort_obj = next((r for r in resorts_full if r.get("id") == current_resort_id), None)
    if not resort_obj: return
    r_name = resort_obj.get("display_name")

    resort_info = repo.get_resort_info(r_name)
    render_resort_card(resort_info["full_name"], resort_info["timezone"], resort_info["address"])
    st.divider()

    input_cols = st.columns([2, 1, 2, 2])
    with input_cols[0]:
        checkin = st.date_input("Check-in Date", datetime.now().date() + timedelta(days=1), format="YYYY/MM/DD")
    with input_cols[1]:
        nights = st.number_input("Nights", min_value=1, max_value=60, value=7)

    adj_in, adj_n, adj = calc.adjust_holiday(r_name, checkin, nights)
    if adj:
        end_date = adj_in + timedelta(days=adj_n - 1)
        st.info(f"Adjusted to full holiday period: {adj_in.strftime('%b %d, %Y')} — {end_date.strftime('%b %d, %Y')} ({adj_n} nights)")

    res_data = calc.repo.get_resort(r_name)
    room_types = get_all_room_types_for_resort(res_data)
    if not room_types:
        st.error("No room data available.")
        return

    with input_cols[2]:
        room_sel = st.selectbox("Room Type", room_types)
    with input_cols[3]:
        comp_rooms = st.multiselect("Compare With", [r for r in room_types if r != room_sel])
    st.divider()

    result = calc.calculate_breakdown(r_name, room_sel, adj_in, adj_n, mode, active_rate, policy, owner_params)
    render_metrics_grid(result, mode, owner_params, policy)

    if result.discount_applied and mode == UserMode.RENTER:
        pct = "30%" if policy == DiscountPolicy.PRESIDENTIAL else "25%"
        st.success(f"Tier Benefit Applied! {pct} off points for {len(result.discounted_days)} day(s).")
    st.divider()

    with st.expander("Daily Breakdown", expanded=False):
        st.dataframe(result.breakdown_df, use_container_width=True, hide_index=True)

    st.markdown("**All Room Types – This Stay**")
    comp_data = []
    for rm in room_types:
        room_res = calc.calculate_breakdown(r_name, rm, adj_in, adj_n, mode, active_rate, policy, owner_params)
        comp_data.append({"Room Type": rm, "Points": f"{room_res.total_points:,}", "Cost": f"${room_res.financial_total:,.0f}"})
    st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

    col1, col2, _ = st.columns([1, 1, 2])
    with col1:
        csv = result.breakdown_df.to_csv(index=False)
        st.download_button("Download CSV", csv, f"{r_name}_{room_sel}_{'rental' if mode == UserMode.RENTER else 'cost'}.csv", mime="text/csv", use_container_width=True)
    with col2:
        if st.button("How it is calculated", use_container_width=True):
            st.session_state.show_help = not st.session_state.show_help

    if st.session_state.show_help:
        st.divider()
        with st.expander("How the Calculation Works", expanded=True):
            if mode == UserMode.OWNER:
                st.markdown("**Owner Cost Calculation** – Maintenance + Capital + Depreciation")
            else:
                st.markdown("**Rent Calculation** – Based on tier-adjusted points")

def run() -> None:
    main()

if __name__ == "__main__":
    run()
