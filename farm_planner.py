#!/usr/bin/env python3
import csv
import json
import os
import random
from dataclasses import dataclass
from enum import Enum


class Season(Enum):
    SPRING = "春季"
    SUMMER = "夏季"
    AUTUMN = "秋季"
    WINTER = "冬季"


SEASON_ORDER = [Season.SPRING, Season.SUMMER, Season.AUTUMN, Season.WINTER]
SEASON_INDEX = {s: i for i, s in enumerate(SEASON_ORDER)}


def _season_sort_key(year, season):
    return year * 4 + SEASON_INDEX[season]


@dataclass
class Crop:
    name: str
    seasons: list
    growth_days: int
    yield_per_mu: float
    water_need: str
    fertilizer_need: str
    npk_per_mu: dict

    def to_dict(self):
        return {
            "name": self.name,
            "seasons": [s.value for s in self.seasons],
            "growth_days": self.growth_days,
            "yield_per_mu": self.yield_per_mu,
            "water_need": self.water_need,
            "fertilizer_need": self.fertilizer_need,
            "npk_per_mu": self.npk_per_mu,
        }

    @staticmethod
    def from_dict(d):
        return Crop(
            name=d["name"],
            seasons=[Season(s) for s in d["seasons"]],
            growth_days=d["growth_days"],
            yield_per_mu=d["yield_per_mu"],
            water_need=d["water_need"],
            fertilizer_need=d["fertilizer_need"],
            npk_per_mu=d["npk_per_mu"],
        )


DEFAULT_CROPS = [
    Crop("小麦", [Season.AUTUMN, Season.WINTER], 210, 400, "中等", "中等",
         {"N": 12.0, "P": 5.0, "K": 6.0}),
    Crop("玉米", [Season.SPRING, Season.SUMMER], 120, 600, "较高", "较高",
         {"N": 15.0, "P": 6.0, "K": 8.0}),
    Crop("水稻", [Season.SPRING, Season.SUMMER], 130, 500, "极高", "较高",
         {"N": 14.0, "P": 5.5, "K": 7.0}),
    Crop("大豆", [Season.SPRING, Season.SUMMER], 100, 180, "中等", "较低",
         {"N": 2.0, "P": 4.0, "K": 4.0}),
    Crop("土豆", [Season.SPRING, Season.AUTUMN], 90, 2500, "中等", "中等",
         {"N": 8.0, "P": 5.0, "K": 10.0}),
]

DEFAULT_PRICES = {
    "小麦": 2.8,
    "玉米": 2.6,
    "水稻": 3.0,
    "大豆": 5.5,
    "土豆": 1.5,
}

DEFAULT_COSTS = {
    "小麦": {"seed_per_mu": 60.0, "irrigation_per_mu": 80.0, "labor_per_mu": 100.0},
    "玉米": {"seed_per_mu": 70.0, "irrigation_per_mu": 100.0, "labor_per_mu": 110.0},
    "水稻": {"seed_per_mu": 80.0, "irrigation_per_mu": 200.0, "labor_per_mu": 150.0},
    "大豆": {"seed_per_mu": 90.0, "irrigation_per_mu": 60.0, "labor_per_mu": 80.0},
    "土豆": {"seed_per_mu": 200.0, "irrigation_per_mu": 90.0, "labor_per_mu": 120.0},
}

FERTILIZER_UNIT_PRICE = {"N": 4.5, "P": 5.0, "K": 4.0}


@dataclass
class Field:
    name: str
    area: float
    soil_type: str
    drainage_score: int

    def to_dict(self):
        return {
            "name": self.name,
            "area": self.area,
            "soil_type": self.soil_type,
            "drainage_score": self.drainage_score,
        }

    @staticmethod
    def from_dict(d):
        return Field(**d)


@dataclass
class PlantingEntry:
    field_name: str
    year: int
    season: Season
    crop_name: str

    def to_dict(self):
        return {
            "field_name": self.field_name,
            "year": self.year,
            "season": self.season.value,
            "crop_name": self.crop_name,
        }

    @staticmethod
    def from_dict(d):
        return PlantingEntry(
            field_name=d["field_name"],
            year=d.get("year", 2026),
            season=Season(d["season"]),
            crop_name=d["crop_name"],
        )


@dataclass
class DisasterRecord:
    disaster_type: str
    year: int
    season: Season
    field_names: list
    severity: float
    triggered_mode: str

    def to_dict(self):
        return {
            "disaster_type": self.disaster_type,
            "year": self.year,
            "season": self.season.value,
            "field_names": self.field_names,
            "severity": self.severity,
            "triggered_mode": self.triggered_mode,
        }

    @staticmethod
    def from_dict(d):
        return DisasterRecord(
            disaster_type=d["disaster_type"],
            year=d.get("year", 2026),
            season=Season(d["season"]),
            field_names=d["field_names"],
            severity=d["severity"],
            triggered_mode=d["triggered_mode"],
        )


@dataclass
class ActualHarvest:
    field_name: str
    year: int
    season: Season
    crop_name: str
    actual_yield: float

    def to_dict(self):
        return {
            "field_name": self.field_name,
            "year": self.year,
            "season": self.season.value,
            "crop_name": self.crop_name,
            "actual_yield": self.actual_yield,
        }

    @staticmethod
    def from_dict(d):
        return ActualHarvest(
            field_name=d["field_name"],
            year=d.get("year", 2026),
            season=Season(d["season"]),
            crop_name=d["crop_name"],
            actual_yield=d["actual_yield"],
        )


