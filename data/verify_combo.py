# -*- coding: utf-8 -*-
"""
验证 01_schema.sql + 02_data.sql 组合脚本能还原出与生产库一致的结果，
并验证 shopping_analytics.sql 单文件还原（已由 verify_restore.py live 模式覆盖）。

本脚本把库名替换为临时库，验证完自动清理，不触碰生产库。
"""
import io
import re
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pymysql

MYSQL = r"C:\mysql-8.3.0-winx64\bin\mysql.exe"
SQL_DIR = r"D:\DSH\shopping-analytics\data\sql"
DB = dict(host="localhost", user="root", password="123456",
          charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor, database="shopping_analytics")
DBNAME, SCRATCH = "shopping_analytics", "shopping_analytics_restore_test"
TABLES = ["dim_month", "ods_visitor_session", "dws_alert_rule",
          "dws_model_result", "dws_feature_importance"]
EXPECT = {"dim_month": 12, "ods_visitor_session": 12205, "dws_alert_rule": 5,
          "dws_model_result": 18, "dws_feature_importance": 12}


def run_mysql(stdin_bytes, db=None):
    cmd = [MYSQL, "-u", "root", "-p123456", "--default-character-set=utf8mb4"]
    if db:
        cmd.append(db)
    p = subprocess.run(cmd, input=stdin_bytes, capture_output=True)
    err = "\n".join(l for l in p.stderr.decode("utf-8", "replace").splitlines()
                    if "Using a password" not in l)
    return p.returncode, err


def exec_sql(sql):
    c = pymysql.connect(host="localhost", user="root", password="123456",
                        charset="utf8mb4", autocommit=True)
    with c.cursor() as cur:
        cur.execute(sql)
    c.close()


def count_tables(db):
    c = pymysql.connect(host="localhost", user="root", password="123456",
                        charset="utf8mb4", database=db,
                        cursorclass=pymysql.cursors.DictCursor)
    out = {}
    with c.cursor() as cur:
        for t in TABLES:
            cur.execute("SELECT COUNT(*) n FROM `%s`" % t)
            out[t] = cur.fetchone()["n"]
        cur.execute("SELECT SUM(revenue) c, ROUND(AVG(revenue)*100,2) p FROM ods_visitor_session")
        kpi = cur.fetchone()
    c.close()
    return out, kpi


def rewrite(src, dbname):
    """把脚本里的库名改写成临时库名（只改 CREATE DATABASE / USE 两处）"""
    return (src
            .replace("CREATE DATABASE IF NOT EXISTS `%s`" % DBNAME,
                     "CREATE DATABASE IF NOT EXISTS `%s`" % dbname)
            .replace("USE `%s`;" % DBNAME, "USE `%s`;" % dbname))


print("=" * 74)
print("组合还原测试：01_schema.sql + 02_data.sql")
print("=" * 74)
exec_sql("DROP DATABASE IF EXISTS `%s`" % SCRATCH)

schema_sql = rewrite(open(SQL_DIR + r"\01_schema.sql", "rb").read().decode("utf-8"), SCRATCH)
rc1, err1 = run_mysql(schema_sql.encode("utf-8"))
print("  01_schema.sql 退出码:", rc1, ("| stderr: " + err1.strip()[:500]) if err1.strip() else "")

data_sql = rewrite(open(SQL_DIR + r"\02_data.sql", "rb").read().decode("utf-8"), SCRATCH)
rc2, err2 = run_mysql(data_sql.encode("utf-8"), db=SCRATCH)
print("  02_data.sql   退出码:", rc2, ("| stderr: " + err2.strip()[:500]) if err2.strip() else "")

counts, kpi = count_tables(SCRATCH)
ok = True
print("\n  还原结果：")
for t in TABLES:
    good = counts[t] == EXPECT[t]
    ok &= good
    print("    [%s] %-24s %6d 行 (期望 %d)" % ("PASS" if good else "FAIL", t,
                                              counts[t], EXPECT[t]))
print("    ods 口径: 成交=%s 转化率=%s%%" % (kpi["c"], kpi["p"]))
kpi_ok = int(kpi["c"]) == 1908 and float(kpi["p"]) == 15.63
print("    业务口径:", "PASS" if kpi_ok else "FAIL")

# 与生产库逐表行数比对
prod, prod_kpi = count_tables(DBNAME)
same = all(counts[t] == prod[t] for t in TABLES)
print("    与生产库行数逐一相同:", "PASS" if same else "FAIL")

exec_sql("DROP DATABASE IF EXISTS `%s`" % SCRATCH)
print("\n  临时库已清理")

print("\n" + "=" * 74)
final = (ok and kpi_ok and same and rc1 == 0 and rc2 == 0)
print("FINAL  01+02 组合还原=%s (schema rc=%s, data rc=%s)" % ("PASS" if final else "FAIL", rc1, rc2))
print("=" * 74)
sys.exit(0 if final else 1)
