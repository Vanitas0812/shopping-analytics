#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成 data/sql 下的两份 SQL 交付物
=========================================================
1. 01_schema.sql         —— 建库 + 建表 + 维表灌数 + 预警规则种子数据（不含会话明细）
2. shopping_analytics.sql —— Navicat 风格完整导出：建库建表 + 全部数据（5 张表全量）

数据全部从当前 MySQL 库 shopping_analytics 实时读出，不手填。
"""
import io
import os
import re
import sys
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pymysql

BASE = os.path.dirname(os.path.abspath(__file__))          # ...\shopping-analytics\data
SQL_DIR = os.path.join(BASE, "sql")
os.makedirs(SQL_DIR, exist_ok=True)

DBNAME = "shopping_analytics"
DB = dict(host="localhost", user="root", password="123456",
          charset="utf8mb4", database=DBNAME,
          cursorclass=pymysql.cursors.DictCursor)

TABLES = ["dim_month", "ods_visitor_session", "dws_alert_rule",
          "dws_model_result", "dws_feature_importance"]

# 表中文说明（用于文件头注释与建表顺序说明）
TABLE_CN = {
    "dim_month": "月份维表（补全 1-12 月）",
    "ods_visitor_session": "访客会话明细（清洗后 12205 行）",
    "dws_alert_rule": "转化预警规则（成员二 CRUD 业务表）",
    "dws_model_result": "模型评估指标（含混淆矩阵四格）",
    "dws_feature_importance": "特征重要性 Top12",
}

# 手写 DDL（与库内 SHOW CREATE TABLE 完全等价，便于阅读与教案引用）
DDL = {}

DDL["dim_month"] = """CREATE TABLE `dim_month` (
  `month_num` INT NOT NULL COMMENT '月份序号1-12',
  `month_name` VARCHAR(10) NOT NULL COMMENT '英文短名',
  `month_cn` VARCHAR(10) NOT NULL COMMENT '中文名',
  `month_order` INT NOT NULL COMMENT '排序号1-12',
  PRIMARY KEY (`month_num`)
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '月份维表' ROW_FORMAT = Dynamic"""

DDL["ods_visitor_session"] = """CREATE TABLE `ods_visitor_session` (
  `session_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '会话主键',
  `administrative` INT NOT NULL DEFAULT 0 COMMENT '管理类页面访问数',
  `administrative_duration` DOUBLE NOT NULL DEFAULT 0 COMMENT '管理类页面停留秒数',
  `informational` INT NOT NULL DEFAULT 0 COMMENT '信息类页面访问数',
  `informational_duration` DOUBLE NOT NULL DEFAULT 0 COMMENT '信息类页面停留秒数',
  `product_related` INT NOT NULL DEFAULT 0 COMMENT '商品类页面访问数',
  `product_related_duration` DOUBLE NOT NULL DEFAULT 0 COMMENT '商品类页面停留秒数',
  `bounce_rates` DOUBLE NOT NULL DEFAULT 0 COMMENT '跳出率',
  `exit_rates` DOUBLE NOT NULL DEFAULT 0 COMMENT '退出率',
  `page_values` DOUBLE NOT NULL DEFAULT 0 COMMENT '页面价值分',
  `special_day` DOUBLE NOT NULL DEFAULT 0 COMMENT '特殊日期接近度0~1',
  `month` VARCHAR(10) NOT NULL COMMENT '访问月份',
  `month_num` INT NOT NULL COMMENT '月份序号1-12',
  `operating_systems` INT NOT NULL COMMENT '操作系统编码1-8',
  `browser` INT NOT NULL COMMENT '浏览器编码1-13',
  `region` INT NOT NULL COMMENT '区域编码1-9',
  `traffic_type` INT NOT NULL COMMENT '流量类型编码1-20',
  `visitor_type` VARCHAR(30) NOT NULL COMMENT '访客类型',
  `weekend` TINYINT(1) NOT NULL COMMENT '是否周末',
  `revenue` TINYINT(1) NOT NULL COMMENT '是否成交 0/1',
  `page_depth` INT NOT NULL DEFAULT 0 COMMENT '衍生:总浏览页面数',
  `total_duration` DOUBLE NOT NULL DEFAULT 0 COMMENT '衍生:总停留秒数',
  `is_bounce` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '衍生:跳出率>=0.2',
  PRIMARY KEY (`session_id`),
  INDEX `idx_month`(`month_num`) USING BTREE,
  INDEX `idx_visitor`(`visitor_type`) USING BTREE,
  INDEX `idx_traffic`(`traffic_type`) USING BTREE,
  INDEX `idx_revenue`(`revenue`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 12206 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '访客会话明细表' ROW_FORMAT = Dynamic"""

DDL["dws_alert_rule"] = """CREATE TABLE `dws_alert_rule` (
  `rule_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '规则主键',
  `rule_name` VARCHAR(100) NOT NULL COMMENT '规则名称',
  `metric` VARCHAR(50) NOT NULL COMMENT '监控指标: conversion_rate/bounce_rate/exit_rate/page_values',
  `operator_cmp` VARCHAR(10) NOT NULL COMMENT '比较符 > >= < <= =',
  `threshold_value` DOUBLE NOT NULL COMMENT '阈值',
  `traffic_type` INT NULL DEFAULT NULL COMMENT '限定流量类型,空=全部',
  `enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  `remark` VARCHAR(255) NULL DEFAULT NULL COMMENT '备注',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`rule_id`)
) ENGINE = InnoDB AUTO_INCREMENT = 6 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '转化预警规则表' ROW_FORMAT = Dynamic"""

DDL["dws_model_result"] = """CREATE TABLE `dws_model_result` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `model_name` VARCHAR(50) NOT NULL COMMENT '模型名',
  `metric_name` VARCHAR(50) NOT NULL COMMENT 'accuracy/auc/precision/recall/f1/tp/fp/tn/fn',
  `metric_value` DOUBLE NOT NULL,
  `is_best` TINYINT(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE = InnoDB AUTO_INCREMENT = 19 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '模型评估指标表' ROW_FORMAT = Dynamic"""

DDL["dws_feature_importance"] = """CREATE TABLE `dws_feature_importance` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `feature_key` VARCHAR(50) NOT NULL COMMENT '特征英文名',
  `feature_cn` VARCHAR(50) NOT NULL COMMENT '特征中文名',
  `importance` DOUBLE NOT NULL,
  `rank_no` INT NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE = InnoDB AUTO_INCREMENT = 13 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '特征重要性表' ROW_FORMAT = Dynamic"""

# ---------------------------------------------------------------- 值格式化
def sql_literal(v):
    """把 python 值转成 MySQL 字面量"""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):
            return "NULL"
        return repr(v)                      # 最短可往返表示，double 不丢精度
    if isinstance(v, str):
        return "'" + (v.replace("\\", "\\\\")
                       .replace("'", "''")
                       .replace("\n", "\\n")
                       .replace("\r", "\\r")
                       .replace("\x00", "")) + "'"
    if isinstance(v, datetime):
        return "'" + v.strftime("%Y-%m-%d %H:%M:%S") + "'"
    if hasattr(v, "as_tuple"):              # Decimal
        return format(v, "f")
    if isinstance(v, (bytes, bytearray)):
        return "0x" + v.hex()
    return "'" + str(v).replace("'", "''") + "'"


def insert_blocks(table, columns, rows, chunk=200):
    """生成 INSERT 语句块，长表分多条以控制单条语句体积"""
    if not rows:
        return []
    head = "INSERT INTO `%s` (%s) VALUES\n" % (
        table, ", ".join("`%s`" % c for c in columns))
    out = []
    for i in range(0, len(rows), chunk):
        part = rows[i:i + chunk]
        body = ",\n".join(
            "(" + ", ".join(sql_literal(v) for v in r) + ")" for r in part)
        out.append(head + body + ";")
    return out


conn = pymysql.connect(**DB)
cur = conn.cursor()
print("=" * 74)
print("读取当前库结构")
print("=" * 74)

# 校验库内 DDL 与手写 DDL 语义一致（仅比较表名、列名、索引名、注释）
meta = {}
for t in TABLES:
    cur.execute("""SELECT COLUMN_NAME c FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION""",
                (DBNAME, t))
    cols = [r["c"] for r in cur.fetchall()]
    cur.execute("""SELECT INDEX_NAME i, NON_UNIQUE nu FROM information_schema.STATISTICS
                   WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
                   GROUP BY INDEX_NAME, NON_UNIQUE ORDER BY INDEX_NAME""", (DBNAME, t))
    idx = [(r["i"], r["nu"]) for r in cur.fetchall()]
    cur.execute("""SELECT TABLE_ROWS, TABLE_COMMENT, ENGINE, TABLE_COLLATION
                   FROM information_schema.TABLES
                   WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s""", (DBNAME, t))
    info = cur.fetchone()
    meta[t] = {"cols": cols, "idx": idx, "info": info}
    print(f"  {t:24s} 列 {len(cols):2d}  索引 {len(idx):2d}  "
          f"引擎 {info['ENGINE']}  注释 {info['TABLE_COMMENT']}")

# 校验手写 DDL 覆盖了全部列名与索引名
for t in TABLES:
    for c in meta[t]["cols"]:
        assert "`%s`" % c in DDL[t], "DDL missing column %s.%s" % (t, c)
    for i, _ in meta[t]["idx"]:
        token = "PRIMARY KEY" if i == "PRIMARY" else "INDEX `%s`" % i
        assert token in DDL[t], "DDL missing index %s.%s" % (t, i)
print("  手写 DDL 列名/索引名覆盖校验：通过")

# 以库内实际 DDL 为准（保证导出脚本还原后与当前库结构逐字一致）
for t in TABLES:
    cur.execute("SHOW CREATE TABLE `%s`" % t)
    live_ddl = list(cur.fetchone().values())[1]
    if re.sub(r"\s+", "", live_ddl) != re.sub(r"\s+", "", DDL[t]):
        print("  [注意] %s 手写 DDL 与库内不一致，已改用库内实际 DDL" % t)
    DDL[t] = live_ddl
print("  DDL 已统一为库内实际结构")

# 读取全部数据
data, colmap = {}, {}
for t in TABLES:
    cur.execute("SELECT * FROM `%s`" % t)
    rows = cur.fetchall()
    cols = list(rows[0].keys()) if rows else meta[t]["cols"]
    colmap[t] = cols
    data[t] = [tuple(r[c] for c in cols) for r in rows]
    print(f"  读取 {t:24s} {len(data[t]):6d} 行")
cur.close()
conn.close()

NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- 01_schema.sql
def build_schema_sql():
    L = []
    L.append("""/*
 Navicat Premium Dump SQL —— 建库建表脚本（01_schema.sql）

 项目：电商用户购买意向分析与转化预测可视化平台
 数据集：UCI Online Shoppers Purchasing Intention（12330 行 × 18 列，去重后 12205 行）
 数据库：MySQL 8.3 / utf8mb4

 本脚本内容：
   1) 创建数据库 shopping_analytics
   2) 创建 5 张表（维表 + 明细表 + 预警规则表 + 模型结果表 + 特征重要性表）
   3) 灌入月份维表 12 行
   4) 灌入转化预警规则种子数据 5 行

 注意：会话明细 12205 行体积较大，不在本脚本内，见 `02_data.sql` 或
       Navicat 风格的完整导出 `shopping_analytics.sql`（建表 + 全量数据）。

 执行方式：mysql -u root -p123456 < 01_schema.sql
 生成时间：%s
*/""" % NOW)
    L.append("")
    L.append("SET NAMES utf8mb4;")
    L.append("SET FOREIGN_KEY_CHECKS = 0;")
    L.append("")
    L.append("-- ----------------------------")
    L.append("-- 创建数据库")
    L.append("-- ----------------------------")
    L.append("CREATE DATABASE IF NOT EXISTS `%s` " % DBNAME)
    L.append("  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
    L.append("")
    L.append("USE `%s`;" % DBNAME)
    L.append("")

    for i, t in enumerate(TABLES, 1):
        L.append("-- ----------------------------")
        L.append("-- %d. %s —— %s" % (i, t, TABLE_CN[t]))
        L.append("-- ----------------------------")
        L.append("DROP TABLE IF EXISTS `%s`;" % t)
        L.append(DDL[t] + ";")
        L.append("")

    # 维表数据
    t = "dim_month"
    L.append("-- ----------------------------")
    L.append("-- Record of %s（月份维表 1-12 月补全，解决缺 Jan/Apr 的图表断点）" % t)
    L.append("-- ----------------------------")
    L.extend(insert_blocks(t, colmap[t], data[t]))
    L.append("")

    # 预警规则种子数据
    t = "dws_alert_rule"
    L.append("-- ----------------------------")
    L.append("-- Record of %s（转化预警规则种子数据）" % t)
    L.append("-- ----------------------------")
    L.extend(insert_blocks(t, colmap[t], data[t]))
    L.append("")

    L.append("SET FOREIGN_KEY_CHECKS = 1;")
    L.append("")
    L.append("-- 校验：SELECT COUNT(*) FROM dim_month;              -- 期望 12")
    L.append("--       SELECT COUNT(*) FROM dws_alert_rule;         -- 期望 5")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------- shopping_analytics.sql
def build_full_sql():
    L = []
    L.append("""/*
 Navicat Premium Data Transfer —— 数据库完整导出（shopping_analytics.sql）

 Source Server         : localhost
 Source Server Type    : MySQL
 Source Server Version : 80300 (8.3.0)
 Source Host           : localhost:3306
 Source Schema         : shopping_analytics

 Target Server Type    : MySQL
 Target Server Version : 80300 (8.3.0)
 File Encoding         : 65001 (UTF-8)

 Date: %s

 项目：电商用户购买意向分析与转化预测可视化平台
 数据集：UCI Online Shoppers Purchasing Intention
         （原始 12330 行 × 18 列，去重去除 125 条完全重复行后 12205 行）

 本脚本含：建库 + 5 张表完整 DDL（含 COMMENT）+ 全部业务数据
   dim_month               12 行   月份维表
   ods_visitor_session  12205 行   访客会话明细（清洗后全量）
   dws_alert_rule           5 行   转化预警规则种子
   dws_model_result        18 行   模型指标（2 模型 × 9 指标，含混淆矩阵 tp/fp/tn/fn）
   dws_feature_importance  12 行   特征重要性 Top12

 还原方式：mysql -u root -p123456 < shopping_analytics.sql
*/""" % NOW)
    L.append("")
    L.append("SET NAMES utf8mb4;")
    L.append("SET FOREIGN_KEY_CHECKS = 0;")
    L.append("")
    L.append("-- ----------------------------")
    L.append("-- Create Database")
    L.append("-- ----------------------------")
    L.append("CREATE DATABASE IF NOT EXISTS `%s` " % DBNAME)
    L.append("  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
    L.append("USE `%s`;" % DBNAME)
    L.append("")

    for i, t in enumerate(TABLES, 1):
        L.append("-- ----------------------------")
        L.append("-- Table structure for %s（%s）" % (t, TABLE_CN[t]))
        L.append("-- ----------------------------")
        L.append("DROP TABLE IF EXISTS `%s`;" % t)
        L.append(DDL[t] + ";")
        L.append("")
        L.append("-- ----------------------------")
        L.append("-- Records of %s（%d 行）" % (t, len(data[t])))
        L.append("-- ----------------------------")
        L.extend(insert_blocks(t, colmap[t], data[t]))
        L.append("")

    L.append("SET FOREIGN_KEY_CHECKS = 1;")
    L.append("")
    L.append("-- ----------------------------")
    L.append("-- 还原后校验（期望值）")
    L.append("-- ----------------------------")
    L.append("-- SELECT COUNT(*) FROM dim_month;               -- 12")
    L.append("-- SELECT COUNT(*) FROM ods_visitor_session;     -- 12205")
    L.append("-- SELECT COUNT(*) FROM dws_alert_rule;          -- 5")
    L.append("-- SELECT COUNT(*) FROM dws_model_result;        -- 18")
    L.append("-- SELECT COUNT(*) FROM dws_feature_importance;  -- 12")
    L.append("-- SELECT SUM(revenue), ROUND(AVG(revenue)*100,2) FROM ods_visitor_session;")
    L.append("--   -- 1908, 15.63")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- 02_data.sql
def build_data_sql():
    L = []
    L.append("""/*
 数据导入脚本（02_data.sql）—— 仅数据，不含建表

 前置条件：已执行 `01_schema.sql` 建好库表。
 本脚本灌入 5 张表的全部业务数据（会话明细 12205 行 + 维表 + 规则 + 模型结果）。
 执行方式：mysql -u root -p123456 shopping_analytics < 02_data.sql
 生成时间：%s
*/""" % NOW)
    L.append("")
    L.append("SET NAMES utf8mb4;")
    L.append("SET FOREIGN_KEY_CHECKS = 0;")
    L.append("USE `%s`;" % DBNAME)
    L.append("")
    for t in TABLES:
        L.append("-- ----------------------------")
        L.append("-- Records of %s（%d 行）" % (t, len(data[t])))
        L.append("-- ----------------------------")
        L.append("TRUNCATE TABLE `%s`;" % t)
        L.extend(insert_blocks(t, colmap[t], data[t]))
        L.append("")
    L.append("SET FOREIGN_KEY_CHECKS = 1;")
    L.append("")
    return "\n".join(L)


print("\n" + "=" * 74)
print("生成 SQL 文件")
print("=" * 74)
p1 = os.path.join(SQL_DIR, "01_schema.sql")
p2 = os.path.join(SQL_DIR, "02_data.sql")
p3 = os.path.join(SQL_DIR, "shopping_analytics.sql")

s1 = build_schema_sql()
s2 = build_data_sql()
s3 = build_full_sql()
for path, content in [(p1, s1), (p2, s2), (p3, s3)]:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"  -> {path}  ({len(content.encode('utf-8')) / 1024:.1f} KB, "
          f"{content.count(chr(10)) + 1} 行)")
print("完成")

