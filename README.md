# 电商用户购买意向分析与转化预测可视化平台

24级数据科学与大数据技术2班 · 第2组

## 成员分工

- **成员一（2024080910017）**：用户行为与流量运营 · `/api/m1` · 成员一大屏（`dashboard-a`）
- **成员二（2024080910072）**：转化预测与精细化运营 · `/api/m2` · 成员二大屏（`dashboard-b`）

## 技术栈

Spring Boot 3.2.5 + Java 21 + JdbcTemplate + MySQL 8.3 + ECharts 5.5 + Python(pandas / scikit-learn)

## 数据集

UCI Online Shoppers Purchasing Intention · 原始 12,330 行 × 18 列 · 去重后 12,205 条会话 · 转化率 15.63%

## 运行步骤

1. 导入数据库：`mysql -u root -p < data/sql/shopping_analytics.sql`
2. 启动后端：`cd shopping-api && mvn spring-boot:run`
3. 访问大屏：<http://localhost:8080/dashboard-a/>

> 数据库默认配置见 `shopping-api/src/main/resources/application.yml`（root / 123456 / localhost:3306）
