#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nonindustrial（非工业行业财务看板）数据接入工具
-------------------------------------------------
用法：
  1. 在 nonindustrial_template.csv 中按列填写每个行业各年度的
     营业收入(亿元) / 净利润(亿元) / ROE(%)（留空=暂无数据）。
  2. 运行：  python csv_to_json.py
     本脚本会：
       - 读取 CSV，按 (行业, 期次) 映射到 data 数组；
       - 覆盖 nonindustrial_data.json（保留 meta 与行业/期次顺序）；
       - 用 nonindustrial_template.html 重新生成 nonindustrial.html。
依赖：仅标准库（json / csv / os）。
"""
import json, csv, os

BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(BASE, "nonindustrial_template.html")
DATA = os.path.join(BASE, "nonindustrial_data.json")
CSV = os.path.join(BASE, "nonindustrial_template.csv")
OUT = os.path.join(BASE, "nonindustrial.html")

METRICS = ("revenue", "profit", "roe")


def to_num(x):
    x = (x or "").strip()
    if x == "" or x.lower() in ("null", "nan", "-", "—", "暂无"):
        return None
    try:
        return float(x)
    except ValueError:
        return None


def build_html():
    tpl = open(TEMPLATE, encoding="utf-8").read()
    data = open(DATA, encoding="utf-8").read()
    json.loads(data)  # 校验 JSON 合法性
    open(OUT, "w", encoding="utf-8").write(tpl.replace("__DATA__", data))
    print("✓ 已重新生成", os.path.relpath(OUT, BASE))


def main():
    if not os.path.exists(DATA):
        raise SystemExit("✗ 找不到 nonindustrial_data.json，请先确认文件存在")
    with open(DATA, encoding="utf-8") as f:
        j = json.load(f)
    industries = list(j.get("industries", []))
    periods = list(j.get("periods", []))

    # 读取 CSV
    rec = {}
    with open(CSV, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            name = (row.get("行业") or "").strip()
            per = (row.get("期次") or row.get("期次(年)") or "").strip()
            if not name or not per:
                continue
            rec[(name, per)] = {
                "revenue": to_num(row.get("营业收入(亿元)")),
                "profit": to_num(row.get("净利润(亿元)")),
                "roe": to_num(row.get("ROE(%)")),
            }

    # 重建 data（沿用既有行业/期次顺序，缺失填 null）
    data_out = {}
    for name in industries:
        data_out[name] = {m: [] for m in METRICS}
        for per in periods:
            v = rec.get((name, per), {})
            for m in METRICS:
                data_out[name][m].append(v.get(m))

    j["data"] = data_out
    j["periods"] = periods
    j["period_labels"] = periods
    j["industries"] = industries
    j.setdefault("meta", {})["note"] = "由 nonindustrial_template.csv 经 csv_to_json.py 生成"

    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False, indent=2)
    print("✓ 已更新", os.path.relpath(DATA, BASE))

    build_html()


if __name__ == "__main__":
    main()
