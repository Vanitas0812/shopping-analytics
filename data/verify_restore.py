# -*- coding: utf-8 -*-
"""
验收脚本：把 SQL 脚本还原到【临时库】并逐行逐列比对当前生产库。

模式
  scratch : 还原到 shopping_analytics_restore_test，比对内容哈希后删除临时库（不干扰队友）
  live    : 真删 shopping_analytics 再用脚本还原（验收硬指标：删库后完整还原）

只在本进程内存里保存快照，不额外写临时文件。
"""
import hashlib
import io
import os
import re
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pymysql

MYSQL = r"C:\mysql-8.3.0-winx64\bin\mysql.exe"
SQL_DIR = r"D:\DSH\shopping-analytics\data\sql"
FULL_SQL = os.path.join(SQL_DIR, "shopping_analytics.sql")
SCHEMA_SQL = os.path.join(SQL_DIR, "01_schema.sql")
DATA_SQL = os.path.join(SQL_DIR, "02_data.sql")
DB = dict(host="localhost", user="root", password="123456",
          charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor)
DBNAME = "shopping_analytics"
SCRATCH = "shopping_analytics_restore_test"
TABLES = ["dim_month", "ods_visitor_session", "dws_alert_rule",
          "dws_model_result", "dws_feature_importance"]
EXPECT = {"dim_month": 12, "ods_visitor_session": 12205, "dws_alert_rule": 5,
          "dws_model_result": 18, "dws_feature_importance": 12}


def conn(with_db=True, db=None):
    kw = dict(DB)
    if with_db:
        kw["database"] = db or DBNAME
    return pymysql.connect(**kw)


def snapshot(db=None):
    c = conn(db=db)
    cur = c.cursor()
    snap = {}
    for t in TABLES:
        cur.execute("SELECT * FROM `%s`" % t)
        rows = cur.fetchall()
        cols = list(rows[0].keys()) if rows else []
        tuples = [tuple(r[k] for k in cols) for r in rows]
        tuples.sort(key=lambda r: r[0])
        h = hashlib.sha256(
            repr([tuple(str(x) for x in r) for r in tuples]).encode("utf-8")).hexdigest()
        cur.execute("SHOW CREATE TABLE `%s`" % t)
        ddl = list(cur.fetchone().values())[1]
        cur.execute("""SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT,
                              COLUMN_COMMENT
                       FROM information_schema.COLUMNS
                       WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
                       ORDER BY ORDINAL_POSITION""", (db or DBNAME, t))
        colmeta = [(r["COLUMN_NAME"], r["COLUMN_TYPE"], r["IS_NULLABLE"],
                    str(r["COLUMN_DEFAULT"]), r["COLUMN_COMMENT"]) for r in cur.fetchall()]
        snap[t] = {"rows": tuples, "n": len(tuples), "hash": h,
                   "ddl": ddl, "colmeta": colmeta, "cols": cols}
    c.close()
    return snap


def run_mysql(stdin_bytes, db=None):
    cmd = [MYSQL, "-u", "root", "-p123456", "--default-character-set=utf8mb4"]
    if db:
        cmd.append(db)
    p = subprocess.run(cmd, input=stdin_bytes, capture_output=True)
    err = p.stderr.decode("utf-8", "replace")
    err = "\n".join(l for l in err.splitlines() if "Using a password" not in l)
    return p.returncode, p.stdout.decode("utf-8", "replace"), err


def drop_db(name):
    c = conn(with_db=False)
    with c.cursor() as cur:
        cur.execute("DROP DATABASE IF EXISTS `%s`" % name)
    c.close()


def db_exists(name):
    c = conn(with_db=False)
    with c.cursor() as cur:
        cur.execute("SHOW DATABASES LIKE %s", (name,))
        r = cur.fetchone() is not None
    c.close()
    return r


def compare(before, after, label):
    ok_all = True
    for t in TABLES:
        b, a = before[t], after[t]
        rows_ok = (b["n"] == a["n"] == EXPECT[t])
        hash_ok = b["hash"] == a["hash"]
        ddl_ok = re.sub(r"\s+", "", b["ddl"]) == re.sub(r"\s+", "", a["ddl"])
        meta_ok = b["colmeta"] == a["colmeta"]
        ok = rows_ok and hash_ok and ddl_ok and meta_ok
        ok_all &= ok
        print("  [%s] %-24s %6d 行 (期望 %d)  内容哈希=%s  DDL=%s  列元信息=%s"
              % ("PASS" if ok else "FAIL", t, a["n"], EXPECT[t],
                 "一致" if hash_ok else "不一致",
                 "一致" if ddl_ok else "不一致",
                 "一致" if meta_ok else "不一致"))
    return ok_all


