#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
电商用户购买意向分析与转化预测 —— 全量指标计算脚本
================================================================
数据源 : data/processed/session_cleaned.csv   (12205 行 × 22 列, 已去重)
输出   : data/processed/analysis.json          全部分析口径数值（供全队文档取数）
         data/processed/model_metrics.json     两模型指标 + 混淆矩阵 + 特征重要性
         data/processed/analysis_summary.md    人读版结论文档
         MySQL shopping_analytics.dws_model_result / dws_feature_importance

口径约定（与 PROJECT_SPEC.md 对齐）
  - 总会话数 12205（12330 原始 - 125 完全重复行）
  - 转化率 = Revenue=1 的会话数 / 总会话数
  - 跳出率 KPI 采用数据集字段 BounceRates 的会话均值（bounceSessionRate 为
    BounceRates>=0.2 的会话占比，作为补充口径）
  - 退出率 KPI 采用 ExitRates 的会话均值
  - 平均页面深度 = page_depth 均值；平均停留 = total_duration 均值（秒）
  - 月度趋势 1-12 月补全，数据集中无 Jan、Apr 的会话，补 0
  - OS/Browser/Region/TrafficType 为匿名编码，仅按编码分组，不臆造语义标签

所有数字均由本脚本真实计算产生，禁止手填。
"""
import io
import json
import os
import sys
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd
import pymysql
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

BASE = os.path.dirname(os.path.abspath(__file__))          # ...\shopping-analytics\data
PROC = os.path.join(BASE, "processed")
RAW = os.path.join(BASE, "raw")
os.makedirs(PROC, exist_ok=True)

DB = dict(host="localhost", user="root", password="123456",
          charset="utf8mb4", database="shopping_analytics",
          cursorclass=pymysql.cursors.DictCursor, autocommit=False)

MONTH_CN = {1: "1月", 2: "2月", 3: "3月", 4: "4月", 5: "5月", 6: "6月",
            7: "7月", 8: "8月", 9: "9月", 10: "10月", 11: "11月", 12: "12月"}
MONTH_EN = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "June",
            7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}

FEATURE_CN = {
    "Administrative": "管理类页面访问数",
    "Administrative_Duration": "管理类停留时长",
    "Informational": "信息类页面访问数",
    "Informational_Duration": "信息类停留时长",
    "ProductRelated": "商品类页面访问数",
    "ProductRelated_Duration": "商品类停留时长",
    "BounceRates": "跳出率",
    "ExitRates": "退出率",
    "PageValues": "页面价值分",
    "SpecialDay": "特殊日期接近度",
    "OperatingSystems": "操作系统编码",
    "Browser": "浏览器编码",
    "Region": "区域编码",
    "TrafficType": "流量类型编码",
    "Weekend": "是否周末",
    "Month": "访问月份",
    "VisitorType": "访客类型",
    "page_depth": "页面访问深度",
    "total_duration": "总停留时长",
    "weekend_i": "是否周末",
}


# ---------------------------------------------------------------- 小工具
def r4(x):
    """比率/指标统一保留 4 位小数"""
    return round(float(x), 4)


def r2(x):
    return round(float(x), 2)


def to_native(o):
    """numpy / pandas 类型 -> 原生 python，保证 json 可序列化"""
    if isinstance(o, dict):
        return {str(k): to_native(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_native(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def agg_stats(g):
    """按任意分组键聚合出 sessions/conversions/conversionRate 等标准字段"""
    out = []
    for key, sub in g:
        sessions = int(len(sub))
        convs = int(sub["revenue_i"].sum())
        out.append({
            "key": key[0] if isinstance(key, tuple) and len(key) == 1 else key,
            "sessions": sessions,
            "conversions": convs,
            "conversionRate": r4(convs / sessions) if sessions else 0.0,
            "pct": r4(sessions / TOTAL),
            "avgPageDepth": r4(sub["page_depth"].mean()),
            "avgDuration": r4(sub["total_duration"].mean()),
            "avgBounceRate": r4(sub["BounceRates"].mean()),
            "avgExitRate": r4(sub["ExitRates"].mean()),
            "avgPageValues": r4(sub["PageValues"].mean()),
        })
    return out


def bins_kpi(sub, label, label_key="binLabel"):
    """label_key 用于对齐后端接口字段名：
    页面深度分层 -> depthLabel，跳出/退出率分箱 -> rangeLabel，PageValues -> binLabel
    """
    sessions = int(len(sub))
    convs = int(sub["revenue_i"].sum())
    return {
        label_key: label,
        "binLabel": label,
        "sessions": sessions,
        "conversions": convs,
        "conversionRate": r4(convs / sessions) if sessions else 0.0,
        "pct": r4(sessions / TOTAL),
        "avgPageValues": r4(sub["PageValues"].mean()) if sessions else 0.0,
    }


print("=" * 74)
print("STEP 1  载入清洗后明细")
print("=" * 74)
CSV = os.path.join(PROC, "session_cleaned.csv")
df = pd.read_csv(CSV)
TOTAL = int(len(df))
RAW_CSV = os.path.join(RAW, "online_shoppers_intention.csv")
raw_rows = int(len(pd.read_csv(RAW_CSV))) if os.path.exists(RAW_CSV) else None
print(f"清洗后明细 : {df.shape[0]} 行 × {df.shape[1]} 列   (源文件 {raw_rows} 行)")
assert TOTAL == 12205, f"expect 12205 rows, got {TOTAL}"
assert df.isnull().sum().sum() == 0, "存在缺失值"

CONV = int(df["revenue_i"].sum())
print(f"成交会话   : {CONV}   转化率 {CONV / TOTAL * 100:.2f}%")

analysis = {}

# ---------------------------------------------------------------- 0. 元信息
analysis["meta"] = {
    "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "sourceFile": "data/raw/online_shoppers_intention.csv",
    "cleanFile": "data/processed/session_cleaned.csv",
    "rawRows": raw_rows,
    "rawColumns": 18,
    "removedDuplicates": (raw_rows - TOTAL) if raw_rows else 125,
    "cleanRows": TOTAL,
    "cleanColumns": int(df.shape[1]),
    "targetColumn": "Revenue",
    "conversionRate": r4(CONV / TOTAL),
    "monthCoverage": sorted(int(m) for m in df["month_num"].unique()),
    "monthMissing": [m for m in range(1, 13) if m not in set(df["month_num"].unique())],
    "note": "OS/Browser/Region/TrafficType 为原始数据集匿名编码，未提供编码字典，"
            "全部按编码分组分析，不映射业务名称。",
}

# ---------------------------------------------------------------- 1. 全局 KPI
print("\n" + "=" * 74)
print("STEP 2  全局 KPI")
print("=" * 74)
new_n = int((df["visitor_type"] == "New_Visitor").sum())
ret_n = int((df["visitor_type"] == "Returning_Visitor").sum())
oth_n = int((df["visitor_type"] == "Other").sum())
weekend_n = int((df["weekend_i"] == 1).sum())

analysis["globalKpi"] = {
    "totalSessions": TOTAL,
    "totalRevenue": CONV,
    "conversionRate": r4(CONV / TOTAL),
    "avgPageDepth": r4(df["page_depth"].mean()),
    "avgDuration": r4(df["total_duration"].mean()),
    "bounceRate": r4(df["BounceRates"].mean()),
    "exitRate": r4(df["ExitRates"].mean()),
    "newVisitorRate": r4(new_n / TOTAL),
    "returningRate": r4(ret_n / TOTAL),
    "otherVisitorRate": r4(oth_n / TOTAL),
    # 补充口径
    "bounceSessionRate": r4(df["is_bounce"].mean()),
    "newVisitorSessions": new_n,
    "returningSessions": ret_n,
    "otherSessions": oth_n,
    "weekendSessions": weekend_n,
    "weekendRate": r4(weekend_n / TOTAL),
    "avgProductRelated": r4(df["ProductRelated"].mean()),
    "avgPageValues": r4(df["PageValues"].mean()),
    "zeroPageValuesRate": r4((df["PageValues"] == 0).mean()),
    "nonZeroPageValuesSessions": int((df["PageValues"] > 0).sum()),
    "revenueFromNonZeroPageValues": r4(
        df.loc[df["PageValues"] > 0, "revenue_i"].sum() / CONV),
    "avgSpecialDay": r4(df["SpecialDay"].mean()),
}
for k, v in analysis["globalKpi"].items():
    print(f"  {k:32s}: {v}")

# ---------------------------------------------------------------- 2. 月度趋势
print("\n" + "=" * 74)
print("STEP 3  月度趋势（1-12 月补全）")
print("=" * 74)
monthly = []
for m in range(1, 13):
    sub = df[df["month_num"] == m]
    sessions = int(len(sub))
    convs = int(sub["revenue_i"].sum())
    monthly.append({
        "monthNum": m,
        "monthName": MONTH_EN[m],
        "monthCn": MONTH_CN[m],
        "sessions": sessions,
        "conversions": convs,
        "conversionRate": r4(convs / sessions) if sessions else 0.0,
        "pct": r4(sessions / TOTAL),
        "avgPageDepth": r4(sub["page_depth"].mean()) if sessions else 0.0,
        "avgDuration": r4(sub["total_duration"].mean()) if sessions else 0.0,
        "avgPageValues": r4(sub["PageValues"].mean()) if sessions else 0.0,
        "avgBounceRate": r4(sub["BounceRates"].mean()) if sessions else 0.0,
        "hasData": sessions > 0,
    })
    print(f"  {m:2d} {MONTH_EN[m]:5s} sessions={sessions:5d} conv={convs:4d} "
          f"rate={monthly[-1]['conversionRate'] * 100:5.2f}%")
analysis["monthlyTrend"] = monthly
peak_m = max([x for x in monthly if x["hasData"]], key=lambda x: x["sessions"])
best_m = max([x for x in monthly if x["hasData"]], key=lambda x: x["conversionRate"])
worst_m = min([x for x in monthly if x["hasData"]], key=lambda x: x["conversionRate"])
analysis["monthlyInsight"] = {
    "peakMonth": peak_m["monthCn"],
    "peakMonthSessions": peak_m["sessions"],
    "peakMonthPct": r4(peak_m["sessions"] / TOTAL),
    "highestConversionMonth": best_m["monthCn"],
    "highestConversionRate": best_m["conversionRate"],
    "lowestConversionMonth": worst_m["monthCn"],
    "lowestConversionRate": worst_m["conversionRate"],
}

# ---------------------------------------------------------------- 3. 访客类型
print("\n" + "=" * 74)
print("STEP 4  访客类型对比")
print("=" * 74)
vt = []
for key, sub in df.groupby("visitor_type"):
    row = agg_stats([(key, sub)])[0]
    vt.append({
        "visitorType": row["key"],
        "sessions": row["sessions"],
        "conversions": row["conversions"],
        "conversionRate": row["conversionRate"],
        "pct": row["pct"],
        "avgPageDepth": row["avgPageDepth"],
        "avgDuration": row["avgDuration"],
        "avgBounceRate": row["avgBounceRate"],
        "avgExitRate": row["avgExitRate"],
        "avgPageValues": row["avgPageValues"],
    })
vt.sort(key=lambda x: -x["sessions"])
analysis["visitorType"] = vt
for x in vt:
    print(f"  {x['visitorType']:20s} sessions={x['sessions']:5d} conv={x['conversions']:4d} "
          f"rate={x['conversionRate'] * 100:5.2f}% 占比={x['pct'] * 100:5.2f}%")

# ---------------------------------------------------------------- 4. 流量类型 Top10
print("\n" + "=" * 74)
print("STEP 5  流量类型 Top10（按会话量）")
print("=" * 74)
tt_all = []
for key, sub in df.groupby("TrafficType"):
    row = agg_stats([(key, sub)])[0]
    tt_all.append({
        "trafficType": int(key),
        "sessions": row["sessions"],
        "conversions": row["conversions"],
        "conversionRate": row["conversionRate"],
        "pct": row["pct"],
        "avgPageDepth": row["avgPageDepth"],
        "avgDuration": row["avgDuration"],
        "avgPageValues": row["avgPageValues"],
        "avgBounceRate": row["avgBounceRate"],
        "avgExitRate": row["avgExitRate"],
    })
tt_all.sort(key=lambda x: -x["sessions"])
analysis["trafficSource"] = tt_all[:10]
analysis["trafficTypeAll"] = tt_all
# 高效率渠道（样本量 >= 100 时按转化率排序，避免小样本假象）
eligible = [x for x in tt_all if x["sessions"] >= 100]
eligible.sort(key=lambda x: -x["conversionRate"])
analysis["trafficEfficiencyTop5"] = eligible[:5]
analysis["trafficEfficiencyMinSessions"] = 100
for x in tt_all[:10]:
    print(f"  TrafficType {x['trafficType']:2d} sessions={x['sessions']:5d} "
          f"conv={x['conversions']:4d} rate={x['conversionRate'] * 100:5.2f}%")

# ---------------------------------------------------------------- 5. 页面深度分层
print("\n" + "=" * 74)
print("STEP 6  页面深度分层")
print("=" * 74)
DEPTH_BINS = [(0, 5, "1-5"), (5, 15, "6-15"), (15, 30, "16-30"),
              (30, 60, "31-60"), (60, np.inf, "60+")]
depth_res = []
for lo, hi, label in DEPTH_BINS:
    # 首个区间下界取 -inf 以纳入 6 条 page_depth=0 的极短会话
    sub = df[(df["page_depth"] > lo) & (df["page_depth"] <= hi)] if lo > 0 \
        else df[df["page_depth"] <= hi]
    depth_res.append(bins_kpi(sub, label, "depthLabel"))
    print(f"  {label:6s} sessions={depth_res[-1]['sessions']:5d} "
          f"conv={depth_res[-1]['conversions']:4d} rate={depth_res[-1]['conversionRate'] * 100:5.2f}%")
assert sum(x["sessions"] for x in depth_res) == TOTAL, "深度分层覆盖不完整"
analysis["pageDepthBins"] = depth_res
analysis["pageDepthZeroSessions"] = int((df["page_depth"] == 0).sum())

# ---------------------------------------------------------------- 6. 跳出/退出率分箱
print("\n" + "=" * 74)
print("STEP 7  跳出率 / 退出率分箱")
print("=" * 74)
RATE_BINS = [(0, 0, "=0"), (0, 0.02, "0-0.02"), (0.02, 0.05, "0.02-0.05"),
             (0.05, 0.10, "0.05-0.1"), (0.10, 0.20, "0.1-0.2")]
bounce_res, exit_res = [], []
for lo, hi, label in RATE_BINS:
    if label == "=0":
        sb = df[df["BounceRates"] == 0]
        se = df[df["ExitRates"] == 0]
    else:
        sb = df[(df["BounceRates"] > lo) & (df["BounceRates"] <= hi)]
        se = df[(df["ExitRates"] > lo) & (df["ExitRates"] <= hi)]
    bounce_res.append(bins_kpi(sb, label, "rangeLabel"))
    exit_res.append(bins_kpi(se, label, "rangeLabel"))
    print(f"  {label:10s} bounce: n={bounce_res[-1]['sessions']:5d} "
          f"rate={bounce_res[-1]['conversionRate'] * 100:5.2f}%   |   "
          f"exit: n={exit_res[-1]['sessions']:5d} rate={exit_res[-1]['conversionRate'] * 100:5.2f}%")
assert sum(x["sessions"] for x in bounce_res) == TOTAL, "跳出率分箱覆盖不完整"
assert sum(x["sessions"] for x in exit_res) == TOTAL, "退出率分箱覆盖不完整"
analysis["bounceRateBins"] = bounce_res
analysis["exitRateBins"] = exit_res

# ---------------------------------------------------------------- 7. 区域分布
print("\n" + "=" * 74)
print("STEP 8  区域分布（匿名编码 1-9）")
print("=" * 74)
region_res = []
for key, sub in df.groupby("Region"):
    row = agg_stats([(key, sub)])[0]
    region_res.append({
        "region": int(key),
        "sessions": row["sessions"],
        "conversions": row["conversions"],
        "conversionRate": row["conversionRate"],
        "pct": row["pct"],
        "avgPageDepth": row["avgPageDepth"],
        "avgDuration": row["avgDuration"],
        "avgPageValues": row["avgPageValues"],
    })
region_res.sort(key=lambda x: -x["sessions"])
analysis["region"] = region_res
for x in region_res:
    print(f"  Region {x['region']} sessions={x['sessions']:5d} "
          f"conv={x['conversions']:4d} rate={x['conversionRate'] * 100:5.2f}% 占比={x['pct'] * 100:5.2f}%")

# ---------------------------------------------------------------- 8. 周末对比
print("\n" + "=" * 74)
print("STEP 9  周末 / 工作日对比")
print("=" * 74)
weekend_res = []
for key in [0, 1]:
    sub = df[df["weekend_i"] == key]
    sessions = int(len(sub))
    convs = int(sub["revenue_i"].sum())
    weekend_res.append({
        "weekend": key,
        "weekendLabel": "周末" if key == 1 else "工作日",
        "sessions": sessions,
        "conversions": convs,
        "conversionRate": r4(convs / sessions),
        "pct": r4(sessions / TOTAL),
        "avgPageDepth": r4(sub["page_depth"].mean()),
        "avgDuration": r4(sub["total_duration"].mean()),
        "avgPageValues": r4(sub["PageValues"].mean()),
        "avgBounceRate": r4(sub["BounceRates"].mean()),
        "avgExitRate": r4(sub["ExitRates"].mean()),
    })
    print(f"  {weekend_res[-1]['weekendLabel']:4s} sessions={sessions:5d} conv={convs:4d} "
          f"rate={weekend_res[-1]['conversionRate'] * 100:5.2f}%")
analysis["weekend"] = weekend_res
wd, we = weekend_res[0], weekend_res[1]
analysis["weekendInsight"] = {
    "conversionGapPct": r4((we["conversionRate"] - wd["conversionRate"]) * 100),
    "depthGap": r4(we["avgPageDepth"] - wd["avgPageDepth"]),
    "durationGap": r4(we["avgDuration"] - wd["avgDuration"]),
}

# ---------------------------------------------------------------- 9. PageValues 分箱
print("\n" + "=" * 74)
print("STEP 10 PageValues 价值分箱")
print("=" * 74)
PV_BINS = [(0, 0, "=0"), (0, 10, "0-10"), (10, 30, "10-30"),
           (30, 60, "30-60"), (60, 100, "60-100"), (100, np.inf, "100+")]
pv_res = []
for lo, hi, label in PV_BINS:
    if label == "=0":
        sub = df[df["PageValues"] == 0]
    else:
        sub = df[(df["PageValues"] > lo) & (df["PageValues"] <= hi)]
    pv_res.append(bins_kpi(sub, label))
    print(f"  {label:8s} sessions={pv_res[-1]['sessions']:5d} "
          f"conv={pv_res[-1]['conversions']:4d} rate={pv_res[-1]['conversionRate'] * 100:5.2f}%")
assert sum(x["sessions"] for x in pv_res) == TOTAL, "PageValues 分箱覆盖不完整"
analysis["pageValuesBins"] = pv_res
analysis["pageValuesMax"] = r4(df["PageValues"].max())

# ---------------------------------------------------------------- 10. 特殊日期效应
print("\n" + "=" * 74)
print("STEP 11 特殊日期效应")
print("=" * 74)
sd_res = []
for key, sub in df.groupby("SpecialDay"):
    sessions = int(len(sub))
    convs = int(sub["revenue_i"].sum())
    sd_res.append({
        "specialDay": round(float(key), 2),
        "sessions": sessions,
        "conversions": convs,
        "conversionRate": r4(convs / sessions) if sessions else 0.0,
        "pct": r4(sessions / TOTAL),
        "avgPageValues": r4(sub["PageValues"].mean()) if sessions else 0.0,
        "avgBounceRate": r4(sub["BounceRates"].mean()) if sessions else 0.0,
    })
sd_res.sort(key=lambda x: x["specialDay"])
analysis["specialDay"] = sd_res
for x in sd_res:
    print(f"  SpecialDay={x['specialDay']:.1f} sessions={x['sessions']:5d} "
          f"conv={x['conversions']:4d} rate={x['conversionRate'] * 100:5.2f}% 占比={x['pct'] * 100:5.2f}%")
normal = df[df["SpecialDay"] == 0]
sp = df[df["SpecialDay"] > 0]
analysis["specialDayCompare"] = {
    "normalSessions": int(len(normal)),
    "normalConversionRate": r4(normal["revenue_i"].mean()),
    "specialSessions": int(len(sp)),
    "specialConversionRate": r4(sp["revenue_i"].mean()),
    "nearZeroSessions": int((df["SpecialDay"].between(0.2, 0.4, inclusive="both")).sum()),
    "nearZeroConversionRate": r4(
        df[df["SpecialDay"].between(0.2, 0.4, inclusive="both")]["revenue_i"].mean()),
    "nearOnesSessions": int((df["SpecialDay"] >= 0.8).sum()),
    "nearOnesConversionRate": r4(df[df["SpecialDay"] >= 0.8]["revenue_i"].mean()),
}

# ---------------------------------------------------------------- 11. OS / Browser 构成
print("\n" + "=" * 74)
print("STEP 12 操作系统 / 浏览器构成（匿名编码）")
print("=" * 74)
os_res = []
for key, sub in df.groupby("OperatingSystems"):
    sessions = int(len(sub))
    convs = int(sub["revenue_i"].sum())
    os_res.append({
        "osCode": int(key),
        "osName": f"OS-{int(key)}",
        "sessions": sessions,
        "conversions": convs,
        "conversionRate": r4(convs / sessions),
        "pct": r4(sessions / TOTAL),
    })
os_res.sort(key=lambda x: -x["sessions"])
browser_res = []
for key, sub in df.groupby("Browser"):
    sessions = int(len(sub))
    convs = int(sub["revenue_i"].sum())
    browser_res.append({
        "browser": int(key),
        "browserName": f"Browser-{int(key)}",
        "sessions": sessions,
        "conversions": convs,
        "conversionRate": r4(convs / sessions),
        "pct": r4(sessions / TOTAL),
    })
browser_res.sort(key=lambda x: -x["sessions"])
analysis["os"] = os_res
analysis["browser"] = browser_res
analysis["osTop3Pct"] = r4(sum(x["pct"] for x in os_res[:3]))
analysis["browserTop3Pct"] = r4(sum(x["pct"] for x in browser_res[:3]))
for x in os_res:
    print(f"  OS-{x['osCode']}  sessions={x['sessions']:5d} rate={x['conversionRate'] * 100:5.2f}% 占比={x['pct'] * 100:5.2f}%")
for x in browser_res[:6]:
    print(f"  Browser-{x['browser']:2d} sessions={x['sessions']:5d} "
          f"rate={x['conversionRate'] * 100:5.2f}% 占比={x['pct'] * 100:5.2f}%")

# ---------------------------------------------------------------- 12. 访客类型 × 周末
print("\n" + "=" * 74)
print("STEP 13 访客类型 × 周末 交叉（热力数据）")
print("=" * 74)
vt_order = [x["visitorType"] for x in vt]
cross = []
for v in vt_order:
    for w in [0, 1]:
        sub = df[(df["visitor_type"] == v) & (df["weekend_i"] == w)]
        sessions = int(len(sub))
        convs = int(sub["revenue_i"].sum())
        cross.append({
            "visitorType": v,
            "weekend": w,
            "weekendLabel": "周末" if w == 1 else "工作日",
            "sessions": sessions,
            "conversions": convs,
            "conversionRate": r4(convs / sessions) if sessions else 0.0,
        })
analysis["visitorTypeWeekend"] = cross
for x in cross:
    print(f"  {x['visitorType']:20s} {x['weekendLabel']:4s} n={x['sessions']:5d} "
          f"rate={x['conversionRate'] * 100:5.2f}%")

# ---------------------------------------------------------------- 13. 相关性（辅助分析）
corr_cols = ["Administrative", "Informational", "ProductRelated", "PageValues",
             "BounceRates", "ExitRates", "SpecialDay", "page_depth",
             "total_duration", "weekend_i"]
corr = df[corr_cols + ["revenue_i"]].corr()["revenue_i"].drop("revenue_i")
analysis["correlationWithRevenue"] = [
    {"feature": k, "featureCn": FEATURE_CN.get(k, k), "corr": r4(v)}
    for k, v in corr.sort_values(ascending=False).items()
]
print("\n" + "=" * 74)
print("STEP 14 与成交的相关性（Pearson）")
print("=" * 74)
for x in analysis["correlationWithRevenue"]:
    print(f"  {x['feature']:24s} {x['corr']:+.4f}")

# ---------------------------------------------------------------- 14. 建模
print("\n" + "=" * 74)
print("STEP 15 转化预测建模（LogisticRegression / RandomForest）")
print("=" * 74)
NUM_FEATS = ["Administrative", "Administrative_Duration", "Informational",
             "Informational_Duration", "ProductRelated", "ProductRelated_Duration",
             "BounceRates", "ExitRates", "PageValues", "SpecialDay",
             "OperatingSystems", "Browser", "Region", "TrafficType", "weekend_i"]
CAT_FEATS = ["Month", "visitor_type"]

X_num = df[NUM_FEATS].astype(float)
X_cat = pd.get_dummies(df[CAT_FEATS].astype(str), prefix=["Month", "VisitorType"], dtype=float)
X = pd.concat([X_num, X_cat], axis=1)
y = df["revenue_i"].astype(int)
print(f"特征矩阵 : {X.shape[0]} 行 × {X.shape[1]} 列（数值 {len(NUM_FEATS)} + 独热 {X_cat.shape[1]}）")
print(f"正负样本 : 成交 {int(y.sum())} / 未成交 {int((1 - y).sum())}")

X_tr, X_te, y_tr, y_te = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)
print(f"训练集 {X_tr.shape[0]} 行（成交 {int(y_tr.sum())}） / "
      f"测试集 {X_te.shape[0]} 行（成交 {int(y_te.sum())}）")

models = {
    "LogisticRegression": Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, random_state=42)),
    ]),
    "RandomForest": RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1),
}

model_rows, metrics_by_model, confusion_by_model = [], {}, {}
for name, mdl in models.items():
    mdl.fit(X_tr, y_tr)
    pred = mdl.predict(X_te)
    proba = mdl.predict_proba(X_te)[:, 1]
    cm = confusion_matrix(y_te, pred, labels=[0, 1])
    tn, fp, fn, tp = int(cm[0][0]), int(cm[0][1]), int(cm[1][0]), int(cm[1][1])
    m = {
        "modelName": name,
        "accuracy": r4(accuracy_score(y_te, pred)),
        "auc": r4(roc_auc_score(y_te, proba)),
        "precision": r4(precision_score(y_te, pred, zero_division=0)),
        "recall": r4(recall_score(y_te, pred, zero_division=0)),
        "f1": r4(f1_score(y_te, pred, zero_division=0)),
    }
    metrics_by_model[name] = m
    confusion_by_model[name] = {"modelName": name, "tp": tp, "fp": fp,
                                "tn": tn, "fn": fn}
    for metric in ["accuracy", "auc", "precision", "recall", "f1"]:
        model_rows.append({"modelName": name, "metricName": metric,
                           "metricValue": m[metric]})
    # 与后端约定：混淆矩阵四格也落在 dws_model_result，metric_name=tp/fp/tn/fn
    for mk, mv in [("tp", tp), ("fp", fp), ("tn", tn), ("fn", fn)]:
        model_rows.append({"modelName": name, "metricName": mk,
                           "metricValue": float(mv)})
    print(f"\n  [{name}]")
    print(f"    accuracy={m['accuracy']:.4f}  auc={m['auc']:.4f}  "
          f"precision={m['precision']:.4f}  recall={m['recall']:.4f}  f1={m['f1']:.4f}")
    print(f"    混淆矩阵: TP={tp} FP={fp} TN={tn} FN={fn}")

best_model = max(metrics_by_model, key=lambda k: metrics_by_model[k]["auc"])
print(f"\n  以 AUC 为准则的最优模型: {best_model} (AUC={metrics_by_model[best_model]['auc']})")

# ---- 特征重要性：RandomForest 基尼重要性，独热列聚合回原始特征 ----
rf = models["RandomForest"]
imp = dict(zip(X.columns, rf.feature_importances_))
agg = {}
for col, val in imp.items():
    if col.startswith("VisitorType_"):
        base = "VisitorType"
    elif col.startswith("Month_"):
        base = "Month"
    else:
        base = col
    agg[base] = agg.get(base, 0.0) + float(val)
importance_list = sorted(
    [{"featureKey": k, "featureCn": FEATURE_CN.get(k, k),
      "importance": round(v, 6), "rankNo": i + 1}
     for i, (k, v) in enumerate(sorted(agg.items(), key=lambda kv: -kv[1]))],
    key=lambda x: x["rankNo"])
importance_top12 = importance_list[:12]
print("\n  特征重要性 Top12（RandomForest, 独热列已聚合回原始特征）:")
for x in importance_top12:
    print(f"    {x['rankNo']:2d}. {x['featureKey']:24s} {x['featureCn']:12s} {x['importance']:.6f}")

# ---- 逻辑回归系数（Top12 by |coef|，补充可解释性）----
lr = models["LogisticRegression"].named_steps["clf"]
coefs = sorted(
    [{"feature": c, "coef": round(float(v), 4)} for c, v in zip(X.columns, lr.coef_[0])],
    key=lambda x: -abs(x["coef"]))
print("\n  逻辑回归系数 Top6（标准化后）:")
for x in coefs[:6]:
    print(f"    {x['feature']:24s} {x['coef']:+.4f}")

analysis["model"] = {
    "featureCount": int(X.shape[1]),
    "numericFeatureCount": len(NUM_FEATS),
    "dummyFeatureCount": int(X_cat.shape[1]),
    "trainRows": int(X_tr.shape[0]),
    "testRows": int(X_te.shape[0]),
    "trainPositive": int(y_tr.sum()),
    "testPositive": int(y_te.sum()),
    "bestModel": best_model,
    "metrics": [metrics_by_model[k] for k in ["LogisticRegression", "RandomForest"]],
    "confusion": [confusion_by_model[k] for k in ["LogisticRegression", "RandomForest"]],
    "featureImportance": importance_top12,
    "featureImportanceAll": importance_list,
    "lrCoefficientsTop12": coefs[:12],
}

model_metrics = {
    "generatedAt": analysis["meta"]["generatedAt"],
    "split": {"testSize": 0.2, "randomState": 42, "stratify": "Revenue",
              "trainRows": int(X_tr.shape[0]), "testRows": int(X_te.shape[0])},
    "metrics": analysis["model"]["metrics"],
    "confusion": analysis["model"]["confusion"],
    "featureImportance": importance_top12,
    "featureImportanceAll": importance_list,
    "lrCoefficientsTop12": coefs[:12],
    "bestModel": best_model,
    "bestMetricRule": "取测试集 AUC 最高者为最优模型，用于 is_best 标记",
}

# ---------------------------------------------------------------- 15. 关键结论（全部由计算结果生成）
print("\n" + "=" * 74)
print("STEP 16 生成结论要点")
print("=" * 74)
kpi = analysis["globalKpi"]
pv_nz = pv_res[-1]
depth_hi = depth_res[-1]
top_tt = analysis["trafficSource"][0]
best_tt = analysis["trafficEfficiencyTop5"][0]
insights = {
    "kpi": [
        f"清洗后有效会话 {kpi['totalSessions']} 条，成交 {kpi['totalRevenue']} 条，"
        f"整体转化率 {kpi['conversionRate'] * 100:.2f}%。",
        f"平均页面深度 {kpi['avgPageDepth']:.2f} 页，平均停留 {kpi['avgDuration']:.2f} 秒；"
        f"跳出率 {kpi['bounceRate'] * 100:.2f}%，退出率 {kpi['exitRate'] * 100:.2f}%。",
        f"新访客占比 {kpi['newVisitorRate'] * 100:.2f}%，回访客占比 "
        f"{kpi['returningRate'] * 100:.2f}%，其他访客占比 {kpi['otherVisitorRate'] * 100:.2f}%。",
        f"PageValues=0 的会话占 {kpi['zeroPageValuesRate'] * 100:.2f}%，"
        f"而全部成交中有 {kpi['revenueFromNonZeroPageValues'] * 100:.2f}% 来自 PageValues>0 的会话。",
    ],
    "structure": [
        f"访问高峰出现在 {peak_m['monthCn']}，会话 {peak_m['sessions']} 条，"
        f"占全年 {peak_m['pct'] * 100:.2f}%；数据集中无 Jan、Apr 记录，趋势图已按 1-12 月补 0。",
        f"转化率最高的月份为 {best_m['monthCn']}（{best_m['conversionRate'] * 100:.2f}%），"
        f"最低为 {worst_m['monthCn']}（{worst_m['conversionRate'] * 100:.2f}%）。",
        f"会话量最大的流量类型为 TrafficType {top_tt['trafficType']}（{top_tt['sessions']} 条，"
        f"转化率 {top_tt['conversionRate'] * 100:.2f}%）；样本量≥100 的渠道中转化效率最高的是 "
        f"TrafficType {best_tt['trafficType']}（{best_tt['conversionRate'] * 100:.2f}%）。",
        f"页面深度 60+ 的深度会话转化率 {depth_hi['conversionRate'] * 100:.2f}%，"
        f"远高于整体水平，深度浏览与成交高度正相关。",
    ],
    "leakage": [
        f"PageValues 100+ 分组会话 {pv_nz['sessions']} 条，转化率 "
        f"{pv_nz['conversionRate'] * 100:.2f}%；PageValues=0 分组转化率仅 "
        f"{pv_res[0]['conversionRate'] * 100:.2f}%，页面价值分是最强的成交前兆指标。",
        f"周末会话 {we['sessions']} 条转化率 {we['conversionRate'] * 100:.2f}%，"
        f"工作日 {wd['sessions']} 条转化率 {wd['conversionRate'] * 100:.2f}%，"
        f"相差 {abs(analysis['weekendInsight']['conversionGapPct']):.2f} 个百分点。",
        f"特殊日期接近度=0 的普通日会话转化率 "
        f"{analysis['specialDayCompare']['normalConversionRate'] * 100:.2f}%，"
        f"远离节假日（0.2-0.4）时转化率 "
        f"{analysis['specialDayCompare']['nearZeroConversionRate'] * 100:.2f}%。",
        f"操作系统 Top3 编码合计占 {analysis['osTop3Pct'] * 100:.2f}%，"
        f"浏览器 Top3 编码合计占 {analysis['browserTop3Pct'] * 100:.2f}%，终端分布高度集中。",
    ],
    "model": [
        f"逻辑回归 AUC {metrics_by_model['LogisticRegression']['auc']:.4f}、"
        f"F1 {metrics_by_model['LogisticRegression']['f1']:.4f}；"
        f"随机森林 AUC {metrics_by_model['RandomForest']['auc']:.4f}、"
        f"F1 {metrics_by_model['RandomForest']['f1']:.4f}。",
        f"以 AUC 为准则，{best_model} 表现更优，写入 dws_model_result 时标记 is_best=1。",
        f"随机森林最重要的前三个特征为 "
        + "、".join(f"{x['featureCn']}({x['importance']:.4f})" for x in importance_top12[:3]) + "。",
        "由于 PageValues 与 ExitRates 本身由站内行为统计而来，模型指标偏高属于业务可解释的"
        "“行为强相关”现象，解释时应强调其预警价值而非因果。",
    ],
}
analysis["insights"] = insights
for group, items in insights.items():
    for s in items:
        print(f"  [{group}] {s}")

# ---------------------------------------------------------------- 16. 落盘
print("\n" + "=" * 74)
print("STEP 17 写出 JSON / Markdown")
print("=" * 74)
P_ANALYSIS = os.path.join(PROC, "analysis.json")
P_MODEL = os.path.join(PROC, "model_metrics.json")

with open(P_ANALYSIS, "w", encoding="utf-8") as f:
    json.dump(to_native(analysis), f, ensure_ascii=False, indent=2)
with open(P_MODEL, "w", encoding="utf-8") as f:
    json.dump(to_native(model_metrics), f, ensure_ascii=False, indent=2)
print(f"  -> {P_ANALYSIS}  ({os.path.getsize(P_ANALYSIS) / 1024:.1f} KB)")
print(f"  -> {P_MODEL}  ({os.path.getsize(P_MODEL) / 1024:.1f} KB)")


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def pct(x, d=2):
    return f"{x * 100:.{d}f}%"


L = []
L.append("# 电商用户购买意向与转化预测 — 分析结果摘要\n")
L.append(f"> 数据源：`data/processed/session_cleaned.csv`（清洗后 {TOTAL} 行 × {df.shape[1]} 列，"
         f"原始 {raw_rows} 行去重去掉 {analysis['meta']['removedDuplicates']} 条完全重复记录）\n"
         f"> 生成时间：{analysis['meta']['generatedAt']}　生成脚本：`data/analysis.py`\n"
         f"> 全部数值由脚本真实计算，与 `analysis.json`、`model_metrics.json` 完全一致。\n")

L.append("## 1 全局 KPI\n")
L.append(md_table(["指标", "口径说明", "数值"], [
    ["总会话数", "去重后会话明细行数", kpi["totalSessions"]],
    ["成交会话数", "Revenue=1 的会话数", kpi["totalRevenue"]],
    ["整体转化率", "成交数 / 总会话数", pct(kpi["conversionRate"])],
    ["平均页面深度", "page_depth 均值（页）", f"{kpi['avgPageDepth']:.2f}"],
    ["平均停留时长", "total_duration 均值（秒）", f"{kpi['avgDuration']:.2f}"],
    ["跳出率", "BounceRates 会话均值", pct(kpi["bounceRate"])],
    ["退出率", "ExitRates 会话均值", pct(kpi["exitRate"])],
    ["新访客占比", "New_Visitor 会话占比", pct(kpi["newVisitorRate"])],
    ["回访客占比", "Returning_Visitor 会话占比", pct(kpi["returningRate"])],
    ["其他访客占比", "Other 会话占比", pct(kpi["otherVisitorRate"])],
    ["周末会话占比", "Weekend=1 会话占比", pct(kpi["weekendRate"])],
    ["PageValues=0 占比", "页面价值分为 0 的会话占比", pct(kpi["zeroPageValuesRate"])],
    ["成交中 PageValues>0 贡献", "PageValues>0 会话贡献的成交占比", pct(kpi["revenueFromNonZeroPageValues"])],
]))
L.append("")

L.append("## 2 月度访问与转化趋势（1-12 月补全）\n")
L.append(md_table(["月份", "会话数", "成交数", "转化率", "会话占比", "平均深度", "平均停留(s)"],
                  [[x["monthCn"], x["sessions"], x["conversions"], pct(x["conversionRate"]),
                    pct(x["pct"]), f"{x['avgPageDepth']:.2f}", f"{x['avgDuration']:.2f}"]
                   for x in monthly]))
L.append(f"\n说明：原始数据集不含 Jan、Apr 的会话记录，趋势图按 1-12 月补 0 以保证时间轴连续；"
         f"访问高峰为 {peak_m['monthCn']}（{peak_m['sessions']} 条，占 {pct(peak_m['pct'])}），"
         f"转化率最高 {best_m['monthCn']}（{pct(best_m['conversionRate'])}）。\n")

L.append("## 3 访客类型对比\n")
L.append(md_table(["访客类型", "会话数", "成交数", "转化率", "占比", "平均深度", "平均停留(s)", "平均PageValues"],
                  [[x["visitorType"], x["sessions"], x["conversions"], pct(x["conversionRate"]),
                    pct(x["pct"]), f"{x['avgPageDepth']:.2f}", f"{x['avgDuration']:.2f}",
                    f"{x['avgPageValues']:.2f}"] for x in vt]))
L.append("")

L.append("## 4 流量类型 Top10（按会话量，匿名编码）\n")
L.append(md_table(["流量类型", "会话数", "成交数", "转化率", "占比", "平均深度", "平均PageValues"],
                  [[f"TrafficType {x['trafficType']}", x["sessions"], x["conversions"],
                    pct(x["conversionRate"]), pct(x["pct"]), f"{x['avgPageDepth']:.2f}",
                    f"{x['avgPageValues']:.2f}"] for x in analysis["trafficSource"]]))
L.append(f"\n样本量≥{analysis['trafficEfficiencyMinSessions']} 的渠道中转化效率前 5："
         + "；".join(f"TrafficType {x['trafficType']}（{pct(x['conversionRate'])}，"
                     f"{x['sessions']} 条）" for x in analysis["trafficEfficiencyTop5"]) + "。\n")

L.append("## 5 页面访问深度分层\n")
L.append(md_table(["深度分层", "会话数", "成交数", "转化率", "占比"],
                  [[x["binLabel"], x["sessions"], x["conversions"], pct(x["conversionRate"]),
                    pct(x["pct"])] for x in depth_res]))
L.append(f"\n注：page_depth=0 的极短会话 {analysis['pageDepthZeroSessions']} 条并入 “1-5” 段统计。\n")

L.append("## 6 跳出率 / 退出率分箱\n")
L.append(md_table(["区间", "跳出率-会话数", "跳出率-成交数", "跳出率-转化率",
                   "退出率-会话数", "退出率-成交数", "退出率-转化率"],
                  [[b["binLabel"], b["sessions"], b["conversions"], pct(b["conversionRate"]),
                    e["sessions"], e["conversions"], pct(e["conversionRate"])]
                   for b, e in zip(bounce_res, exit_res)]))
L.append("")

L.append("## 7 区域分布（匿名编码 1-9）\n")
L.append(md_table(["区域编码", "会话数", "成交数", "转化率", "占比", "平均深度"],
                  [[f"Region {x['region']}", x["sessions"], x["conversions"],
                    pct(x["conversionRate"]), pct(x["pct"]), f"{x['avgPageDepth']:.2f}"]
                   for x in region_res]))
L.append("\n原始数据集未提供区域编码字典，仅按编码分组呈现，不做地理名称映射。\n")

L.append("## 8 周末与工作日对比\n")
L.append(md_table(["类型", "会话数", "成交数", "转化率", "占比", "平均深度", "平均停留(s)"],
                  [[x["weekendLabel"], x["sessions"], x["conversions"], pct(x["conversionRate"]),
                    pct(x["pct"]), f"{x['avgPageDepth']:.2f}", f"{x['avgDuration']:.2f}"]
                   for x in weekend_res]))
L.append("")

L.append("## 9 PageValues 价值分箱\n")
L.append(md_table(["分箱", "会话数", "成交数", "转化率", "占比"],
                  [[x["binLabel"], x["sessions"], x["conversions"], pct(x["conversionRate"]),
                    pct(x["pct"])] for x in pv_res]))
L.append("")

L.append("## 10 特殊日期效应\n")
L.append(md_table(["SpecialDay", "会话数", "成交数", "转化率", "占比"],
                  [[f"{x['specialDay']:.1f}", x["sessions"], x["conversions"],
                    pct(x["conversionRate"]), pct(x["pct"])] for x in sd_res]))
L.append(f"\n普通日（0）转化率 {pct(analysis['specialDayCompare']['normalConversionRate'])}，"
         f"节假日临近（0.2-0.4）转化率 {pct(analysis['specialDayCompare']['nearZeroConversionRate'])}，"
         f"节假日当天附近（≥0.8）转化率 {pct(analysis['specialDayCompare']['nearOnesConversionRate'])}。\n")

L.append("## 11 操作系统与浏览器构成（匿名编码）\n")
L.append(md_table(["操作系统编码", "会话数", "成交数", "转化率", "占比"],
                  [[f"OS-{x['osCode']}", x["sessions"], x["conversions"],
                    pct(x["conversionRate"]), pct(x["pct"])] for x in os_res]))
L.append("")
L.append(md_table(["浏览器编码", "会话数", "成交数", "转化率", "占比"],
                  [[f"Browser-{x['browser']}", x["sessions"], x["conversions"],
                    pct(x["conversionRate"]), pct(x["pct"])] for x in browser_res]))
L.append("")

L.append("## 12 访客类型 × 周末 交叉\n")
L.append(md_table(["访客类型", "类型", "会话数", "成交数", "转化率"],
                  [[x["visitorType"], x["weekendLabel"], x["sessions"], x["conversions"],
                    pct(x["conversionRate"])] for x in cross]))
L.append("")

L.append("## 13 转化预测模型评估\n")
L.append(md_table(["模型", "Accuracy", "AUC", "Precision", "Recall", "F1"],
                  [[m["modelName"], f"{m['accuracy']:.4f}", f"{m['auc']:.4f}",
                    f"{m['precision']:.4f}", f"{m['recall']:.4f}", f"{m['f1']:.4f}"]
                   for m in analysis["model"]["metrics"]]))
L.append("")
L.append(md_table(["模型", "TP", "FP", "TN", "FN"],
                  [[c["modelName"], c["tp"], c["fp"], c["tn"], c["fn"]]
                   for c in analysis["model"]["confusion"]]))
L.append(f"\n训练/测试划分：test_size=0.2，random_state=42，stratify=Revenue；"
         f"训练 {analysis['model']['trainRows']} 行，测试 {analysis['model']['testRows']} 行；"
         f"特征维度 {analysis['model']['featureCount']}（数值 {analysis['model']['numericFeatureCount']} "
         f"+ Month/VisitorType 独热 {analysis['model']['dummyFeatureCount']}）。"
         f"最优模型（AUC 准则）：**{best_model}**。\n")

L.append("## 14 特征重要性 Top12（RandomForest）\n")
L.append(md_table(["排名", "特征", "中文名", "重要性"],
                  [[x["rankNo"], x["featureKey"], x["featureCn"], f"{x['importance']:.6f}"]
                   for x in importance_top12]))
L.append("")

L.append("## 15 关键结论\n")
for group, title in [("kpi", "整体规模"), ("structure", "结构与流量"),
                     ("leakage", "转化与流失"), ("model", "模型")]:
    L.append(f"### 15.{['kpi', 'structure', 'leakage', 'model'].index(group) + 1} {title}\n")
    for s in insights[group]:
        L.append(f"- {s}")
    L.append("")

L.append("---\n")
L.append("附：完整数值见 `data/processed/analysis.json`，模型明细见 "
         "`data/processed/model_metrics.json`，两者与本文档同源同批次生成。\n")

P_SUM = os.path.join(PROC, "analysis_summary.md")
with open(P_SUM, "w", encoding="utf-8") as f:
    f.write("\n".join(L))
print(f"  -> {P_SUM}  ({os.path.getsize(P_SUM) / 1024:.1f} KB)")

# ---------------------------------------------------------------- 17. 写库
print("\n" + "=" * 74)
print("STEP 18 写入 MySQL：dws_model_result / dws_feature_importance")
print("=" * 74)
conn = pymysql.connect(**DB)
try:
    with conn.cursor() as cur:
        # 显式写 id 并重置 AUTO_INCREMENT，保证多次重跑后 id 仍稳定为 1..N，
        # 这样 Navicat 完整导出脚本（data/sql/shopping_analytics.sql）可重复还原。
        cur.execute("DELETE FROM dws_model_result")
        cur.executemany(
            "INSERT INTO dws_model_result (id, model_name, metric_name, metric_value, is_best) "
            "VALUES (%s, %s, %s, %s, %s)",
            [(i + 1, r["modelName"], r["metricName"], r["metricValue"],
              1 if r["modelName"] == best_model else 0) for i, r in enumerate(model_rows)])
        cur.execute("DELETE FROM dws_feature_importance")
        cur.executemany(
            "INSERT INTO dws_feature_importance (id, feature_key, feature_cn, importance, rank_no) "
            "VALUES (%s, %s, %s, %s, %s)",
            [(i + 1, x["featureKey"], x["featureCn"], x["importance"], x["rankNo"])
             for i, x in enumerate(importance_top12)])
        cur.execute("ALTER TABLE dws_model_result AUTO_INCREMENT = %s", (len(model_rows) + 1,))
        cur.execute("ALTER TABLE dws_feature_importance AUTO_INCREMENT = %s",
                    (len(importance_top12) + 1,))
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("SELECT model_name, metric_name, metric_value, is_best "
                    "FROM dws_model_result ORDER BY model_name, metric_name")
        rows = cur.fetchall()
        cur.execute("SELECT COUNT(*) AS c FROM dws_feature_importance")
        imp_cnt = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c, SUM(revenue) AS r, ROUND(AVG(revenue)*100,2) AS p "
                    "FROM ods_visitor_session")
        base = cur.fetchone()
    print(f"  dws_model_result      : {len(rows)} 行")
    print(f"  dws_feature_importance: {imp_cnt} 行")
    print(f"  基线校验 ods_visitor_session: {base['c']} 行, 成交 {base['r']}, 转化率 {base['p']}%")
    for r in rows:
        print(f"    {r['model_name']:20s} {r['metric_name']:10s} "
              f"{r['metric_value']:.4f}  is_best={r['is_best']}")
finally:
    conn.close()

print("\n" + "=" * 74)
print(f"完成：{TOTAL} 行 / 成交 {CONV} / 转化率 {CONV / TOTAL * 100:.2f}% / "
      f"最优模型 {best_model}")
print("=" * 74)