class FarmManager:
    SOIL_MULTIPLIER = {"沙土": 0.85, "黏土": 0.90, "壤土": 1.0}
    DRAINAGE_THRESHOLD = 5
    ROTATION_PENALTY = 0.10

    def __init__(self, data_file="farm_data.json"):
        self.data_file = data_file
        self.crops: dict[str, Crop] = {}
        self.fields: dict[str, Field] = {}
        self.plan: list[PlantingEntry] = []
        self.actual_harvests: list[ActualHarvest] = []
        self.disaster_records: list[DisasterRecord] = []
        self.prices: dict[str, float] = dict(DEFAULT_PRICES)
        self.costs: dict[str, dict] = json.loads(json.dumps(DEFAULT_COSTS))
        self.fertilizer_prices: dict[str, float] = dict(FERTILIZER_UNIT_PRICE)
        self.current_year: int = 2026
        self.plan_years: list = [2026]
        self.budget_targets: dict = {}
        self.scenarios: dict = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.data_file):
            for c in DEFAULT_CROPS:
                self.crops[c.name] = c
            self._save()
            return
        with open(self.data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.crops = {n: Crop.from_dict(d) for n, d in data.get("crops", {}).items()}
        self.fields = {n: Field.from_dict(d) for n, d in data.get("fields", {}).items()}
        self.plan = [PlantingEntry.from_dict(d) for d in data.get("plan", [])]
        self.actual_harvests = [ActualHarvest.from_dict(d) for d in data.get("actual_harvests", [])]
        self.disaster_records = [DisasterRecord.from_dict(d) for d in data.get("disaster_records", [])]
        self.prices = data.get("prices", dict(DEFAULT_PRICES))
        self.costs = data.get("costs", json.loads(json.dumps(DEFAULT_COSTS)))
        self.fertilizer_prices = data.get("fertilizer_prices", dict(FERTILIZER_UNIT_PRICE))
        self.current_year = data.get("current_year", 2026)
        self.plan_years = sorted(data.get("plan_years", [2026]))
        raw_budget = data.get("budget_targets", {})
        self.budget_targets = {int(k): v for k, v in raw_budget.items()}
        self.scenarios = data.get("scenarios", {})
        self._sync_plan_years()

    def _save(self):
        self._sync_plan_years()
        data = {
            "crops": {n: c.to_dict() for n, c in self.crops.items()},
            "fields": {n: f.to_dict() for n, f in self.fields.items()},
            "plan": [e.to_dict() for e in self.plan],
            "actual_harvests": [h.to_dict() for h in self.actual_harvests],
            "disaster_records": [d.to_dict() for d in self.disaster_records],
            "prices": self.prices,
            "costs": self.costs,
            "fertilizer_prices": self.fertilizer_prices,
            "current_year": self.current_year,
            "plan_years": self.plan_years,
            "budget_targets": self.budget_targets,
            "scenarios": self.scenarios,
        }
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _sync_plan_years(self):
        years = set(self.plan_years)
        for e in self.plan:
            years.add(e.year)
        for h in self.actual_harvests:
            years.add(h.year)
        for d in self.disaster_records:
            years.add(d.year)
        if not years:
            years = {self.current_year}
        self.plan_years = sorted(years)

    def set_plan_years(self, start_year, num_years):
        self.current_year = start_year
        self.plan_years = [start_year + i for i in range(num_years)]
        self.plan = [e for e in self.plan if e.year in self.plan_years]
        self.actual_harvests = [h for h in self.actual_harvests if h.year in self.plan_years]
        self.disaster_records = [d for d in self.disaster_records if d.year in self.plan_years]
        self._save()

    def add_crop(self, name, seasons, growth_days, yield_per_mu, water_need,
                 fertilizer_need, npk_per_mu):
        crop = Crop(name, seasons, growth_days, yield_per_mu, water_need,
                    fertilizer_need, npk_per_mu)
        self.crops[name] = crop
        if name not in self.prices:
            self.prices[name] = 0.0
        if name not in self.costs:
            self.costs[name] = {"seed_per_mu": 50.0, "irrigation_per_mu": 80.0, "labor_per_mu": 100.0}
        self._save()
        return crop

    def add_field(self, name, area, soil_type, drainage_score):
        f = Field(name, area, soil_type, drainage_score)
        self.fields[name] = f
        self._save()
        return f

    def add_plan_entry(self, field_name, year, season, crop_name):
        if field_name not in self.fields:
            return None, f"农田 '{field_name}' 不存在"
        if crop_name not in self.crops:
            return None, f"作物 '{crop_name}' 不存在"
        crop = self.crops[crop_name]
        if season not in crop.seasons:
            return None, f"{crop_name} 不适合在{season.value}种植"
        existing = [e for e in self.plan
                    if e.field_name == field_name and e.year == year and e.season == season]
        for e in existing:
            self.plan.remove(e)
        entry = PlantingEntry(field_name, year, season, crop_name)
        self.plan.append(entry)
        if year not in self.plan_years:
            self.plan_years.append(year)
            self.plan_years.sort()
        self._save()
        return entry, None

    def get_cross_year_info(self, year):
        info = []
        prev_year = year - 1
        if prev_year not in self.plan_years:
            return info
        winter_entries = [e for e in self.plan
                          if e.year == prev_year and e.season == Season.WINTER]
        spring_entries = [e for e in self.plan
                          if e.year == year and e.season == Season.SPRING]
        for we in winter_entries:
            se = next((e for e in spring_entries if e.field_name == we.field_name), None)
            if se:
                is_conflict = we.crop_name == se.crop_name
                info.append({
                    "field": we.field_name,
                    "prev_year": prev_year,
                    "prev_season": Season.WINTER,
                    "prev_crop": we.crop_name,
                    "curr_year": year,
                    "curr_season": Season.SPRING,
                    "curr_crop": se.crop_name,
                    "is_conflict": is_conflict,
                    "penalty": self.ROTATION_PENALTY if is_conflict else 0,
                })
            else:
                info.append({
                    "field": we.field_name,
                    "prev_year": prev_year,
                    "prev_season": Season.WINTER,
                    "prev_crop": we.crop_name,
                    "curr_year": year,
                    "curr_season": Season.SPRING,
                    "curr_crop": "",
                    "is_conflict": False,
                    "penalty": 0,
                })
        return info

    def get_cross_year_connections(self, year):
        info = self.get_cross_year_info(year)
        return [i for i in info if i["is_conflict"]]

    def check_rotation_conflicts(self, year=None):
        conflicts = []
        entries_by_field = {}
        plan_entries = self.plan if year is None else [e for e in self.plan if e.year == year]
        for entry in plan_entries:
            key = entry.field_name
            if key not in entries_by_field:
                entries_by_field[key] = []
            entries_by_field[key].append(entry)

        if year is not None:
            cross = self.get_cross_year_connections(year)
            conflicts.extend(cross)

        for fname, entries in entries_by_field.items():
            entries_sorted = sorted(
                entries,
                key=lambda e: _season_sort_key(e.year, e.season)
            )
            for i in range(1, len(entries_sorted)):
                prev = entries_sorted[i - 1]
                curr = entries_sorted[i]
                if not self._are_seasons_adjacent(prev.year, prev.season, curr.year, curr.season):
                    continue
                if prev.crop_name == curr.crop_name:
                    conflicts.append({
                        "field": fname,
                        "prev_year": prev.year,
                        "prev_season": prev.season,
                        "curr_year": curr.year,
                        "curr_season": curr.season,
                        "crop": curr.crop_name,
                        "penalty": self.ROTATION_PENALTY,
                    })
        return conflicts

    def _are_seasons_adjacent(self, prev_year, prev_season, curr_year, curr_season):
        prev_idx = SEASON_INDEX[prev_season]
        curr_idx = SEASON_INDEX[curr_season]
        if prev_year == curr_year:
            return curr_idx == prev_idx + 1
        elif curr_year == prev_year + 1:
            return prev_idx == 3 and curr_idx == 0
        else:
            return False

    def _soil_multiplier(self, field: Field, crop: Crop):
        base = self.SOIL_MULTIPLIER.get(field.soil_type, 1.0)
        if crop.water_need in ("较高", "极高") and field.drainage_score < self.DRAINAGE_THRESHOLD:
            if crop.water_need == "极高":
                base *= 0.85
            else:
                base *= 0.92
        return base

    def predict_yield(self, field_name, year, season, crop_name, include_disasters=True):
        f = self.fields.get(field_name)
        c = self.crops.get(crop_name)
        if not f or not c:
            return 0.0
        base = c.yield_per_mu * f.area
        soil_mult = self._soil_multiplier(f, c)
        rotation_mult = 1.0
        conflicts = self.check_rotation_conflicts()
        for cf in conflicts:
            if (cf["field"] == field_name and cf["curr_year"] == year
                    and cf["curr_season"] == season and cf["crop"] == crop_name):
                rotation_mult = 1.0 - cf["penalty"]
                break
        disaster_mult = 1.0
        if include_disasters:
            for dr in self.disaster_records:
                if dr.year == year and dr.season == season and field_name in dr.field_names:
                    disaster_mult *= (1.0 - dr.severity)
        return base * soil_mult * rotation_mult * disaster_mult

    def predict_season_harvest(self, year, season):
        total = 0.0
        details = []
        for entry in self.plan:
            if entry.year == year and entry.season == season:
                y = self.predict_yield(entry.field_name, year, entry.season, entry.crop_name)
                total += y
                details.append({
                    "field": entry.field_name,
                    "crop": entry.crop_name,
                    "year": year,
                    "season": entry.season,
                    "predicted_kg": y,
                })
        return total, details

    def predict_annual_harvest(self, year):
        results = {}
        for s in SEASON_ORDER:
            total, details = self.predict_season_harvest(year, s)
            results[s] = {"total_kg": total, "details": details}
        return results

    def predict_multi_year_harvest(self, years=None):
        if years is None:
            years = self.plan_years
        results = {}
        for y in years:
            results[y] = self.predict_annual_harvest(y)
        return results

    def calculate_season_costs(self, year, season):
        seed_cost = 0.0
        fert_cost = 0.0
        irrig_cost = 0.0
        labor_cost = 0.0
        details = []
        for entry in self.plan:
            if entry.year != year or entry.season != season:
                continue
            crop = self.crops.get(entry.crop_name)
            fld = self.fields.get(entry.field_name)
            if not crop or not fld:
                continue
            area = fld.area
            c = self.costs.get(entry.crop_name, {})
            sc = c.get("seed_per_mu", 0) * area
            ic = c.get("irrigation_per_mu", 0) * area
            lc = c.get("labor_per_mu", 0) * area
            npk = crop.npk_per_mu
            fc = sum(npk.get(k, 0) * self.fertilizer_prices.get(k, 0) * area
                     for k in ["N", "P", "K"])
            total_c = sc + fc + ic + lc
            seed_cost += sc
            fert_cost += fc
            irrig_cost += ic
            labor_cost += lc
            details.append({
                "field": entry.field_name,
                "crop": entry.crop_name,
                "area": area,
                "seed_cost": sc,
                "fertilizer_cost": fc,
                "irrigation_cost": ic,
                "labor_cost": lc,
                "total_cost": total_c,
            })
        total = seed_cost + fert_cost + irrig_cost + labor_cost
        return total, {"seed": seed_cost, "fertilizer": fert_cost,
                       "irrigation": irrig_cost, "labor": labor_cost}, details

    def calculate_annual_costs(self, year):
        total_season = {}
        grand_total = 0.0
        for s in SEASON_ORDER:
            total, breakdown, _ = self.calculate_season_costs(year, s)
            total_season[s] = {"total": total, "breakdown": breakdown}
            grand_total += total
        return grand_total, total_season

    def estimate_income(self, year, season):
        _, details = self.predict_season_harvest(year, season)
        total_income = 0.0
        income_details = []
        for d in details:
            price = self.prices.get(d["crop"], 0.0)
            income = d["predicted_kg"] * price
            total_income += income
            income_details.append({
                "field": d["field"],
                "crop": d["crop"],
                "predicted_kg": d["predicted_kg"],
                "price_per_kg": price,
                "income": income,
            })
        return total_income, income_details

    def estimate_annual_income(self, year):
        results = {}
        for s in SEASON_ORDER:
            income, details = self.estimate_income(year, s)
            results[s] = {"total_income": income, "details": details}
        return results

    def profit_analysis(self, year=None):
        if year is None:
            years = self.plan_years
        else:
            years = [year]
        results = {}
        for y in years:
            total_revenue = 0.0
            total_cost = 0.0
            season_data = {}
            for s in SEASON_ORDER:
                revenue, _ = self.estimate_income(y, s)
                cost, breakdown, _ = self.calculate_season_costs(y, s)
                profit = revenue - cost
                total_revenue += revenue
                total_cost += cost
                season_data[s] = {
                    "revenue": revenue,
                    "cost": cost,
                    "cost_breakdown": breakdown,
                    "profit": profit,
                }
            results[y] = {
                "total_revenue": total_revenue,
                "total_cost": total_cost,
                "total_profit": total_revenue - total_cost,
                "seasons": season_data,
            }
        return results

    def record_actual_harvest(self, field_name, year, season, crop_name, actual_kg):
        existing = [h for h in self.actual_harvests
                    if h.field_name == field_name and h.year == year and h.season == season]
        for h in existing:
            self.actual_harvests.remove(h)
        ah = ActualHarvest(field_name, year, season, crop_name, actual_kg)
        self.actual_harvests.append(ah)
        self._save()
        return ah

    def deviation_analysis(self, year=None, season=None):
        reports = []
        entries = self.plan
        if year is not None:
            entries = [e for e in entries if e.year == year]
        if season is not None:
            entries = [e for e in entries if e.season == season]
        for entry in entries:
            predicted = self.predict_yield(entry.field_name, entry.year,
                                           entry.season, entry.crop_name)
            actual = None
            for ah in self.actual_harvests:
                if (ah.field_name == entry.field_name and ah.year == entry.year
                        and ah.season == entry.season and ah.crop_name == entry.crop_name):
                    actual = ah.actual_yield
                    break
            if actual is None:
                continue
            deviation = actual - predicted
            deviation_pct = (deviation / predicted * 100) if predicted > 0 else 0.0
            reports.append({
                "field": entry.field_name,
                "year": entry.year,
                "season": entry.season,
                "crop": entry.crop_name,
                "predicted_kg": predicted,
                "actual_kg": actual,
                "deviation_kg": deviation,
                "deviation_pct": deviation_pct,
            })
        return reports

    def deviation_by_crop(self, year=None):
        reports = self.deviation_analysis(year=year)
        by_crop = {}
        for r in reports:
            crop = r["crop"]
            if crop not in by_crop:
                by_crop[crop] = {
                    "crop": crop,
                    "count": 0,
                    "total_predicted": 0.0,
                    "total_actual": 0.0,
                }
            by_crop[crop]["count"] += 1
            by_crop[crop]["total_predicted"] += r["predicted_kg"]
            by_crop[crop]["total_actual"] += r["actual_kg"]
        result = []
        for crop, data in by_crop.items():
            total_dev = data["total_actual"] - data["total_predicted"]
            dev_pct = (total_dev / data["total_predicted"] * 100) if data["total_predicted"] > 0 else 0.0
            data["total_deviation"] = total_dev
            data["deviation_pct"] = dev_pct
            result.append(data)
        result.sort(key=lambda x: x["deviation_pct"], reverse=True)
        return result

    def deviation_by_field(self, year=None):
        reports = self.deviation_analysis(year=year)
        by_field = {}
        for r in reports:
            fname = r["field"]
            if fname not in by_field:
                by_field[fname] = {
                    "field": fname,
                    "count": 0,
                    "total_predicted": 0.0,
                    "total_actual": 0.0,
                }
            by_field[fname]["count"] += 1
            by_field[fname]["total_predicted"] += r["predicted_kg"]
            by_field[fname]["total_actual"] += r["actual_kg"]
        result = []
        for fname, data in by_field.items():
            total_dev = data["total_actual"] - data["total_predicted"]
            dev_pct = (total_dev / data["total_predicted"] * 100) if data["total_predicted"] > 0 else 0.0
            data["total_deviation"] = total_dev
            data["deviation_pct"] = dev_pct
            result.append(data)
        result.sort(key=lambda x: x["deviation_pct"], reverse=True)
        return result

    def simulate_disaster(self, disaster_type, year, season, field_names=None, severity=None):
        if not self.fields:
            return None, "尚未添加任何农田，请先添加农田后再进行灾害模拟"
        if severity is None:
            severity = round(random.uniform(0.1, 0.5), 2)
        if field_names is None:
            k = min(random.randint(1, max(1, len(self.fields))), len(self.fields))
            field_names = random.sample(list(self.fields.keys()), k=k)
            triggered = "随机"
        else:
            valid = [fn for fn in field_names if fn in self.fields]
            field_names = valid
            triggered = "手动"
        if not field_names:
            return None, "没有可用的农田"
        dr = DisasterRecord(disaster_type, year, season, field_names, severity, triggered)
        self.disaster_records.append(dr)
        self._save()
        return dr, None

    def random_disaster(self, year=None):
        if not self.fields:
            return None
        dtype = random.choice(["干旱", "洪涝", "霜冻", "虫害"])
        if year is None:
            year = random.choice(self.plan_years) if self.plan_years else self.current_year
        season = random.choice(SEASON_ORDER)
        severity = round(random.uniform(0.1, 0.5), 2)
        k = min(random.randint(1, max(1, len(self.fields))), len(self.fields))
        affected = random.sample(list(self.fields.keys()), k=k)
        dr = DisasterRecord(dtype, year, season, affected, severity, "随机")
        self.disaster_records.append(dr)
        self._save()
        return dr

    def clear_disasters(self):
        self.disaster_records.clear()
        self._save()

    def calculate_fertilizer(self, year=None):
        totals = {"N": 0.0, "P": 0.0, "K": 0.0}
        details = []
        entries = self.plan if year is None else [e for e in self.plan if e.year == year]
        for entry in entries:
            crop = self.crops.get(entry.crop_name)
            fld = self.fields.get(entry.field_name)
            if not crop or not fld:
                continue
            npk = crop.npk_per_mu
            field_npk = {k: v * fld.area for k, v in npk.items()}
            for k in totals:
                totals[k] += field_npk.get(k, 0)
            details.append({
                "field": entry.field_name,
                "year": entry.year,
                "season": entry.season,
                "crop": entry.crop_name,
                "area": fld.area,
                "N": field_npk.get("N", 0),
                "P": field_npk.get("P", 0),
                "K": field_npk.get("K", 0),
            })
        return totals, details

    def export_plan_csv(self, filepath="planting_plan.csv", year=None):
        years = [year] if year else self.plan_years
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["年份", "农田", "面积(亩)", "土壤类型", "排水评分",
                             "春季作物", "夏季作物", "秋季作物", "冬季作物"])
            for y in years:
                for fname, fld in self.fields.items():
                    row = [y, fname, fld.area, fld.soil_type, fld.drainage_score]
                    for s in SEASON_ORDER:
                        crop_name = ""
                        for e in self.plan:
                            if e.field_name == fname and e.year == y and e.season == s:
                                crop_name = e.crop_name
                                break
                        row.append(crop_name)
                    writer.writerow(row)
        return filepath

    def set_budget_target(self, year, budget=None, target_profit=None):
        if year not in self.budget_targets:
            self.budget_targets[year] = {"budget": None, "target_profit": None}
        if budget is not None:
            self.budget_targets[year]["budget"] = budget
        if target_profit is not None:
            self.budget_targets[year]["target_profit"] = target_profit
        self._save()
        return self.budget_targets[year]

    def get_budget_target(self, year):
        return self.budget_targets.get(year, {"budget": None, "target_profit": None})

    def get_plan_table(self):
        table = {}
        for y in self.plan_years:
            table[y] = {}
            for fname in self.fields:
                table[y][fname] = {}
                for s in SEASON_ORDER:
                    crop_name = ""
                    for e in self.plan:
                        if e.field_name == fname and e.year == y and e.season == s:
                            crop_name = e.crop_name
                            break
                    table[y][fname][s] = crop_name
        return table

    def update_plan_cell(self, field_name, year, season, crop_name):
        if not crop_name or crop_name.strip() == "":
            self.plan = [e for e in self.plan
                         if not (e.field_name == field_name and e.year == year and e.season == season)]
            self._save()
            return True, "已清空"
        return self.add_plan_entry(field_name, year, season, crop_name.strip())

    def copy_field_plan(self, from_year, to_year, field_name=None):
        if from_year not in self.plan_years or to_year not in self.plan_years:
            return 0, "年份不在规划期内"
        count = 0
        entries_to_copy = [e for e in self.plan if e.year == from_year]
        if field_name is not None:
            entries_to_copy = [e for e in entries_to_copy if e.field_name == field_name]
        for e in entries_to_copy:
            crop = self.crops.get(e.crop_name)
            if crop and e.season in crop.seasons:
                entry, err = self.add_plan_entry(e.field_name, to_year, e.season, e.crop_name)
                if entry:
                    count += 1
        return count, f"已复制 {count} 条计划"

    def batch_replace_crop(self, old_crop, new_crop, field_name=None, years=None):
        if old_crop not in self.crops:
            return 0, f"作物 '{old_crop}' 不存在"
        if new_crop not in self.crops:
            return 0, f"作物 '{new_crop}' 不存在"
        if years is None:
            years = self.plan_years
        count = 0
        for e in list(self.plan):
            if e.crop_name != old_crop:
                continue
            if field_name is not None and e.field_name != field_name:
                continue
            if e.year not in years:
                continue
            if e.season not in self.crops[new_crop].seasons:
                continue
            entry, err = self.add_plan_entry(e.field_name, e.year, e.season, new_crop)
            if entry:
                count += 1
        return count, f"已替换 {count} 条计划"

    def batch_clear_season(self, field_name, season, years=None):
        if years is None:
            years = self.plan_years
        count = 0
        for e in list(self.plan):
            if e.field_name != field_name or e.season != season:
                continue
            if e.year not in years:
                continue
            self.plan.remove(e)
            count += 1
        if count > 0:
            self._save()
        return count, f"已清空 {count} 条计划"

    def save_scenario(self, name):
        scenario = {
            "plan": json.loads(json.dumps([e.to_dict() for e in self.plan])),
            "budget_targets": json.loads(json.dumps({str(k): v for k, v in self.budget_targets.items()})),
            "created_at": None,
        }
        self.scenarios[name] = scenario
        self._save()
        return True

    def load_scenario(self, name):
        if name not in self.scenarios:
            return False, f"方案 '{name}' 不存在"
        sc = self.scenarios[name]
        self.plan = [PlantingEntry.from_dict(d) for d in sc.get("plan", [])]
        raw_bt = sc.get("budget_targets", {})
        self.budget_targets = {int(k): v for k, v in raw_bt.items()}
        self._save()
        return True, f"已加载方案 '{name}'"

    def delete_scenario(self, name):
        if name not in self.scenarios:
            return False
        del self.scenarios[name]
        self._save()
        return True

    def compare_scenarios(self, scenario_names=None, year=None):
        if scenario_names is None:
            scenario_names = list(self.scenarios.keys())
        if not scenario_names:
            return {}

        current_plan = list(self.plan)
        current_budget = dict(self.budget_targets)
        results = {}

        for name in scenario_names:
            if name != "__current__" and name in self.scenarios:
                sc = self.scenarios[name]
                self.plan = [PlantingEntry.from_dict(d) for d in sc.get("plan", [])]
                raw_bt = sc.get("budget_targets", {})
                self.budget_targets = {int(k): v for k, v in raw_bt.items()}
            elif name != "__current__":
                continue

            if year is None:
                years = self.plan_years
            else:
                years = [year]

            total_yield = 0.0
            total_revenue = 0.0
            total_cost = 0.0
            for y in years:
                for s in SEASON_ORDER:
                    yh, _ = self.predict_season_harvest(y, s)
                    total_yield += yh
                    rev, _ = self.estimate_income(y, s)
                    total_revenue += rev
                    c, _, _ = self.calculate_season_costs(y, s)
                    total_cost += c
            total_profit = total_revenue - total_cost
            conflicts = self.check_rotation_conflicts(year=year)

            results[name] = {
                "total_yield_kg": total_yield,
                "total_revenue": total_revenue,
                "total_cost": total_cost,
                "total_profit": total_profit,
                "conflict_count": len(conflicts),
                "plan_count": len(self.plan),
            }

            if year is not None:
                bt = self.get_budget_target(year)
                results[name]["budget"] = bt.get("budget")
                results[name]["target_profit"] = bt.get("target_profit")

        self.plan = current_plan
        self.budget_targets = current_budget
        return results

    def get_decision_suggestions(self):
        suggestions = []

        for fname in self.fields:
            trend = self.deviation_trend_by_field(fname)
            if len(trend) >= 2:
                low_years = [t for t in trend if t["deviation_pct"] < -5]
                if len(low_years) >= 2:
                    affected_entries = [(e.year, e.season.value, e.crop_name)
                                        for e in self.plan if e.field_name == fname]
                    suggestions.append({
                        "type": "field_low",
                        "target": fname,
                        "priority": "中",
                        "title": f"{fname} 连续{len(low_years)}年偏低",
                        "detail": f"近{len(trend)}年偏差: " + ", ".join(
                            f"{t['year']}年{t['deviation_pct']:+.1f}%" for t in trend),
                        "actions": [
                            f"建议降低 {fname} 的高风险作物种植面积",
                            f"可考虑换茬或调整 {fname} 在以下季节的作物: " +
                            ", ".join(f"{y}年{s}({c})" for y, s, c in affected_entries[:3]),
                        ],
                    })

        for crop_name in self.crops:
            trend = self.deviation_trend_by_crop(crop_name)
            if len(trend) >= 2:
                low_years = [t for t in trend if t["deviation_pct"] < -5]
                if len(low_years) >= 2:
                    affected = [(e.year, e.season.value, e.field_name)
                                for e in self.plan if e.crop_name == crop_name]
                    suggestions.append({
                        "type": "crop_low",
                        "target": crop_name,
                        "priority": "中",
                        "title": f"{crop_name} 连续{len(low_years)}年偏低",
                        "detail": f"近{len(trend)}年偏差: " + ", ".join(
                            f"{t['year']}年{t['deviation_pct']:+.1f}%" for t in trend),
                        "actions": [
                            f"建议减少 {crop_name} 的种植面积",
                            f"可考虑替换为更高产的作物",
                            f"{crop_name} 当前分布: " +
                            ", ".join(f"{y}年{s}({f})" for y, s, f in affected[:3]),
                        ],
                    })
        return suggestions

    def budget_analysis(self, year):
        target = self.get_budget_target(year)
        profit_data = self.profit_analysis(year)[year]
        result = {
            "year": year,
            "total_revenue": profit_data["total_revenue"],
            "total_cost": profit_data["total_cost"],
            "total_profit": profit_data["total_profit"],
            "budget": target.get("budget"),
            "target_profit": target.get("target_profit"),
            "budget_status": None,
            "target_status": None,
        }
        if target.get("budget") is not None:
            over = profit_data["total_cost"] - target["budget"]
            result["budget_status"] = {
                "over_amount": over,
                "over_pct": (over / target["budget"] * 100) if target["budget"] > 0 else 0,
                "is_over": over > 0,
            }
        if target.get("target_profit") is not None:
            gap = target["target_profit"] - profit_data["total_profit"]
            result["target_status"] = {
                "gap_amount": gap,
                "gap_pct": (gap / target["target_profit"] * 100) if target["target_profit"] > 0 else 0,
                "is_met": gap <= 0,
            }
        return result

    def optimization_suggestions(self, year):
        suggestions = []
        ba = self.budget_analysis(year)

        if ba.get("budget_status") and ba["budget_status"].get("is_over"):
            s_budget = {
                "type": "budget",
                "priority": "高",
                "title": "预算超支警告",
                "detail": f"当前计划成本¥{ba['total_cost']:,.0f}，超出预算¥{ba['budget_status']['over_amount']:,.0f} ({ba['budget_status']['over_pct']:+.1f}%)",
                "actions": [],
            }

            cost_details = []
            for s in SEASON_ORDER:
                _, bd, _ = self.calculate_season_costs(year, s)
                for k, v in bd.items():
                    cost_details.append((f"{s.value}-{k}", v))
            cost_details.sort(key=lambda x: x[1], reverse=True)
            if cost_details:
                top = cost_details[0]
                s_budget["actions"].append(
                    f"最大支出来源: {top[0]} (¥{top[1]:,.0f})，考虑缩减高成本作物")

            for fname, fld in self.fields.items():
                for s in SEASON_ORDER:
                    for e in self.plan:
                        if e.field_name == fname and e.year == year and e.season == s:
                            crop = self.crops.get(e.crop_name)
                            if crop:
                                c = self.costs.get(e.crop_name, {})
                                seed = c.get("seed_per_mu", 0) * fld.area
                                if seed > 1000:
                                    s_budget["actions"].append(
                                        f"{fname} {s.value} {e.crop_name} 种子成本较高(¥{seed:,.0f})，可考虑换低成本品种")
            suggestions.append(s_budget)

        if ba.get("target_status") and not ba["target_status"]["is_met"]:
            s_target = {
                "type": "target",
                "priority": "中",
                "title": "未达目标收益",
                "detail": f"当前净收益¥{ba['total_profit']:,.0f}，距目标还差¥{ba['target_status']['gap_amount']:,.0f}",
                "actions": [],
            }
            profit_data = self.profit_analysis(year)[year]
            season_profits = [(s.value, profit_data["seasons"][s]["profit"]) for s in SEASON_ORDER]
            season_profits.sort(key=lambda x: x[1])
            if season_profits and season_profits[0][1] < 0:
                s_target["actions"].append(
                    f"{season_profits[0][0]}亏损¥{abs(season_profits[0][1]):,.0f}，可考虑调整作物")

            crop_profits = {}
            for e in self.plan:
                if e.year != year:
                    continue
                crop = self.crops.get(e.crop_name)
                fld = self.fields.get(e.field_name)
                if crop and fld:
                    yv = self.predict_yield(e.field_name, year, e.season, e.crop_name)
                    rev = yv * self.prices.get(e.crop_name, 0)
                    c = self.costs.get(e.crop_name, {})
                    sc = c.get("seed_per_mu", 0) * fld.area
                    ic = c.get("irrigation_per_mu", 0) * fld.area
                    lc = c.get("labor_per_mu", 0) * fld.area
                    fc = sum(crop.npk_per_mu.get(k, 0) * self.fertilizer_prices.get(k, 0) * fld.area
                             for k in ["N", "P", "K"])
                    total_c = sc + fc + ic + lc
                    p = rev - total_c
                    key = f"{e.field_name} {e.season.value} {e.crop_name}"
                    crop_profits[key] = p
            low_profit = sorted(crop_profits.items(), key=lambda x: x[1])[:2]
            for key, p in low_profit:
                if p < 500:
                    s_target["actions"].append(f"{key} 收益较低(¥{p:,.0f})，可考虑换高收益作物")
            suggestions.append(s_target)

        rotation_conflicts = self.check_rotation_conflicts(year=year)
        if rotation_conflicts:
            suggestions.append({
                "type": "rotation",
                "priority": "低",
                "title": "轮作优化建议",
                "detail": f"发现 {len(rotation_conflicts)} 处轮作冲突，建议调整避免减产",
                "actions": [f"{cf['field']} {cf['prev_year']}年{cf['prev_season'].value}→{cf['curr_year']}年{cf['curr_season'].value} 连续{cf['crop']}" for cf in rotation_conflicts],
            })

        return suggestions

    def deviation_trend_by_field(self, field_name):
        reports = self.deviation_analysis()
        field_reports = [r for r in reports if r["field"] == field_name]
        if not field_reports:
            return []
        by_year = {}
        for r in field_reports:
            y = r["year"]
            if y not in by_year:
                by_year[y] = {"count": 0, "predicted": 0.0, "actual": 0.0}
            by_year[y]["count"] += 1
            by_year[y]["predicted"] += r["predicted_kg"]
            by_year[y]["actual"] += r["actual_kg"]
        result = []
        for y in sorted(by_year.keys()):
            d = by_year[y]
            dev = d["actual"] - d["predicted"]
            dev_pct = (dev / d["predicted"] * 100) if d["predicted"] > 0 else 0
            result.append({
                "year": y,
                "count": d["count"],
                "predicted": d["predicted"],
                "actual": d["actual"],
                "deviation": dev,
                "deviation_pct": dev_pct,
            })
        return result

    def deviation_trend_by_crop(self, crop_name):
        reports = self.deviation_analysis()
        crop_reports = [r for r in reports if r["crop"] == crop_name]
        if not crop_reports:
            return []
        by_year = {}
        for r in crop_reports:
            y = r["year"]
            if y not in by_year:
                by_year[y] = {"count": 0, "predicted": 0.0, "actual": 0.0}
            by_year[y]["count"] += 1
            by_year[y]["predicted"] += r["predicted_kg"]
            by_year[y]["actual"] += r["actual_kg"]
        result = []
        for y in sorted(by_year.keys()):
            d = by_year[y]
            dev = d["actual"] - d["predicted"]
            dev_pct = (dev / d["predicted"] * 100) if d["predicted"] > 0 else 0
            result.append({
                "year": y,
                "count": d["count"],
                "predicted": d["predicted"],
                "actual": d["actual"],
                "deviation": dev,
                "deviation_pct": dev_pct,
            })
        return result

    def generate_calendar(self, year=None):
        years = [year] if year else self.plan_years
        if not self.fields:
            print("\n  尚未添加任何农田\n")
            return
        if not years:
            print("\n  暂无规划年份\n")
            return

        plan_map = {}
        for entry in self.plan:
            plan_map[(entry.field_name, entry.year, entry.season)] = entry.crop_name

        crop_symbols = {"小麦": "麦", "玉米": "玉", "水稻": "稻", "大豆": "豆", "土豆": "薯"}
        used_crops = set()
        for e in self.plan:
            if e.year in years:
                used_crops.add(e.crop_name)
        extra = [c for c in used_crops if c not in crop_symbols]
        for c in extra:
            crop_symbols[c] = c[0]

        field_names = list(self.fields.keys())
        name_width = max(len(n) for n in field_names) + 2
        name_width = max(name_width, 6)
        cell_width = 10
        total_width = name_width + cell_width * 4 + 3

        for y in years:
            print()
            print("┌" + "─" * (total_width - 2) + "┐")
            title = f"{y}年 田块种植日历"
            pad = total_width - 2 - len(title) * 2
            left_pad = pad // 2
            right_pad = pad - left_pad
            print("│" + " " * left_pad + title + " " * right_pad + "│")
            print("├" + "─" * name_width + "┼" + "─" * cell_width + "┼" +
                  "─" * cell_width + "┼" + "─" * cell_width + "┼" + "─" * cell_width + "┤")

            header = "│" + "农田".ljust(name_width)
            for s in SEASON_ORDER:
                header += "│" + s.value.center(cell_width)
            header += "│"
            print(header)

            print("├" + "─" * name_width + "┼" + "─" * cell_width + "┼" +
                  "─" * cell_width + "┼" + "─" * cell_width + "┼" + "─" * cell_width + "┤")

            for fname in field_names:
                row = "│" + fname.ljust(name_width)
                for s in SEASON_ORDER:
                    crop_name = plan_map.get((fname, y, s), "")
                    if crop_name:
                        sym = crop_symbols.get(crop_name, crop_name[0])
                        display = f"{sym}·{crop_name}"
                    else:
                        display = "—"
                    row += "│" + display.center(cell_width)
                row += "│"
                print(row)
                print("├" + "─" * name_width + "┼" + "─" * cell_width + "┼" +
                      "─" * cell_width + "┼" + "─" * cell_width + "┼" + "─" * cell_width + "┤")

            legend_parts = []
            for cn, sym in crop_symbols.items():
                if cn in used_crops:
                    legend_parts.append(f"{sym}={cn}")
            legend = " ".join(legend_parts)
            remaining = cell_width * 4 + 3
            legend_line = "│" + "图例:".ljust(name_width) + "│" + legend[:remaining].ljust(remaining) + "│"
            print(legend_line)
            print("└" + "─" * name_width + "┴" + "─" * cell_width + "┴" +
                  "─" * cell_width + "┴" + "─" * cell_width + "┴" + "─" * cell_width + "┘")

        if year is not None and year > min(self.plan_years):
            cross_info = self.get_cross_year_info(year)
            if cross_info:
                print("\n  🔗 跨年衔接 (与上一年冬季):")
                for ci in cross_info:
                    prev_label = f"{ci['prev_year']}年{ci['prev_season'].value}"
                    curr_label = f"{ci['curr_year']}年{ci['curr_season'].value}"
                    if ci["curr_crop"]:
                        if ci["is_conflict"]:
                            print(f"    - {ci['field']}: {prev_label}({ci['prev_crop']})→{curr_label}({ci['curr_crop']}) 连续种植 ⚠ 减产{ci['penalty']*100:.0f}%")
                        else:
                            print(f"    - {ci['field']}: {prev_label}({ci['prev_crop']})→{curr_label}({ci['curr_crop']}) 正常轮作 ✓")
                    else:
                        print(f"    - {ci['field']}: {prev_label}({ci['prev_crop']})→{curr_label}(空置)")

        conflicts = self.check_rotation_conflicts(year=year)
        same_year = [cf for cf in conflicts if cf["prev_year"] == cf["curr_year"]]
        if same_year:
            print("\n  ⚠ 年轮作冲突警告:")
            for cf in same_year:
                prev_label = f"{cf['prev_year']}年{cf['prev_season'].value}"
                curr_label = f"{cf['curr_year']}年{cf['curr_season'].value}"
                print(f"    - {cf['field']}: {prev_label}→{curr_label} "
                      f"连续种植{cf['crop']}，减产{cf['penalty']*100:.0f}%")
        print()