def business_check(db=None):
    c = conn(db=db)
    with c.cursor() as cur:
        cur.execute("""SELECT COUNT(*) n, SUM(revenue) c,
                              ROUND(AVG(revenue)*100,2) p, ROUND(AVG(page_depth),4) d,
                              ROUND(AVG(total_duration),4) dur,
                              ROUND(AVG(bounce_rates),4) br, ROUND(AVG(exit_rates),4) er
                       FROM ods_visitor_session""")
        kpi = cur.fetchone()
        cur.execute("SELECT COUNT(DISTINCT model_name) m, COUNT(*) n FROM dws_model_result")
        mr = cur.fetchone()
        cur.execute("SELECT MIN(rank_no) a, MAX(rank_no) b, COUNT(*) n "
                    "FROM dws_feature_importance")
        fi = cur.fetchone()
    c.close()
    ok = (kpi["n"] == 12205 and int(kpi["c"]) == 1908
          and float(kpi["p"]) == 15.63 and mr["m"] == 2 and mr["n"] == 18
          and fi["n"] == 12 and fi["a"] == 1 and fi["b"] == 12)
    print("    ods_visitor_session : n=%s 成交=%s 转化率=%s%% 平均深度=%s 平均停留=%s "
          "跳出=%s 退出=%s" % (kpi["n"], kpi["c"], kpi["p"], kpi["d"],
                              kpi["dur"], kpi["br"], kpi["er"]))
    print("    dws_model_result    : %s 个模型 / %s 行" % (mr["m"], mr["n"]))
    print("    dws_feature_importance: rank %s..%s / %s 行" % (fi["a"], fi["b"], fi["n"]))
    print("    业务口径校验:", "PASS" if ok else "FAIL")
    return ok


mode = (sys.argv[1] if len(sys.argv) > 1 else "scratch").lower()

print("=" * 76)
print("STEP 1  内存快照当前库 %s" % DBNAME)
print("=" * 76)
before = snapshot(DBNAME)
for t in TABLES:
    print("  %-24s %6d 行  sha256=%s..." % (t, before[t]["n"], before[t]["hash"][:16]))

if mode == "scratch":
    print("\n" + "=" * 76)
    print("STEP 2  还原 shopping_analytics.sql 到临时库 %s" % SCRATCH)
    print("=" * 76)
    drop_db(SCRATCH)
    sql = open(FULL_SQL, "rb").read().decode("utf-8")
    # 仅替换库名，其余脚本内容原样执行 -> 验证脚本本身可执行性
    sql2 = sql.replace("CREATE DATABASE IF NOT EXISTS `%s`" % DBNAME,
                       "CREATE DATABASE IF NOT EXISTS `%s`" % SCRATCH)
    assert sql2 != sql, "未命中 CREATE DATABASE 行"
    sql2 = sql2.replace("USE `%s`;" % DBNAME, "USE `%s`;" % SCRATCH)
    rc, out, err = run_mysql(sql2.encode("utf-8"))
    print("  mysql 退出码:", rc)
    if err.strip():
        print("  stderr:", err.strip()[:800])
    print("  临时库已创建:", db_exists(SCRATCH))

    print("\n" + "=" * 76)
    print("STEP 3  逐表比对临时库 vs 生产库（行数/内容哈希/DDL/列元信息）")
    print("=" * 76)
    after = snapshot(SCRATCH)
    ok = compare(before, after, "scratch")

    print("\n" + "=" * 76)
    print("STEP 4  临时库业务口径校验")
    print("=" * 76)
    ok2 = business_check(SCRATCH)

    print("\n" + "=" * 76)
    print("STEP 5  清理临时库")
    print("=" * 76)
    drop_db(SCRATCH)
    print("  临时库已删除:", not db_exists(SCRATCH))

    print("\n" + "=" * 76)
    print("FINAL  内容一致性=%s | 业务口径=%s | mysql退出码=%s"
          % ("PASS" if ok else "FAIL", "PASS" if ok2 else "FAIL", rc))
    print("       生产库 %s 全程未被删除（队友可继续联调）" % DBNAME)
    print("=" * 76)
    sys.exit(0 if (ok and ok2 and rc == 0) else 1)

else:
    print("\n" + "=" * 76)
    print("STEP 2  DROP DATABASE %s" % DBNAME)
    print("=" * 76)
    drop_db(DBNAME)
    print("  数据库已删除:", not db_exists(DBNAME))

    print("\n" + "=" * 76)
    print("STEP 3  mysql -u root -p123456 < shopping_analytics.sql")
    print("=" * 76)
    rc, out, err = run_mysql(open(FULL_SQL, "rb").read())
    print("  退出码:", rc)
    if err.strip():
        print("  stderr:", err.strip()[:800])
    print("  数据库已重建:", db_exists(DBNAME))

    print("\n" + "=" * 76)
    print("STEP 4  逐表比对（删库前快照 vs 还原后）")
    print("=" * 76)
    after = snapshot(DBNAME)
    ok = compare(before, after, "live")

    print("\n" + "=" * 76)
    print("STEP 5  业务口径校验")
    print("=" * 76)
    ok2 = business_check()

    print("\n" + "=" * 76)
    print("FINAL  删库还原=%s | 内容一致=%s | 业务口径=%s | 退出码=%s"
          % ("PASS" if db_exists(DBNAME) else "FAIL",
             "PASS" if ok else "FAIL", "PASS" if ok2 else "FAIL", rc))
    print("=" * 76)
    sys.exit(0 if (ok and ok2 and rc == 0) else 1)
