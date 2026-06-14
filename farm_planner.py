#!/usr/bin/env python3
import csv
import json
import os
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Season(Enum):
    SPRING = "春季"
    SUMMER = "夏季"
    AUTUMN = "秋季"
    WINTER = "冬季"


SEASON_ORDER = [Season.SPRING, Season.SUMMER, Season.AUTUMN, Season.WINTER]


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
    season: Season
    crop_name: str

    def to_dict(self):
        return {
            "field_name": self.field_name,
            "season": self.season.value,
            "crop_name": self.crop_name,
        }

    @staticmethod
    def from_dict(d):
        return PlantingEntry(
            field_name=d["field_name"],
            season=Season(d["season"]),
            crop_name=d["crop_name"],
        )


@dataclass
class DisasterRecord:
    disaster_type: str
    season: Season
    field_names: list
    severity: float
    triggered_mode: str

    def to_dict(self):
        return {
            "disaster_type": self.disaster_type,
            "season": self.season.value,
            "field_names": self.field_names,
            "severity": self.severity,
            "triggered_mode": self.triggered_mode,
        }

    @staticmethod
    def from_dict(d):
        return DisasterRecord(
            disaster_type=d["disaster_type"],
            season=Season(d["season"]),
            field_names=d["field_names"],
            severity=d["severity"],
            triggered_mode=d["triggered_mode"],
        )