def print_separator(char="─", length=60):
    print(f"  {char * length}")


def input_float(prompt, default=None, allow_empty=False):
    while True:
        val = input(prompt).strip()
        if not val:
            if allow_empty:
                return None
            if default is not None:
                return default
            print("  请输入有效的数字")
            continue
        try:
            return float(val)
        except ValueError:
            print("  请输入有效的数字")


def input_int(prompt, default=None, allow_empty=False):
    while True:
        val = input(prompt).strip()
        if not val:
            if allow_empty:
                return None
            if default is not None:
                return default
            print("  请输入有效的整数")
            continue
        try:
            return int(val)
        except ValueError:
            print("  请输入有效的整数")


def select_from_list(options, prompt="请选择"):
    for i, opt in enumerate(options, 1):
        print(f"    {i}. {opt}")
    while True:
        choice = input(f"  {prompt} (1-{len(options)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return int(choice) - 1
        print("  无效选择，请重试")


class CLI:
    def __init__(self):
        self.mgr = FarmManager()

    def run(self):
        while True:
            self._main_menu()

    def _select_year(self, prompt="选择年份", allow_all=False):
        if not self.mgr.plan_years:
            print("  暂无规划年份，请先设置规划年限")
            return None
        year_strs = [str(y) for y in self.mgr.plan_years]
        if allow_all:
            year_strs = ["(全部年份)"] + year_strs
        i = select_from_list(year_strs, prompt)
        if allow_all and i == 0:
            return 0
        return self.mgr.plan_years[i - 1 if allow_all else i]

    def _main_menu(self):
        print()
        print_separator()
        print(f"  🌾 农场种植计划与收成预测工具  (规划年份: {min(self.mgr.plan_years)}-{max(self.mgr.plan_years)})")
        print_separator()
        print("  1.  管理作物")
        print("  2.  管理农田")
        print("  3.  制定种植计划")
        print("  4.  收成预测与收入估算")
        print("  5.  经营分析 (成本/收益)")
        print("  6.  记录实际收成")
        print("  7.  偏差分析报告")
        print("  8.  自然灾害模拟")
        print("  9.  肥料采购建议")
        print("  10. 导出种植计划 (CSV)")
        print("  11. 查看田块种植日历")
        print("  12. 配置价格与成本")
        print("  13. 设置规划年限")
        print("  14. 多年度表格排期")
        print("  15. 经营决策工具 (预算/目标/建议)")
        print("  16. 偏差趋势分析 (按年份)")
        print("  17. 种植方案版本管理与对比")
        print("  0.  退出")
        print_separator()
        choice = input("  请选择功能: ").strip()
        actions = {
            "1": self._manage_crops,
            "2": self._manage_fields,
            "3": self._manage_plan,
            "4": self._predict_harvest,
            "5": self._profit_analysis,
            "6": self._record_harvest,
            "7": self._deviation_report,
            "8": self._disaster_sim,
            "9": self._fertilizer_advice,
            "10": self._export_csv,
            "11": self._view_calendar,
            "12": self._configure_prices_costs,
            "13": self._configure_years,
            "14": self._multi_year_table,
            "15": self._business_decision,
            "16": self._deviation_trend,
            "17": self._scenario_manager,
            "0": self._exit,
        }
        action = actions.get(choice)
        if action:
            action()
        else:
            print("  无效选择")

    def _manage_crops(self):
        print("\n  === 作物管理 ===")
        print("  当前作物列表:")
        for name, crop in self.mgr.crops.items():
            seasons_str = "、".join(s.value for s in crop.seasons)
            print(f"    {name}: 种植季={seasons_str}, 周期={crop.growth_days}天, "
                  f"亩产={crop.yield_per_mu}kg, 水需求={crop.water_need}, "
                  f"肥需求={crop.fertilizer_need}")
            print(f"      推荐施肥(每亩): N={crop.npk_per_mu['N']}kg, "
                  f"P={crop.npk_per_mu['P']}kg, K={crop.npk_per_mu['K']}kg")
        print("\n  1. 添加作物  2. 返回")
        c = input("  选择: ").strip()
        if c == "1":
            name = input("  作物名称: ").strip()
            if name in self.mgr.crops:
                print("  该作物已存在")
                return
            print("  选择适宜种植季节 (可多选，用逗号分隔):")
            for i, s in enumerate(SEASON_ORDER, 1):
                print(f"    {i}. {s.value}")
            season_input = input("  选择: ").strip()
            seasons = []
            for idx in season_input.split(","):
                idx = idx.strip()
                if idx.isdigit() and 1 <= int(idx) <= 4:
                    seasons.append(SEASON_ORDER[int(idx) - 1])
            if not seasons:
                print("  未选择有效季节")
                return
            growth_days = input_int("  生长周期(天): ")
            yield_per_mu = input_float("  预期亩产(kg): ")
            water_opts = ["较低", "中等", "较高", "极高"]
            print("  水肥需求等级:")
            wi = select_from_list(water_opts, "水需求")
            fi = select_from_list(water_opts, "肥需求")
            print("  推荐施肥量(每亩, kg):")
            n = input_float("  氮(N): ")
            p = input_float("  磷(P): ")
            k = input_float("  钾(K): ")
            self.mgr.add_crop(name, seasons, growth_days, yield_per_mu,
                              water_opts[wi], water_opts[fi],
                              {"N": n, "P": p, "K": k})
            print(f"  ✓ 作物 '{name}' 已添加")

    def _manage_fields(self):
        print("\n  === 农田管理 ===")
        if self.mgr.fields:
            print("  当前农田列表:")
            for name, fld in self.mgr.fields.items():
                print(f"    {name}: 面积={fld.area}亩, 土壤={fld.soil_type}, "
                      f"排水评分={fld.drainage_score}/10")
        else:
            print("  尚未添加农田")
        print("\n  1. 添加农田  2. 删除农田  3. 返回")
        c = input("  选择: ").strip()
        if c == "1":
            name = input("  农田名称: ").strip()
            if name in self.mgr.fields:
                print("  该农田已存在")
                return
            area = input_float("  面积(亩): ")
            soil_opts = ["沙土", "黏土", "壤土"]
            si = select_from_list(soil_opts, "土壤类型")
            drainage = input_int("  排水评分(1-10): ")
            drainage = max(1, min(10, drainage))
            self.mgr.add_field(name, area, soil_opts[si], drainage)
            print(f"  ✓ 农田 '{name}' 已添加")
        elif c == "2":
            names = list(self.mgr.fields.keys())
            if not names:
                print("  没有可删除的农田")
                return
            for i, n in enumerate(names, 1):
                print(f"    {i}. {n}")
            idx = input("  选择要删除的农田编号: ").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(names):
                fname = names[int(idx) - 1]
                self.mgr.plan = [e for e in self.mgr.plan if e.field_name != fname]
                self.mgr.actual_harvests = [h for h in self.mgr.actual_harvests
                                            if h.field_name != fname]
                self.mgr.disaster_records = [d for d in self.mgr.disaster_records
                                             if fname not in d.field_names]
                del self.mgr.fields[fname]
                self.mgr._save()
                print(f"  ✓ 农田 '{fname}' 已删除")

    def _manage_plan(self):
        print("\n  === 种植计划管理 ===")
        if not self.mgr.fields:
            print("  请先添加农田")
            return
        if not self.mgr.crops:
            print("  请先添加作物")
            return

        print("  当前种植计划:")
        if self.mgr.plan:
            for entry in sorted(self.mgr.plan,
                                key=lambda e: (e.year, SEASON_ORDER.index(e.season), e.field_name)):
                print(f"    {entry.year}年 {entry.season.value} - {entry.field_name} - {entry.crop_name}")
        else:
            print("    (空)")

        years = sorted(set([e.year for e in self.mgr.plan]))
        for y in years:
            if y - 1 not in self.mgr.plan_years and y - 1 not in years:
                continue
            cinfo = self.mgr.get_cross_year_info(y)
            if cinfo:
                labels = []
                for ci in cinfo:
                    if ci["is_conflict"]:
                        labels.append(f"⚠ {ci['field']}({ci['prev_crop']}→{ci['curr_crop']})")
                    elif ci["curr_crop"]:
                        labels.append(f"✓ {ci['field']}({ci['prev_crop']}→{ci['curr_crop']})")
                    else:
                        labels.append(f"  {ci['field']}({ci['prev_crop']}→空置)")
                if labels:
                    print(f"\n  🔗 {y-1}冬→{y}春衔接: " + "  ".join(labels))

        conflicts = self.mgr.check_rotation_conflicts()
        same_year = [cf for cf in conflicts if cf["prev_year"] == cf["curr_year"]]
        if same_year:
            print("\n  ⚠ 年轮作冲突:")
            for cf in same_year:
                prev_label = f"{cf['prev_year']}年{cf['prev_season'].value}"
                curr_label = f"{cf['curr_year']}年{cf['curr_season'].value}"
                print(f"    {cf['field']}: {prev_label}→{curr_label} "
                      f"连续种植{cf['crop']}，减产{cf['penalty']*100:.0f}%")

        print("\n  1. 添加/修改计划条目  2. 删除计划条目  3. 快速批量规划  4. 返回")
        c = input("  选择: ").strip()
        if c == "1":
            year = self._select_year("选择年份")
            if year is None:
                return
            fnames = list(self.mgr.fields.keys())
            for i, n in enumerate(fnames, 1):
                print(f"    {i}. {n} ({self.mgr.fields[n].area}亩)")
            fi = input("  选择农田编号: ").strip()
            if not (fi.isdigit() and 1 <= int(fi) <= len(fnames)):
                print("  无效选择")
                return
            fname = fnames[int(fi) - 1]

            season_labels = [s.value for s in SEASON_ORDER]
            si = select_from_list(season_labels, "选择季节")

            cnames = list(self.mgr.crops.keys())
            suitable = [cn for cn in cnames if SEASON_ORDER[si] in self.mgr.crops[cn].seasons]
            if not suitable:
                print(f"  没有作物适合在{SEASON_ORDER[si].value}种植")
                return
            print(f"  {SEASON_ORDER[si].value}适宜作物:")
            for i, cn in enumerate(suitable, 1):
                crop = self.mgr.crops[cn]
                print(f"    {i}. {cn} (亩产{crop.yield_per_mu}kg, 周期{crop.growth_days}天)")
            ci = input("  选择作物编号: ").strip()
            if not (ci.isdigit() and 1 <= int(ci) <= len(suitable)):
                print("  无效选择")
                return
            entry, err = self.mgr.add_plan_entry(fname, year, SEASON_ORDER[si], suitable[int(ci) - 1])
            if err:
                print(f"  ✗ {err}")
            else:
                print(f"  ✓ 已规划: {year}年 {SEASON_ORDER[si].value} - {fname} - {suitable[int(ci)-1]}")

        elif c == "2":
            if not self.mgr.plan:
                print("  没有可删除的计划条目")
                return
            entries = sorted(self.mgr.plan,
                             key=lambda e: (e.year, SEASON_ORDER.index(e.season), e.field_name))
            for i, e in enumerate(entries, 1):
                print(f"    {i}. {e.year}年 {e.season.value} - {e.field_name} - {e.crop_name}")
            idx = input("  选择要删除的编号: ").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(entries):
                removed = entries.pop(int(idx) - 1)
                self.mgr.plan.remove(removed)
                self.mgr._save()
                print(f"  ✓ 已删除: {removed.year}年 {removed.season.value} - "
                      f"{removed.field_name} - {removed.crop_name}")

        elif c == "3":
            print("  快速批量规划: 为所有未分配的农田-季节组合分配作物")
            count = 0
            for y in self.mgr.plan_years:
                for fname in self.mgr.fields:
                    for s in SEASON_ORDER:
                        existing = [e for e in self.mgr.plan
                                    if e.field_name == fname and e.year == y and e.season == s]
                        if existing:
                            continue
                        suitable = [cn for cn in self.mgr.crops if s in self.mgr.crops[cn].seasons]
                        if not suitable:
                            continue
                        chosen = random.choice(suitable)
                        self.mgr.add_plan_entry(fname, y, s, chosen)
                        count += 1
            print(f"  ✓ 已自动规划 {count} 个条目")

    def _predict_harvest(self):
        print("\n  === 收成预测与收入估算 ===")
        print("  1. 按季节预测  2. 全年预测  3. 多年度总览  4. 返回")
        c = input("  选择: ").strip()
        if c == "1":
            year = self._select_year("选择年份")
            if year is None:
                return
            season_labels = [s.value for s in SEASON_ORDER]
            si = select_from_list(season_labels, "选择季节")
            season = SEASON_ORDER[si]
            total, details = self.mgr.predict_season_harvest(year, season)
            income, income_details = self.mgr.estimate_income(year, season)
            print(f"\n  {year}年 {season.value}收成预测:")
            if not details:
                print("    (无种植计划)")
            for d in details:
                print(f"    {d['field']}: {d['crop']} - 预计 {d['predicted_kg']:.1f}kg "
                      f"({d['predicted_kg']/1000:.2f}吨)")
            print(f"\n  {year}年 {season.value}预计总产量: {total:.1f}kg ({total/1000:.2f}吨)")
            print(f"  {year}年 {season.value}预计总收入: ¥{income:,.2f}")
            for id_ in income_details:
                print(f"    {id_['field']}({id_['crop']}): "
                      f"{id_['predicted_kg']:.1f}kg × ¥{id_['price_per_kg']:.2f}/kg "
                      f"= ¥{id_['income']:,.2f}")

        elif c == "2":
            year = self._select_year("选择年份")
            if year is None:
                return
            annual = self.mgr.predict_annual_harvest(year)
            annual_income = self.mgr.estimate_annual_income(year)
            total_all = 0.0
            total_income_all = 0.0
            print(f"\n  {year}年全年收成预测:")
            for s in SEASON_ORDER:
                data = annual[s]
                inc_data = annual_income[s]
                total_all += data["total_kg"]
                total_income_all += inc_data["total_income"]
                print(f"\n  【{s.value}】")
                print(f"    预计产量: {data['total_kg']:.1f}kg ({data['total_kg']/1000:.2f}吨)")
                print(f"    预计收入: ¥{inc_data['total_income']:,.2f}")
                for d in data["details"]:
                    print(f"      {d['field']}: {d['crop']} - {d['predicted_kg']:.1f}kg")
            print(f"\n  {year}年全年预计总产量: {total_all:.1f}kg ({total_all/1000:.2f}吨)")
            print(f"  {year}年全年预计总收入: ¥{total_income_all:,.2f}")

        elif c == "3":
            print(f"\n  多年度收成总览 ({min(self.mgr.plan_years)}-{max(self.mgr.plan_years)}年):")
            grand_total = 0.0
            grand_income = 0.0
            for y in self.mgr.plan_years:
                annual = self.mgr.predict_annual_harvest(y)
                annual_income = self.mgr.estimate_annual_income(y)
                y_total = sum(annual[s]["total_kg"] for s in SEASON_ORDER)
                y_income = sum(annual_income[s]["total_income"] for s in SEASON_ORDER)
                grand_total += y_total
                grand_income += y_income
                print(f"    {y}年: 产量={y_total:.1f}kg ({y_total/1000:.2f}吨), "
                      f"收入=¥{y_income:,.2f}")
            print(f"\n  合计: 产量={grand_total:.1f}kg ({grand_total/1000:.2f}吨), "
                  f"收入=¥{grand_income:,.2f}")

    def _profit_analysis(self):
        print("\n  === 经营分析 (成本/收益) ===")
        print("  1. 按季节分析  2. 全年分析  3. 多年度对比  4. 返回")
        c = input("  选择: ").strip()

        if c == "1":
            year = self._select_year("选择年份")
            if year is None:
                return
            season_labels = [s.value for s in SEASON_ORDER]
            si = select_from_list(season_labels, "选择季节")
            season = SEASON_ORDER[si]
            revenue, rev_details = self.mgr.estimate_income(year, season)
            total_cost, cost_bd, cost_details = self.mgr.calculate_season_costs(year, season)
            profit = revenue - total_cost
            print(f"\n  {year}年 {season.value}经营分析:")
            print(f"    毛收入: ¥{revenue:,.2f}")
            print(f"    总成本: ¥{total_cost:,.2f}")
            print(f"    净收益: ¥{profit:,.2f}")
            print(f"\n  成本构成:")
            print(f"    种子成本: ¥{cost_bd['seed']:,.2f}")
            print(f"    化肥成本: ¥{cost_bd['fertilizer']:,.2f}")
            print(f"    灌溉成本: ¥{cost_bd['irrigation']:,.2f}")
            print(f"    人工成本: ¥{cost_bd['labor']:,.2f}")
            if cost_details:
                print(f"\n  明细:")
                for d in cost_details:
                    print(f"    {d['field']}({d['crop']}): 种子¥{d['seed_cost']:,.0f} + "
                          f"化肥¥{d['fertilizer_cost']:,.0f} + 灌溉¥{d['irrigation_cost']:,.0f} + "
                          f"人工¥{d['labor_cost']:,.0f} = 合计¥{d['total_cost']:,.0f}")

        elif c == "2":
            year = self._select_year("选择年份")
            if year is None:
                return
            data = self.mgr.profit_analysis(year)[year]
            print(f"\n  {year}年全年经营分析:")
            print(f"    毛收入: ¥{data['total_revenue']:,.2f}")
            print(f"    总成本: ¥{data['total_cost']:,.2f}")
            print(f"    净收益: ¥{data['total_profit']:,.2f}")
            print(f"\n  分季节情况:")
            for s in SEASON_ORDER:
                sd = data["seasons"][s]
                print(f"    【{s.value}】 收入:¥{sd['revenue']:,.0f}  "
                      f"成本:¥{sd['cost']:,.0f}  净收益:¥{sd['profit']:,.0f}")

        elif c == "3":
            print(f"\n  多年度经营对比 ({min(self.mgr.plan_years)}-{max(self.mgr.plan_years)}年):")
            total_rev = total_cost = total_profit = 0.0
            for y in self.mgr.plan_years:
                d = self.mgr.profit_analysis(y)[y]
                total_rev += d["total_revenue"]
                total_cost += d["total_cost"]
                total_profit += d["total_profit"]
                print(f"    {y}年: 毛收入¥{d['total_revenue']:,.2f}  "
                      f"成本¥{d['total_cost']:,.2f}  净收益¥{d['total_profit']:,.2f}")
            print(f"\n  合计: 毛收入¥{total_rev:,.2f}  "
                  f"成本¥{total_cost:,.2f}  净收益¥{total_profit:,.2f}")

    def _record_harvest(self):
        print("\n  === 记录实际收成 ===")
        if not self.mgr.plan:
            print("  没有种植计划，无法记录收成")
            return
        entries = sorted(self.mgr.plan,
                         key=lambda e: (e.year, SEASON_ORDER.index(e.season), e.field_name))
        for i, e in enumerate(entries, 1):
            existing = [h for h in self.mgr.actual_harvests
                        if h.field_name == e.field_name and h.year == e.year and h.season == e.season]
            status = f" (已记录: {existing[0].actual_yield:.1f}kg)" if existing else ""
            print(f"    {i}. {e.year}年 {e.season.value} - {e.field_name} - {e.crop_name}{status}")
        idx = input("  选择编号: ").strip()
        if not (idx.isdigit() and 1 <= int(idx) <= len(entries)):
            print("  无效选择")
            return
        entry = entries[int(idx) - 1]
        predicted = self.mgr.predict_yield(entry.field_name, entry.year,
                                           entry.season, entry.crop_name)
        print(f"  预测产量: {predicted:.1f}kg")
        actual = input_float("  实际收成(kg): ")
        self.mgr.record_actual_harvest(entry.field_name, entry.year,
                                       entry.season, entry.crop_name, actual)
        dev = actual - predicted
        dev_pct = (dev / predicted * 100) if predicted > 0 else 0
        print(f"  ✓ 已记录: 实际={actual:.1f}kg, 偏差={dev:+.1f}kg ({dev_pct:+.1f}%)")

    def _deviation_report(self):
        print("\n  === 偏差分析报告 ===")
        print("  1. 明细列表  2. 按作物汇总  3. 按农田汇总  4. 返回")
        c = input("  选择: ").strip()

        if c == "1":
            print("  1. 按季节  2. 按年份  3. 全部")
            sub = input("  选择: ").strip()
            if sub == "1":
                year = self._select_year("选择年份")
                if year is None:
                    return
                season_labels = [s.value for s in SEASON_ORDER]
                si = select_from_list(season_labels, "选择季节")
                reports = self.mgr.deviation_analysis(year=year, season=SEASON_ORDER[si])
            elif sub == "2":
                year = self._select_year("选择年份")
                if year is None:
                    return
                reports = self.mgr.deviation_analysis(year=year)
            elif sub == "3":
                reports = self.mgr.deviation_analysis()
            else:
                return

            if not reports:
                print("  暂无实际收成记录可分析")
                return

            print(f"\n  {'年份':<6} {'季节':<6} {'农田':<10} {'作物':<6} "
                  f"{'预测(kg)':<12} {'实际(kg)':<12} {'偏差(kg)':<12} {'偏差%':<10}")
            print_separator("─", 88)
            total_pred = total_actual = 0.0
            for r in reports:
                print(f"  {r['year']:<6} {r['season'].value:<6} {r['field']:<10} "
                      f"{r['crop']:<6} {r['predicted_kg']:<12.1f} {r['actual_kg']:<12.1f} "
                      f"{r['deviation_kg']:<+12.1f} {r['deviation_pct']:<+10.1f}%")
                total_pred += r["predicted_kg"]
                total_actual += r["actual_kg"]
            if total_pred > 0:
                total_dev = total_actual - total_pred
                total_dev_pct = total_dev / total_pred * 100
                print_separator("─", 88)
                print(f"  {'合计':<6} {'':<6} {'':<10} {'':<6} "
                      f"{total_pred:<12.1f} {total_actual:<12.1f} "
                      f"{total_dev:<+12.1f} {total_dev_pct:<+10.1f}%")

        elif c == "2":
            print("  1. 单年汇总  2. 多年度汇总")
            sub = input("  选择: ").strip()
            if sub == "1":
                year = self._select_year("选择年份")
                if year is None:
                    return
                data = self.mgr.deviation_by_crop(year=year)
                title = f"{year}年"
            elif sub == "2":
                data = self.mgr.deviation_by_crop()
                title = f"{min(self.mgr.plan_years)}-{max(self.mgr.plan_years)}年"
            else:
                return

            if not data:
                print("  暂无数据")
                return

            print(f"\n  {title}按作物偏差汇总:")
            print(f"  {'作物':<8} {'次数':<6} {'预测合计(kg)':<14} {'实际合计(kg)':<14} "
                  f"{'偏差(kg)':<12} {'偏差%':<10} 趋势")
            print_separator("─", 86)
            for d in data:
                trend = "↗ 偏高" if d["deviation_pct"] > 0 else ("↘ 偏低" if d["deviation_pct"] < 0 else "— 持平")
                print(f"  {d['crop']:<8} {d['count']:<6} "
                      f"{d['total_predicted']:<14.1f} {d['total_actual']:<14.1f} "
                      f"{d['total_deviation']:<+12.1f} {d['deviation_pct']:<+10.1f}%  {trend}")

        elif c == "3":
            print("  1. 单年汇总  2. 多年度汇总")
            sub = input("  选择: ").strip()
            if sub == "1":
                year = self._select_year("选择年份")
                if year is None:
                    return
                data = self.mgr.deviation_by_field(year=year)
                title = f"{year}年"
            elif sub == "2":
                data = self.mgr.deviation_by_field()
                title = f"{min(self.mgr.plan_years)}-{max(self.mgr.plan_years)}年"
            else:
                return

            if not data:
                print("  暂无数据")
                return

            print(f"\n  {title}按农田偏差汇总:")
            print(f"  {'农田':<12} {'次数':<6} {'预测合计(kg)':<14} {'实际合计(kg)':<14} "
                  f"{'偏差(kg)':<12} {'偏差%':<10} 趋势")
            print_separator("─", 86)
            for d in data:
                trend = "↗ 长期偏高" if d["deviation_pct"] > 5 else (
                    "↘ 长期偏低" if d["deviation_pct"] < -5 else "— 正常")
                print(f"  {d['field']:<12} {d['count']:<6} "
                      f"{d['total_predicted']:<14.1f} {d['total_actual']:<14.1f} "
                      f"{d['total_deviation']:<+12.1f} {d['deviation_pct']:<+10.1f}%  {trend}")

    def _disaster_sim(self):
        print("\n  === 自然灾害模拟 ===")
        if self.mgr.disaster_records:
            print("  当前灾害记录:")
            for dr in self.mgr.disaster_records:
                fields_str = "、".join(dr.field_names)
                print(f"    {dr.disaster_type} ({dr.year}年{dr.season.value}): "
                      f"影响农田={fields_str}, 严重度={dr.severity*100:.0f}%, "
                      f"触发方式={dr.triggered_mode}")
        else:
            print("  暂无灾害记录")

        print("\n  1. 手动触发灾害  2. 随机触发灾害  3. 清除所有灾害  4. 返回")
        c = input("  选择: ").strip()
        if c == "1":
            if not self.mgr.fields:
                print("  ⚠ 尚未添加任何农田，请先添加农田后再进行灾害模拟")
                return
            disaster_types = ["干旱", "洪涝", "霜冻", "虫害"]
            di = select_from_list(disaster_types, "灾害类型")
            year = self._select_year("选择年份")
            if year is None:
                return
            season_labels = [s.value for s in SEASON_ORDER]
            si = select_from_list(season_labels, "影响季节")
            fnames = list(self.mgr.fields.keys())
            print("  选择受灾农田 (逗号分隔编号，留空选全部):")
            for i, n in enumerate(fnames, 1):
                print(f"    {i}. {n}")
            choice = input("  选择: ").strip()
            if choice:
                selected = []
                for idx in choice.split(","):
                    idx = idx.strip()
                    if idx.isdigit() and 1 <= int(idx) <= len(fnames):
                        selected.append(fnames[int(idx) - 1])
                field_names = selected if selected else fnames
            else:
                field_names = fnames
            severity = input_float("  严重度(0.1-0.5, 即10%-50%减产): ", 0.3)
            severity = max(0.01, min(1.0, severity))
            dr, err = self.mgr.simulate_disaster(
                disaster_types[di], year, SEASON_ORDER[si], field_names, severity)
            if err:
                print(f"  ✗ {err}")
            else:
                fields_str = "、".join(dr.field_names)
                print(f"  ✓ {dr.disaster_type}已触发: 影响{len(dr.field_names)}块农田({fields_str}), "
                      f"减产{dr.severity*100:.0f}%")

        elif c == "2":
            if not self.mgr.fields:
                print("  ⚠ 尚未添加任何农田，请先添加农田后再进行灾害模拟")
                return
            dr = self.mgr.random_disaster()
            if dr is None:
                print("  ⚠ 无法触发随机灾害")
                return
            fields_str = "、".join(dr.field_names)
            print(f"  ✓ 随机灾害: {dr.disaster_type} ({dr.year}年{dr.season.value}), "
                  f"影响={fields_str}, 减产{dr.severity*100:.0f}%")

        elif c == "3":
            self.mgr.clear_disasters()
            print("  ✓ 已清除所有灾害记录")

    def _fertilizer_advice(self):
        print("\n  === 肥料采购建议 ===")
        print("  1. 单年  2. 多年度合计  3. 返回")
        c = input("  选择: ").strip()
        if c == "1":
            year = self._select_year("选择年份")
            if year is None:
                return
            totals, details = self.mgr.calculate_fertilizer(year=year)
            title = f"{year}年"
        elif c == "2":
            totals, details = self.mgr.calculate_fertilizer()
            title = f"{min(self.mgr.plan_years)}-{max(self.mgr.plan_years)}年合计"
        else:
            return

        if not details:
            print("  没有种植计划，无法计算肥料需求")
            return

        print(f"\n  {title}肥料需求明细:")
        print(f"  {'农田':<10} {'年份':<6} {'季节':<6} {'作物':<6} {'面积(亩)':<10} "
              f"{'N(kg)':<10} {'P(kg)':<10} {'K(kg)':<10}")
        print_separator("─", 80)
        for d in details:
            print(f"  {d['field']:<10} {d['year']:<6} {d['season'].value:<6} "
                  f"{d['crop']:<6} {d['area']:<10.1f} "
                  f"{d['N']:<10.1f} {d['P']:<10.1f} {d['K']:<10.1f}")

        print_separator("─", 80)
        print(f"  {'合计':<10} {'':<6} {'':<6} {'':<6} {'':<10} "
              f"{totals['N']:<10.1f} {totals['P']:<10.1f} {totals['K']:<10.1f}")

        print(f"\n  📋 肥料采购建议:")
        print(f"    尿素(含N 46%):  {totals['N'] / 0.46:.1f} kg")
        print(f"    过磷酸钙(含P₂O₅ 16%):  {totals['P'] / 0.16:.1f} kg "
              f"(P→P₂O₅换算: {totals['P']*2.29:.1f} kg P₂O₅)")
        print(f"    氯化钾(含K₂O 60%):  {totals['K'] / 0.60:.1f} kg "
              f"(K→K₂O换算: {totals['K']*1.20:.1f} kg K₂O)")
        print(f"\n  建议额外采购10%余量以应对损耗:")
        print(f"    尿素:  {totals['N'] / 0.46 * 1.1:.1f} kg")
        print(f"    过磷酸钙:  {totals['P'] / 0.16 * 1.1:.1f} kg")
        print(f"    氯化钾:  {totals['K'] / 0.60 * 1.1:.1f} kg")

    def _export_csv(self):
        print("\n  === 导出种植计划 ===")
        print("  1. 单年  2. 全部年份  3. 返回")
        c = input("  选择: ").strip()
        if c == "1":
            year = self._select_year("选择年份")
            if year is None:
                return
            filepath = input(f"  导出文件名 (默认: planting_plan_{year}.csv): ").strip()
            if not filepath:
                filepath = f"planting_plan_{year}.csv"
            if not filepath.endswith(".csv"):
                filepath += ".csv"
            result = self.mgr.export_plan_csv(filepath, year=year)
        elif c == "2":
            filepath = input("  导出文件名 (默认: planting_plan.csv): ").strip()
            if not filepath:
                filepath = "planting_plan.csv"
            if not filepath.endswith(".csv"):
                filepath += ".csv"
            result = self.mgr.export_plan_csv(filepath)
        else:
            return
        print(f"  ✓ 种植计划已导出到: {result}")

    def _view_calendar(self):
        print("\n  === 田块种植日历 ===")
        print("  1. 单年  2. 全部年份  3. 返回")
        c = input("  选择: ").strip()
        if c == "1":
            year = self._select_year("选择年份")
            if year is None:
                return
            self.mgr.generate_calendar(year=year)
        elif c == "2":
            self.mgr.generate_calendar()
        else:
            return

    def _configure_prices_costs(self):
        print("\n  === 配置价格与成本 ===")
        print("  1. 配置作物售价  2. 配置作物成本  3. 配置肥料单价  4. 返回")
        c = input("  选择: ").strip()

        if c == "1":
            print("  当前价格 (元/kg):")
            for name, price in self.mgr.prices.items():
                print(f"    {name}: ¥{price:.2f}")
            name = input("  作物名称: ").strip()
            if not name:
                return
            if name not in self.mgr.prices:
                print("  新作物价格条目")
            price = input_float("  价格(元/kg): ")
            self.mgr.prices[name] = price
            self.mgr._save()
            print(f"  ✓ {name} 价格已设为 ¥{price:.2f}/kg")

        elif c == "2":
            print("  当前作物单位成本 (元/亩):")
            for name, cost in self.mgr.costs.items():
                print(f"    {name}: 种子¥{cost.get('seed_per_mu', 0):.0f} + "
                      f"灌溉¥{cost.get('irrigation_per_mu', 0):.0f} + "
                      f"人工¥{cost.get('labor_per_mu', 0):.0f}")
            name = input("  作物名称: ").strip()
            if not name:
                return
            if name not in self.mgr.costs:
                self.mgr.costs[name] = {"seed_per_mu": 0.0, "irrigation_per_mu": 0.0, "labor_per_mu": 0.0}
                print("  新作物成本条目")
            seed_cost = input_float("  种子成本(元/亩): ", self.mgr.costs[name].get("seed_per_mu", 0))
            irrig_cost = input_float("  灌溉成本(元/亩): ", self.mgr.costs[name].get("irrigation_per_mu", 0))
            labor_cost = input_float("  人工成本(元/亩): ", self.mgr.costs[name].get("labor_per_mu", 0))
            self.mgr.costs[name] = {
                "seed_per_mu": seed_cost,
                "irrigation_per_mu": irrig_cost,
                "labor_per_mu": labor_cost,
            }
            self.mgr._save()
            print(f"  ✓ {name} 成本已更新")

        elif c == "3":
            print("  当前肥料单价 (元/kg):")
            for k, v in self.mgr.fertilizer_prices.items():
                print(f"    {k}: ¥{v:.2f}/kg")
            print("  1. 氮(N)  2. 磷(P)  3. 钾(K)")
            choice = input("  选择: ").strip()
            mapping = {"1": "N", "2": "P", "3": "K"}
            if choice not in mapping:
                print("  无效选择")
                return
            k = mapping[choice]
            price = input_float(f"  {k} 单价(元/kg): ", self.mgr.fertilizer_prices.get(k, 0))
            self.mgr.fertilizer_prices[k] = price
            self.mgr._save()
            print(f"  ✓ {k} 单价已设为 ¥{price:.2f}/kg")

    def _configure_years(self):
        print("\n  === 设置规划年限 ===")
        print(f"  当前规划年份: {min(self.mgr.plan_years)}-{max(self.mgr.plan_years)} "
              f"({len(self.mgr.plan_years)}年)")
        start_year = input_int("  起始年份: ", self.mgr.current_year)
        num_years = input_int("  规划年数: ", len(self.mgr.plan_years))
        if num_years < 1:
            print("  年数必须大于0")
            return
        confirm = input(f"  将设置 {start_year}-{start_year+num_years-1} 共 {num_years} 年规划期，"
                        f"超出范围的计划和记录将被移除。确认? (y/N): ").strip().lower()
        if confirm in ("y", "yes"):
            self.mgr.set_plan_years(start_year, num_years)
            print(f"  ✓ 已设置规划年限: {start_year}-{start_year+num_years-1} ({num_years}年)")
        else:
            print("  已取消")

    def _multi_year_table(self):
        print("\n  === 多年度表格排期 ===")
        if not self.mgr.fields:
            print("  请先添加农田")
            return
        if len(self.mgr.plan_years) < 2:
            print("  建议先设置规划年限（至少2年）以使用表格排期")
        years = self.mgr.plan_years
        fields = list(self.mgr.fields.keys())

        while True:
            table = self.mgr.get_plan_table()
            print()
            print_separator("═", 120)
            header = f"  {'农田':<12}"
            for y in years:
                header += f" │ {y}年春 │ {y}年夏 │ {y}年秋 │ {y}年冬 │"
            print(header)
            print_separator("─", 120)
            for fname in fields:
                row = f"  {fname:<12}"
                for y in years:
                    for s in SEASON_ORDER:
                        crop = table[y][fname][s]
                        display = crop if crop else "  —  "
                        row += f" │ {display:<7}"
                    row += " │"
                print(row)
            print_separator("═", 120)

            for y in years[1:]:
                cinfo = self.mgr.get_cross_year_info(y)
                if cinfo:
                    lines = []
                    for ci in cinfo:
                        if ci["is_conflict"]:
                            lines.append(f"⚠ {ci['field']}({ci['prev_crop']}→{ci['curr_crop']})")
                        elif ci["curr_crop"]:
                            lines.append(f"✓ {ci['field']}({ci['prev_crop']}→{ci['curr_crop']})")
                        else:
                            lines.append(f"  {ci['field']}({ci['prev_crop']}→空置)")
                    print(f"  🔗 {y-1}冬→{y}春衔接: " + "  ".join(lines))

            total_cost = 0.0
            total_rev = 0.0
            for y in years:
                for s in SEASON_ORDER:
                    c, _, _ = self.mgr.calculate_season_costs(y, s)
                    r, _ = self.mgr.estimate_income(y, s)
                    total_cost += c
                    total_rev += r
            conflicts = self.mgr.check_rotation_conflicts()
            cross_count = len([c for c in conflicts if c["prev_year"] != c["curr_year"]])
            same_count = len([c for c in conflicts if c["prev_year"] == c["curr_year"]])
            print(f"  📊 总计: 成本¥{total_cost:,.0f}  收入¥{total_rev:,.0f}  "
                  f"净收益¥{total_rev - total_cost:,.0f}  "
                  f"轮作冲突 {len(conflicts)} 处(跨年{cross_count}, 年内{same_count})")

            print()
            print("  操作: [M]修改  [C]复制全年到下年  [R]复制某行  "
                  "[T]批量替换作物  [K]批量清空某季  [S]查看预算冲突  [B]返回")
            op = input("  选择操作: ").strip().upper()
            if op == "B":
                return
            elif op == "M":
                print("  选择要修改的单元格:")
                for i, f in enumerate(fields, 1):
                    print(f"    {i}. {f}")
                fi = input("  农田编号: ").strip()
                if not (fi.isdigit() and 1 <= int(fi) <= len(fields)):
                    continue
                fname = fields[int(fi) - 1]

                year_opts = [str(y) for y in years]
                yi = select_from_list(year_opts, "选择年份")
                y = years[yi]

                season_opts = [s.value for s in SEASON_ORDER]
                si = select_from_list(season_opts, "选择季节")
                s = SEASON_ORDER[si]

                suitable = [cn for cn in self.mgr.crops if s in self.mgr.crops[cn].seasons]
                suitable.insert(0, "(清空)")
                ci = select_from_list(suitable, "选择作物（0清空）")
                if ci == 0:
                    crop_name = ""
                else:
                    crop_name = suitable[ci]
                _, err = self.mgr.update_plan_cell(fname, y, s, crop_name)
                if err:
                    print(f"  ✗ {err}")
                else:
                    print(f"  ✓ 已更新: {fname} {y}年{s.value} → {crop_name or '(空)'}")
            elif op == "C":
                from_year_opts = [str(y) for y in years[:-1]]
                if not from_year_opts:
                    print("  没有可复制的年份")
                    continue
                yi = select_from_list(from_year_opts, "从哪一年复制")
                from_y = years[yi]
                to_y = from_y + 1
                count, msg = self.mgr.copy_field_plan(from_y, to_y)
                print(f"  {msg}")
            elif op == "R":
                from_year_opts = [str(y) for y in years[:-1]]
                if not from_year_opts:
                    print("  没有可复制的年份")
                    continue
                yi = select_from_list(from_year_opts, "从哪一年复制")
                from_y = years[yi]
                to_y = from_y + 1
                for i, f in enumerate(fields, 1):
                    print(f"    {i}. {f}")
                fi = input("  选择农田编号: ").strip()
                if not (fi.isdigit() and 1 <= int(fi) <= len(fields)):
                    continue
                fname = fields[int(fi) - 1]
                count, msg = self.mgr.copy_field_plan(from_y, to_y, fname)
                print(f"  {msg}")
            elif op == "T":
                crop_list = list(self.mgr.crops.keys())
                if not crop_list:
                    continue
                oi = select_from_list(crop_list, "选择要被替换的作物")
                old_crop = crop_list[oi]
                ni = select_from_list(crop_list, f"选择新作物（替换 {old_crop}）")
                new_crop = crop_list[ni]
                fi_opts = ["全部农田"] + fields
                fi = select_from_list([f for f in fi_opts], "选择作用范围")
                target_field = None if fi == 0 else fields[fi - 1]
                count, msg = self.mgr.batch_replace_crop(old_crop, new_crop, target_field, years)
                print(f"  {msg}")
            elif op == "K":
                for i, f in enumerate(fields, 1):
                    print(f"    {i}. {f}")
                fi = input("  选择农田编号: ").strip()
                if not (fi.isdigit() and 1 <= int(fi) <= len(fields)):
                    continue
                fname = fields[int(fi) - 1]
                season_opts = [s.value for s in SEASON_ORDER]
                si = select_from_list(season_opts, "选择要清空的季节")
                s = SEASON_ORDER[si]
                count, msg = self.mgr.batch_clear_season(fname, s, years)
                print(f"  {msg}")
            elif op == "S":
                year = self._select_year("选择年份查看详情（空=全部）", allow_all=True)
                if year is None:
                    year = 0
                if year == 0:
                    suggestions = []
                    for y in years:
                        suggestions.extend(self.mgr.optimization_suggestions(y))
                else:
                    suggestions = self.mgr.optimization_suggestions(year)
                if not suggestions:
                    print("  ✓ 未发现优化问题")
                    continue
                priority_map = {"高": "🔴", "中": "🟡", "低": "🟢"}
                for i, s in enumerate(suggestions, 1):
                    icon = priority_map.get(s["priority"], "")
                    print(f"  {icon} [{s['priority']}] {i}. {s['title']}")
                    print(f"     {s['detail']}")
                    if s.get("actions"):
                        for a in s["actions"]:
                            print(f"       • {a}")

    def _business_decision(self):
        print("\n  === 经营决策工具 ===")
        print("  1. 设置年度预算与目标  2. 查看预算达成分析  3. 优化建议  4. 返回")
        c = input("  选择: ").strip()

        if c == "1":
            year = self._select_year("选择年份")
            if year is None:
                return
            current = self.mgr.get_budget_target(year)
            print(f"\n  {year}年当前设置:")
            if current.get("budget") is not None:
                print(f"    年度总成本预算: ¥{current['budget']:,.2f}")
            else:
                print(f"    年度总成本预算: 未设置")
            if current.get("target_profit") is not None:
                print(f"    目标净收益: ¥{current['target_profit']:,.2f}")
            else:
                print(f"    目标净收益: 未设置")
            print("\n  (留空=跳过不修改, 输入0表示清除)")
            budget_val = input_float("  年度总成本预算 (元): ", allow_empty=True)
            if budget_val is not None:
                if budget_val == 0:
                    budget_val = None
                    print("    (已清除预算)")
                else:
                    print(f"    (设置预算为¥{budget_val:,.2f})")
            else:
                print("    (跳过预算设置)")

            target_val = input_float("  目标净收益 (元): ", allow_empty=True)
            if target_val is not None:
                if target_val == 0:
                    target_val = None
                    print("    (已清除目标)")
                else:
                    print(f"    (设置目标为¥{target_val:,.2f})")
            else:
                print("    (跳过目标设置)")

            self.mgr.set_budget_target(year, budget=budget_val, target_profit=target_val)
            print(f"  ✓ {year}年预算与目标已更新")

        elif c == "2":
            year = self._select_year("选择年份")
            if year is None:
                return
            ba = self.mgr.budget_analysis(year)
            print(f"\n  {year}年预算达成分析:")
            print(f"    预计毛收入: ¥{ba['total_revenue']:,.2f}")
            print(f"    预计总成本: ¥{ba['total_cost']:,.2f}")
            print(f"    预计净收益: ¥{ba['total_profit']:,.2f}")
            if ba["budget"] is not None:
                bs = ba["budget_status"]
                status = "✓ 预算内" if not bs["is_over"] else "✗ 超预算"
                print(f"\n    成本预算: ¥{ba['budget']:,.2f}")
                print(f"    预算状态: {status} ({bs['over_pct']:+.1f}%)")
                if bs["is_over"]:
                    print(f"    超出金额: ¥{bs['over_amount']:,.2f}")
            if ba["target_profit"] is not None:
                ts = ba["target_status"]
                status = "✓ 已达成" if ts["is_met"] else "✗ 未达成"
                print(f"\n    目标净收益: ¥{ba['target_profit']:,.2f}")
                print(f"    目标状态: {status} ({ts['gap_pct']:+.1f}%)")
                if not ts["is_met"]:
                    print(f"    还差金额: ¥{ts['gap_amount']:,.2f}")

        elif c == "3":
            year = self._select_year("选择年份")
            if year is None:
                return
            suggestions = self.mgr.optimization_suggestions(year)
            if not suggestions:
                print(f"\n  {year}年经营状态良好，暂无优化建议 ✓")
                return
            print(f"\n  {year}年优化建议:")
            priority_map = {"高": "🔴", "中": "🟡", "低": "🟢"}
            for i, s in enumerate(suggestions, 1):
                icon = priority_map.get(s["priority"], "")
                print(f"\n  {icon} [{s['priority']}] {i}. {s['title']}")
                print(f"     {s['detail']}")
                if s["actions"]:
                    print(f"     建议:")
                    for a in s["actions"]:
                        print(f"       • {a}")

    def _deviation_trend(self):
        print("\n  === 偏差趋势分析 (按年份) ===")
        print("  1. 按作物查看趋势  2. 按农田查看趋势  3. 综合决策建议  4. 返回")
        c = input("  选择: ").strip()

        if c == "1":
            crop_names = list(self.mgr.crops.keys())
            if not crop_names:
                print("  暂无作物")
                return
            ci = select_from_list(crop_names, "选择作物")
            crop_name = crop_names[ci]
            trend = self.mgr.deviation_trend_by_crop(crop_name)
            if not trend:
                print(f"\n  {crop_name} 暂无偏差记录")
                return
            print(f"\n  {crop_name} 年度偏差趋势:")
            print(f"  {'年份':<8} {'记录数':<8} {'预测(kg)':<14} {'实际(kg)':<14} {'偏差(kg)':<14} {'偏差%':<12} 趋势")
            print_separator("─", 90)
            for t in trend:
                trend_sym = "↗ 偏高" if t["deviation_pct"] > 5 else ("↘ 偏低" if t["deviation_pct"] < -5 else "— 正常")
                print(f"  {t['year']:<8} {t['count']:<8} {t['predicted']:<14.1f} {t['actual']:<14.1f} {t['deviation']:<+14.1f} {t['deviation_pct']:<+12.1f}%  {trend_sym}")
            low_cnt = len([t for t in trend if t["deviation_pct"] < -5])
            if low_cnt >= 2:
                print(f"\n  ⚠ {crop_name} 有 {low_cnt} 年表现偏低，建议:")
                affected = [(e.year, e.season.value, e.field_name)
                            for e in self.mgr.plan if e.crop_name == crop_name]
                print(f"    • 可考虑减少 {crop_name} 的种植面积")
                print(f"    • 可考虑替换为更高产的作物")
                if affected:
                    print(f"    • 当前分布: " + ", ".join(
                        f"{y}年{s}({f})" for y, s, f in affected[:5]))

        elif c == "2":
            field_names = list(self.mgr.fields.keys())
            if not field_names:
                print("  暂无农田")
                return
            fi = select_from_list(field_names, "选择农田")
            field_name = field_names[fi]
            trend = self.mgr.deviation_trend_by_field(field_name)
            if not trend:
                print(f"\n  {field_name} 暂无偏差记录")
                return
            print(f"\n  {field_name} 年度偏差趋势:")
            print(f"  {'年份':<8} {'记录数':<8} {'预测(kg)':<14} {'实际(kg)':<14} {'偏差(kg)':<14} {'偏差%':<12} 趋势")
            print_separator("─", 90)
            for t in trend:
                trend_sym = "↗ 偏高" if t["deviation_pct"] > 5 else ("↘ 偏低" if t["deviation_pct"] < -5 else "— 正常")
                print(f"  {t['year']:<8} {t['count']:<8} {t['predicted']:<14.1f} {t['actual']:<14.1f} {t['deviation']:<+14.1f} {t['deviation_pct']:<+12.1f}%  {trend_sym}")
            low_cnt = len([t for t in trend if t["deviation_pct"] < -5])
            if low_cnt >= 2:
                print(f"\n  ⚠ {field_name} 有 {low_cnt} 年表现偏低，建议:")
                affected = [(e.year, e.season.value, e.crop_name)
                            for e in self.mgr.plan if e.field_name == field_name]
                print(f"    • 可考虑降低 {field_name} 的高风险作物面积")
                print(f"    • 可考虑换茬或调整该地块的种植品种")
                if affected:
                    print(f"    • 当前安排: " + ", ".join(
                        f"{y}年{s}({c})" for y, s, c in affected[:5]))

        elif c == "3":
            suggestions = self.mgr.get_decision_suggestions()
            if not suggestions:
                print("\n  ✓ 当前数据中暂未发现连续偏低的作物或农田")
                return
            print(f"\n  共发现 {len(suggestions)} 条决策建议:")
            priority_map = {"高": "🔴", "中": "🟡", "低": "🟢"}
            for i, s in enumerate(suggestions, 1):
                icon = priority_map.get(s["priority"], "")
                print(f"\n  {icon} [{s['priority']}] {i}. {s['title']}")
                print(f"     {s['detail']}")
                if s.get("actions"):
                    print(f"     建议操作:")
                    for a in s["actions"]:
                        print(f"       • {a}")

    def _scenario_manager(self):
        print("\n  === 种植方案版本管理与对比 ===")
        print("  1. 保存当前方案  2. 加载方案  3. 删除方案  "
              "4. 并排对比方案  5. 返回")
        c = input("  选择: ").strip()

        if c == "1":
            name = input("  方案名称: ").strip()
            if not name:
                print("  名称不能为空")
                return
            if name in self.mgr.scenarios:
                yn = input(f"  方案 '{name}' 已存在，覆盖? (y/n): ").strip().lower()
                if yn != "y":
                    return
            self.mgr.save_scenario(name)
            print(f"  ✓ 方案 '{name}' 已保存 ({len(self.mgr.plan)} 条计划)")

        elif c == "2":
            names = list(self.mgr.scenarios.keys())
            if not names:
                print("  尚无已保存方案")
                return
            ni = select_from_list(names, "选择方案")
            name = names[ni]
            ok, msg = self.mgr.load_scenario(name)
            if ok:
                print(f"  ✓ {msg}")
            else:
                print(f"  ✗ {msg}")

        elif c == "3":
            names = list(self.mgr.scenarios.keys())
            if not names:
                print("  尚无已保存方案")
                return
            ni = select_from_list(names, "选择要删除的方案")
            name = names[ni]
            yn = input(f"  确认删除方案 '{name}'? (y/n): ").strip().lower()
            if yn != "y":
                return
            if self.mgr.delete_scenario(name):
                print(f"  ✓ 方案 '{name}' 已删除")

        elif c == "4":
            names = list(self.mgr.scenarios.keys())
            all_names = ["(当前方案)"] + names
            if not names:
                print("  尚无已保存方案，请先保存至少一个方案")
                return
            print("\n  选择要对比的方案 (逗号分隔编号, 如 1,2,3):")
            for i, n in enumerate(all_names, 1):
                print(f"    {i}. {n}")
            raw = input("  选择方案编号: ").strip()
            if not raw:
                return
            try:
                picks = [int(x) - 1 for x in raw.split(",") if x.strip().isdigit()]
            except ValueError:
                print("  输入格式错误")
                return
            picks = [p for p in picks if 0 <= p < len(all_names)]
            if len(picks) < 2:
                print("  请至少选择2个方案")
                return
            sel_names = []
            for p in picks:
                if p == 0:
                    sel_names.append("__current__")
                else:
                    sel_names.append(names[p - 1])

            year = self._select_year("选择对比年份 (空=全部)", allow_all=True)
            if year == 0:
                year = None

            results = self.mgr.compare_scenarios(sel_names, year)
            if not results:
                print("  对比失败")
                return

            display_names = {
                "__current__": "(当前方案)",
            }
            for n in names:
                display_names[n] = n

            print(f"\n  方案对比表 (按规划期合计)" if year is None
                  else f"\n  方案对比表 ({year}年)")
            cols = list(results.keys())
            col_w = 18
            print(f"  {'指标':<18}", end="")
            for k in cols:
                print(f"│ {display_names.get(k, k):<{col_w}}", end="")
            print()
            print_separator("─", 18 + (col_w + 2) * len(cols))

            def _row(label, key, fmt):
                print(f"  {label:<18}", end="")
                for k in cols:
                    v = results[k].get(key)
                    if v is None:
                        print(f"│ {'(未设置)':<{col_w}}", end="")
                    else:
                        print(f"│ {fmt.format(v):<{col_w}}", end="")
                print()

            _row("预计总产量(kg)", "total_yield_kg", "{:,.1f}")
            _row("预计毛收入(元)", "total_revenue", "{:,.0f}")
            _row("预计总成本(元)", "total_cost", "{:,.0f}")
            _row("预计净收益(元)", "total_profit", "{:,.0f}")
            _row("轮作冲突数", "conflict_count", "{:d}")
            _row("计划条目数", "plan_count", "{:d}")
            if year is not None:
                _row("年度预算(元)", "budget", "{:,.0f}")
                _row("目标净收益(元)", "target_profit", "{:,.0f}")

            if year is None:
                print(f"\n  提示: 选择具体年份可查看预算与目标对比")
            best = max(results.items(), key=lambda kv: kv[1]["total_profit"])
            print(f"\n  🎯 当前净收益最高方案: {display_names.get(best[0], best[0])}"
                  f" (¥{best[1]['total_profit']:,.0f})")

    def _exit(self):
        print("\n  再见! 🌾")
        raise SystemExit(0)


if __name__ == "__main__":
    cli = CLI()
    cli.run()