@dataclass
class ActualHarvest:
    field_name: str
    season: Season
    crop_name: str
    actual_yield: float

    def to_dict(self):
        return {
            "field_name": self.field_name,
            "season": self.season.value,
            "crop_name": self.crop_name,
            "actual_yield": self.actual_yield,
        }

    @staticmethod
    def from_dict(d):
        return ActualHarvest(
            field_name=d["field_name"],
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

    def _save(self):
        data = {
            "crops": {n: c.to_dict() for n, c in self.crops.items()},
            "fields": {n: f.to_dict() for n, f in self.fields.items()},
            "plan": [e.to_dict() for e in self.plan],
            "actual_harvests": [h.to_dict() for h in self.actual_harvests],
            "disaster_records": [d.to_dict() for d in self.disaster_records],
            "prices": self.prices,
        }
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_crop(self, name, seasons, growth_days, yield_per_mu, water_need,
                 fertilizer_need, npk_per_mu):
        crop = Crop(name, seasons, growth_days, yield_per_mu, water_need,
                    fertilizer_need, npk_per_mu)
        self.crops[name] = crop
        if name not in self.prices:
            self.prices[name] = 0.0
        self._save()
        return crop

    def add_field(self, name, area, soil_type, drainage_score):
        f = Field(name, area, soil_type, drainage_score)
        self.fields[name] = f
        self._save()
        return f

    def add_plan_entry(self, field_name, season, crop_name):
        if field_name not in self.fields:
            return None, f"农田 '{field_name}' 不存在"
        if crop_name not in self.crops:
            return None, f"作物 '{crop_name}' 不存在"
        crop = self.crops[crop_name]
        if season not in crop.seasons:
            return None, f"{crop_name} 不适合在{season.value}种植"
        existing = [e for e in self.plan
                    if e.field_name == field_name and e.season == season]
        if existing:
            self.plan.remove(existing[0])
        entry = PlantingEntry(field_name, season, crop_name)
        self.plan.append(entry)
        self._save()
        return entry, None

    def check_rotation_conflicts(self):
        conflicts = []
        field_seasons = {}
        for entry in sorted(self.plan, key=lambda e: (e.field_name, SEASON_ORDER.index(e.season))):
            key = entry.field_name
            if key not in field_seasons:
                field_seasons[key] = []
            field_seasons[key].append(entry)

        for fname, entries in field_seasons.items():
            for i in range(1, len(entries)):
                prev = entries[i - 1]
                curr = entries[i]
                if prev.crop_name == curr.crop_name:
                    conflicts.append({
                        "field": fname,
                        "prev_season": prev.season,
                        "curr_season": curr.season,
                        "crop": curr.crop_name,
                        "penalty": self.ROTATION_PENALTY,
                    })
        return conflicts

    def _soil_multiplier(self, field: Field, crop: Crop):
        base = self.SOIL_MULTIPLIER.get(field.soil_type, 1.0)
        if crop.water_need in ("较高", "极高") and field.drainage_score < self.DRAINAGE_THRESHOLD:
            if crop.water_need == "极高":
                base *= 0.85
            else:
                base *= 0.92
        return base

    def predict_yield(self, field_name, season, crop_name, include_disasters=True):
        f = self.fields.get(field_name)
        c = self.crops.get(crop_name)
        if not f or not c:
            return 0.0
        base = c.yield_per_mu * f.area
        soil_mult = self._soil_multiplier(f, c)
        rotation_mult = 1.0
        conflicts = self.check_rotation_conflicts()
        for cf in conflicts:
            if cf["field"] == field_name and cf["curr_season"] == season and cf["crop"] == crop_name:
                rotation_mult = 1.0 - cf["penalty"]
                break
        disaster_mult = 1.0
        if include_disasters:
            for dr in self.disaster_records:
                if dr.season == season and field_name in dr.field_names:
                    disaster_mult *= (1.0 - dr.severity)
        return base * soil_mult * rotation_mult * disaster_mult

    def predict_season_harvest(self, season):
        total = 0.0
        details = []
        for entry in self.plan:
            if entry.season == season:
                y = self.predict_yield(entry.field_name, entry.season, entry.crop_name)
                total += y
                details.append({
                    "field": entry.field_name,
                    "crop": entry.crop_name,
                    "predicted_kg": y,
                })
        return total, details

    def predict_annual_harvest(self):
        results = {}
        for s in SEASON_ORDER:
            total, details = self.predict_season_harvest(s)
            results[s] = {"total_kg": total, "details": details}
        return results

    def estimate_income(self, season):
        _, details = self.predict_season_harvest(season)
        total_income = 0.0
        income_details = []
        for d in details:
            price = self.prices.get(d["crop"], 0.0)
            tons = d["predicted_kg"] / 1000.0
            income = tons * price * 1000
            total_income += income
            income_details.append({
                "field": d["field"],
                "crop": d["crop"],
                "predicted_kg": d["predicted_kg"],
                "price_per_kg": price,
                "income": income,
            })
        return total_income, income_details

    def estimate_annual_income(self):
        results = {}
        for s in SEASON_ORDER:
            income, details = self.estimate_income(s)
            results[s] = {"total_income": income, "details": details}
        return results

    def record_actual_harvest(self, field_name, season, crop_name, actual_kg):
        existing = [h for h in self.actual_harvests
                    if h.field_name == field_name and h.season == season]
        for h in existing:
            self.actual_harvests.remove(h)
        ah = ActualHarvest(field_name, season, crop_name, actual_kg)
        self.actual_harvests.append(ah)
        self._save()
        return ah

    def deviation_analysis(self, season=None):
        reports = []
        entries = self.plan if season is None else [e for e in self.plan if e.season == season]
        for entry in entries:
            predicted = self.predict_yield(entry.field_name, entry.season, entry.crop_name)
            actual = 0.0
            for ah in self.actual_harvests:
                if (ah.field_name == entry.field_name and ah.season == entry.season
                        and ah.crop_name == entry.crop_name):
                    actual = ah.actual_yield
                    break
            if actual > 0:
                deviation = actual - predicted
                deviation_pct = (deviation / predicted * 100) if predicted > 0 else 0
                reports.append({
                    "field": entry.field_name,
                    "season": entry.season,
                    "crop": entry.crop_name,
                    "predicted_kg": predicted,
                    "actual_kg": actual,
                    "deviation_kg": deviation,
                    "deviation_pct": deviation_pct,
                })
        return reports

    def simulate_disaster(self, disaster_type, season, field_names=None, severity=None):
        if severity is None:
            severity = round(random.uniform(0.1, 0.5), 2)
        if field_names is None:
            field_names = random.sample(list(self.fields.keys()),
                                        k=random.randint(1, len(self.fields)))
        else:
            valid = [fn for fn in field_names if fn in self.fields]
            field_names = valid
        if not field_names:
            return None, "没有可用的农田"
        dr = DisasterRecord(disaster_type, season, field_names, severity, "手动" if field_names else "随机")
        self.disaster_records.append(dr)
        self._save()
        return dr, None

    def random_disaster(self):
        dtype = random.choice(["干旱", "洪涝", "霜冻", "虫害"])
        season = random.choice(SEASON_ORDER)
        severity = round(random.uniform(0.1, 0.5), 2)
        k = random.randint(1, max(1, len(self.fields)))
        affected = random.sample(list(self.fields.keys()), k=k)
        dr = DisasterRecord(dtype, season, affected, severity, "随机")
        self.disaster_records.append(dr)
        self._save()
        return dr

    def clear_disasters(self):
        self.disaster_records.clear()
        self._save()

    def calculate_fertilizer(self):
        totals = {"N": 0.0, "P": 0.0, "K": 0.0}
        details = []
        for entry in self.plan:
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
                "season": entry.season,
                "crop": entry.crop_name,
                "area": fld.area,
                "N": field_npk.get("N", 0),
                "P": field_npk.get("P", 0),
                "K": field_npk.get("K", 0),
            })
        return totals, details

    def export_plan_csv(self, filepath="planting_plan.csv"):
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["农田", "面积(亩)", "土壤类型", "排水评分",
                             "春季作物", "夏季作物", "秋季作物", "冬季作物"])
            for fname, fld in self.fields.items():
                row = [fname, fld.area, fld.soil_type, fld.drainage_score]
                for s in SEASON_ORDER:
                    crop_name = ""
                    for e in self.plan:
                        if e.field_name == fname and e.season == s:
                            crop_name = e.crop_name
                            break
                    row.append(crop_name)
                writer.writerow(row)
        return filepath

    def generate_calendar(self):
        season_labels = [s.value for s in SEASON_ORDER]
        field_names = list(self.fields.keys())
        if not field_names:
            print("\n  尚未添加任何农田\n")
            return

        plan_map = {}
        for entry in self.plan:
            plan_map[(entry.field_name, entry.season)] = entry.crop_name

        crop_symbols = {"小麦": "麦", "玉米": "玉", "水稻": "稻", "大豆": "豆", "土豆": "薯"}
        used_crops = set()
        for e in self.plan:
            used_crops.add(e.crop_name)
        extra = [c for c in used_crops if c not in crop_symbols]
        for c in extra:
            crop_symbols[c] = c[0]

        name_width = max(len(n) for n in field_names) + 2
        name_width = max(name_width, 6)
        cell_width = 10
        total_width = name_width + cell_width * 4 + 3

        print()
        print("┌" + "─" * (total_width - 2) + "┐")
        title = "田块种植日历"
        pad = total_width - 2 - len(title) * 2
        left_pad = pad // 2
        right_pad = pad - left_pad
        print("│" + " " * left_pad + title + " " * right_pad + "│")
        print("├" + "─" * name_width + "┼" + "─" * cell_width + "┼" + "─" * cell_width + "┼" + "─" * cell_width + "┼" + "─" * cell_width + "┤")

        header = "│" + "农田".ljust(name_width)
        for label in season_labels:
            header += "│" + label.center(cell_width)
        header += "│"
        print(header)

        print("├" + "─" * name_width + "┼" + "─" * cell_width + "┼" + "─" * cell_width + "┼" + "─" * cell_width + "┼" + "─" * cell_width + "┤")

        for fname in field_names:
            row = "│" + fname.ljust(name_width)
            for s in SEASON_ORDER:
                crop_name = plan_map.get((fname, s), "")
                if crop_name:
                    sym = crop_symbols.get(crop_name, crop_name[0])
                    display = f"{sym}·{crop_name}"
                else:
                    display = "—"
                row += "│" + display.center(cell_width)
            row += "│"
            print(row)
            print("├" + "─" * name_width + "┼" + "─" * cell_width + "┼" + "─" * cell_width + "┼" + "─" * cell_width + "┼" + "─" * cell_width + "┤")

        print("│" + "图例:".ljust(name_width) + "│", end="")
        legend_parts = []
        for cn, sym in crop_symbols.items():
            if cn in used_crops:
                legend_parts.append(f"{sym}={cn}")
        legend = " ".join(legend_parts)
        remaining = cell_width * 4 + 3
        print(legend[:remaining].ljust(remaining) + "│")
        print("└" + "─" * name_width + "┴" + "─" * cell_width + "┴" + "─" * cell_width + "┴" + "─" * cell_width + "┴" + "─" * cell_width + "┘")

        conflicts = self.check_rotation_conflicts()
        if conflicts:
            print("\n  ⚠ 轮作冲突警告:")
            for cf in conflicts:
                print(f"    - {cf['field']}: {cf['prev_season'].value}→{cf['curr_season'].value} "
                      f"连续种植{cf['crop']}，减产{cf['penalty']*100:.0f}%")
        print()


def print_separator(char="─", length=60):
    print(f"  {char * length}")


def input_float(prompt, default=None):
    while True:
        val = input(prompt).strip()
        if not val and default is not None:
            return default
        try:
            return float(val)
        except ValueError:
            print("  请输入有效的数字")


def input_int(prompt, default=None):
    while True:
        val = input(prompt).strip()
        if not val and default is not None:
            return default
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

    def _main_menu(self):
        print()
        print_separator()
        print("  🌾 农场种植计划与收成预测工具")
        print_separator()
        print("  1.  管理作物")
        print("  2.  管理农田")
        print("  3.  制定种植计划")
        print("  4.  收成预测与收入估算")
        print("  5.  记录实际收成")
        print("  6.  偏差分析报告")
        print("  7.  自然灾害模拟")
        print("  8.  肥料采购建议")
        print("  9.  导出种植计划 (CSV)")
        print("  10. 查看田块种植日历")
        print("  11. 配置作物价格")
        print("  0.  退出")
        print_separator()
        choice = input("  请选择功能: ").strip()
        actions = {
            "1": self._manage_crops,
            "2": self._manage_fields,
            "3": self._manage_plan,
            "4": self._predict_harvest,
            "5": self._record_harvest,
            "6": self._deviation_report,
            "7": self._disaster_sim,
            "8": self._fertilizer_advice,
            "9": self._export_csv,
            "10": self._view_calendar,
            "11": self._configure_prices,
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
                                key=lambda e: (e.field_name, SEASON_ORDER.index(e.season))):
                print(f"    {entry.field_name} - {entry.season.value} - {entry.crop_name}")
        else:
            print("    (空)")

        conflicts = self.mgr.check_rotation_conflicts()
        if conflicts:
            print("\n  ⚠ 轮作冲突:")
            for cf in conflicts:
                print(f"    {cf['field']}: {cf['prev_season'].value}→{cf['curr_season'].value} "
                      f"连续种植{cf['crop']}，减产{cf['penalty']*100:.0f}%")

        print("\n  1. 添加/修改计划条目  2. 删除计划条目  3. 快速批量规划  4. 返回")
        c = input("  选择: ").strip()
        if c == "1":
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
            entry, err = self.mgr.add_plan_entry(fname, SEASON_ORDER[si], suitable[int(ci) - 1])
            if err:
                print(f"  ✗ {err}")
            else:
                print(f"  ✓ 已规划: {fname} - {SEASON_ORDER[si].value} - {suitable[int(ci)-1]}")

        elif c == "2":
            if not self.mgr.plan:
                print("  没有可删除的计划条目")
                return
            for i, e in enumerate(self.mgr.plan, 1):
                print(f"    {i}. {e.field_name} - {e.season.value} - {e.crop_name}")
            idx = input("  选择要删除的编号: ").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(self.mgr.plan):
                removed = self.mgr.plan.pop(int(idx) - 1)
                self.mgr._save()
                print(f"  ✓ 已删除: {removed.field_name} - {removed.season.value} - {removed.crop_name}")

        elif c == "3":
            print("  快速批量规划: 为所有未分配的农田-季节组合分配作物")
            count = 0
            for fname in self.mgr.fields:
                for s in SEASON_ORDER:
                    existing = [e for e in self.mgr.plan
                                if e.field_name == fname and e.season == s]
                    if existing:
                        continue
                    suitable = [cn for cn in self.mgr.crops if s in self.mgr.crops[cn].seasons]
                    if not suitable:
                        continue
                    chosen = random.choice(suitable)
                    self.mgr.add_plan_entry(fname, s, chosen)
                    count += 1
            print(f"  ✓ 已自动规划 {count} 个条目")

    def _predict_harvest(self):
        print("\n  === 收成预测与收入估算 ===")
        print("  1. 按季节预测  2. 全年预测  3. 返回")
        c = input("  选择: ").strip()
        if c == "1":
            season_labels = [s.value for s in SEASON_ORDER]
            si = select_from_list(season_labels, "选择季节")
            season = SEASON_ORDER[si]
            total, details = self.mgr.predict_season_harvest(season)
            income, income_details = self.mgr.estimate_income(season)
            print(f"\n  {season.value}收成预测:")
            if not details:
                print("    (无种植计划)")
            for d in details:
                print(f"    {d['field']}: {d['crop']} - 预计 {d['predicted_kg']:.1f}kg "
                      f"({d['predicted_kg']/1000:.2f}吨)")
            print(f"\n  {season.value}预计总产量: {total:.1f}kg ({total/1000:.2f}吨)")
            print(f"  {season.value}预计总收入: ¥{income:,.2f}")
            for id_ in income_details:
                print(f"    {id_['field']}({id_['crop']}): "
                      f"{id_['predicted_kg']:.1f}kg × ¥{id_['price_per_kg']:.2f}/kg "
                      f"= ¥{id_['income']:,.2f}")

        elif c == "2":
            annual = self.mgr.predict_annual_harvest()
            annual_income = self.mgr.estimate_annual_income()
            total_all = 0.0
            total_income_all = 0.0
            print("\n  全年收成预测:")
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
            print(f"\n  全年预计总产量: {total_all:.1f}kg ({total_all/1000:.2f}吨)")
            print(f"  全年预计总收入: ¥{total_income_all:,.2f}")

    def _record_harvest(self):
        print("\n  === 记录实际收成 ===")
        if not self.mgr.plan:
            print("  没有种植计划，无法记录收成")
            return
        entries = sorted(self.mgr.plan,
                         key=lambda e: (e.field_name, SEASON_ORDER.index(e.season)))
        for i, e in enumerate(entries, 1):
            existing = [h for h in self.mgr.actual_harvests
                        if h.field_name == e.field_name and h.season == e.season]
            status = f" (已记录: {existing[0].actual_yield:.1f}kg)" if existing else ""
            print(f"    {i}. {e.field_name} - {e.season.value} - {e.crop_name}{status}")
        idx = input("  选择编号: ").strip()
        if not (idx.isdigit() and 1 <= int(idx) <= len(entries)):
            print("  无效选择")
            return
        entry = entries[int(idx) - 1]
        predicted = self.mgr.predict_yield(entry.field_name, entry.season, entry.crop_name)
        print(f"  预测产量: {predicted:.1f}kg")
        actual = input_float("  实际收成(kg): ")
        self.mgr.record_actual_harvest(entry.field_name, entry.season, entry.crop_name, actual)
        dev = actual - predicted
        dev_pct = (dev / predicted * 100) if predicted > 0 else 0
        print(f"  ✓ 已记录: 实际={actual:.1f}kg, 偏差={dev:+.1f}kg ({dev_pct:+.1f}%)")

    def _deviation_report(self):
        print("\n  === 偏差分析报告 ===")
        print("  1. 按季节  2. 全年  3. 返回")
        c = input("  选择: ").strip()
        if c == "1":
            season_labels = [s.value for s in SEASON_ORDER]
            si = select_from_list(season_labels, "选择季节")
            season = SEASON_ORDER[si]
            reports = self.mgr.deviation_analysis(season)
        elif c == "2":
            reports = self.mgr.deviation_analysis()
        else:
            return

        if not reports:
            print("  暂无实际收成记录可分析")
            return

        print(f"\n  {'农田':<10} {'季节':<6} {'作物':<6} {'预测(kg)':<12} "
              f"{'实际(kg)':<12} {'偏差(kg)':<12} {'偏差%':<10}")
        print_separator("─", 78)
        total_pred = total_actual = 0.0
        for r in reports:
            print(f"  {r['field']:<10} {r['season'].value:<6} {r['crop']:<6} "
                  f"{r['predicted_kg']:<12.1f} {r['actual_kg']:<12.1f} "
                  f"{r['deviation_kg']:<+12.1f} {r['deviation_pct']:<+10.1f}%")
            total_pred += r["predicted_kg"]
            total_actual += r["actual_kg"]
        if total_pred > 0:
            total_dev = total_actual - total_pred
            total_dev_pct = total_dev / total_pred * 100
            print_separator("─", 78)
            print(f"  {'合计':<10} {'':<6} {'':<6} {total_pred:<12.1f} {total_actual:<12.1f} "
                  f"{total_dev:<+12.1f} {total_dev_pct:<+10.1f}%")

    def _disaster_sim(self):
        print("\n  === 自然灾害模拟 ===")
        if self.mgr.disaster_records:
            print("  当前灾害记录:")
            for dr in self.mgr.disaster_records:
                fields_str = "、".join(dr.field_names)
                print(f"    {dr.disaster_type} ({dr.season.value}): "
                      f"影响农田={fields_str}, 严重度={dr.severity*100:.0f}%, "
                      f"触发方式={dr.triggered_mode}")
        else:
            print("  暂无灾害记录")

        print("\n  1. 手动触发灾害  2. 随机触发灾害  3. 清除所有灾害  4. 返回")
        c = input("  选择: ").strip()
        if c == "1":
            disaster_types = ["干旱", "洪涝", "霜冻", "虫害"]
            di = select_from_list(disaster_types, "灾害类型")
            season_labels = [s.value for s in SEASON_ORDER]
            si = select_from_list(season_labels, "影响季节")
            fnames = list(self.mgr.fields.keys())
            if not fnames:
                print("  没有农田")
                return
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
                disaster_types[di], SEASON_ORDER[si], field_names, severity)
            if err:
                print(f"  ✗ {err}")
            else:
                print(f"  ✓ {dr.disaster_type}已触发: 影响{len(dr.field_names)}块农田, "
                      f"减产{dr.severity*100:.0f}%")

        elif c == "2":
            dr = self.mgr.random_disaster()
            fields_str = "、".join(dr.field_names)
            print(f"  ✓ 随机灾害: {dr.disaster_type} ({dr.season.value}), "
                  f"影响={fields_str}, 减产{dr.severity*100:.0f}%")

        elif c == "3":
            self.mgr.clear_disasters()
            print("  ✓ 已清除所有灾害记录")

    def _fertilizer_advice(self):
        print("\n  === 肥料采购建议 ===")
        totals, details = self.mgr.calculate_fertilizer()
        if not details:
            print("  没有种植计划，无法计算肥料需求")
            return

        print(f"\n  {'农田':<10} {'季节':<6} {'作物':<6} {'面积(亩)':<10} "
              f"{'N(kg)':<10} {'P(kg)':<10} {'K(kg)':<10}")
        print_separator("─", 68)
        for d in details:
            print(f"  {d['field']:<10} {d['season'].value:<6} {d['crop']:<6} "
                  f"{d['area']:<10.1f} {d['N']:<10.1f} {d['P']:<10.1f} {d['K']:<10.1f}")

        print_separator("─", 68)
        print(f"  {'合计':<10} {'':<6} {'':<6} {'':<10} "
              f"{totals['N']:<10.1f} {totals['P']:<10.1f} {totals['K']:<10.1f}")

        print(f"\n  📋 肥料采购建议:")
        print(f"    尿素(含N 46%):  {totals['N'] / 0.46:.1f} kg")
        print(f"    过磷酸钙(含P₂O₅ 16%):  {totals['P'] / 0.16:.1f} kg (P→P₂O₅换算: {totals['P']*2.29:.1f} kg P₂O₅)")
        print(f"    氯化钾(含K₂O 60%):  {totals['K'] / 0.60:.1f} kg (K→K₂O换算: {totals['K']*1.20:.1f} kg K₂O)")
        print(f"\n  建议额外采购10%余量以应对损耗:")
        print(f"    尿素:  {totals['N'] / 0.46 * 1.1:.1f} kg")
        print(f"    过磷酸钙:  {totals['P'] / 0.16 * 1.1:.1f} kg")
        print(f"    氯化钾:  {totals['K'] / 0.60 * 1.1:.1f} kg")

    def _export_csv(self):
        print("\n  === 导出种植计划 ===")
        filepath = input("  导出文件名 (默认: planting_plan.csv): ").strip()
        if not filepath:
            filepath = "planting_plan.csv"
        if not filepath.endswith(".csv"):
            filepath += ".csv"
        result = self.mgr.export_plan_csv(filepath)
        print(f"  ✓ 种植计划已导出到: {result}")

    def _view_calendar(self):
        print()
        self.mgr.generate_calendar()

    def _configure_prices(self):
        print("\n  === 配置作物价格 ===")
        print("  当前价格 (元/kg):")
        for name, price in self.mgr.prices.items():
            print(f"    {name}: ¥{price:.2f}")
        print("\n  1. 修改价格  2. 添加新作物价格  3. 返回")
        c = input("  选择: ").strip()
        if c in ("1", "2"):
            name = input("  作物名称: ").strip()
            if name not in self.mgr.prices:
                print("  新作物价格条目")
            price = input_float("  价格(元/kg): ")
            self.mgr.prices[name] = price
            self.mgr._save()
            print(f"  ✓ {name} 价格已设为 ¥{price:.2f}/kg")

    def _exit(self):
        print("\n  再见! 🌾")
        raise SystemExit(0)


if __name__ == "__main__":
    cli = CLI()
    cli.run()
