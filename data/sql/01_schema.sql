/*
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
 生成时间：2026-11-04 09:48:33
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- 创建数据库
-- ----------------------------
CREATE DATABASE IF NOT EXISTS `shopping_analytics` 
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

USE `shopping_analytics`;

-- ----------------------------
-- 1. dim_month —— 月份维表（补全 1-12 月）
-- ----------------------------
DROP TABLE IF EXISTS `dim_month`;
CREATE TABLE `dim_month` (
  `month_num` int NOT NULL COMMENT '月份序号1-12',
  `month_name` varchar(10) NOT NULL COMMENT '英文短名',
  `month_cn` varchar(10) NOT NULL COMMENT '中文名',
  `month_order` int NOT NULL COMMENT '排序号1-12',
  PRIMARY KEY (`month_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='月份维表';

-- ----------------------------
-- 2. ods_visitor_session —— 访客会话明细（清洗后 12205 行）
-- ----------------------------
DROP TABLE IF EXISTS `ods_visitor_session`;
CREATE TABLE `ods_visitor_session` (
  `session_id` bigint NOT NULL AUTO_INCREMENT COMMENT '会话主键',
  `administrative` int NOT NULL DEFAULT '0' COMMENT '管理类页面访问数',
  `administrative_duration` double NOT NULL DEFAULT '0' COMMENT '管理类页面停留秒数',
  `informational` int NOT NULL DEFAULT '0' COMMENT '信息类页面访问数',
  `informational_duration` double NOT NULL DEFAULT '0' COMMENT '信息类页面停留秒数',
  `product_related` int NOT NULL DEFAULT '0' COMMENT '商品类页面访问数',
  `product_related_duration` double NOT NULL DEFAULT '0' COMMENT '商品类页面停留秒数',
  `bounce_rates` double NOT NULL DEFAULT '0' COMMENT '跳出率',
  `exit_rates` double NOT NULL DEFAULT '0' COMMENT '退出率',
  `page_values` double NOT NULL DEFAULT '0' COMMENT '页面价值分',
  `special_day` double NOT NULL DEFAULT '0' COMMENT '特殊日期接近度0~1',
  `month` varchar(10) NOT NULL COMMENT '访问月份',
  `month_num` int NOT NULL COMMENT '月份序号1-12',
  `operating_systems` int NOT NULL COMMENT '操作系统编码1-8',
  `browser` int NOT NULL COMMENT '浏览器编码1-13',
  `region` int NOT NULL COMMENT '区域编码1-9',
  `traffic_type` int NOT NULL COMMENT '流量类型编码1-20',
  `visitor_type` varchar(30) NOT NULL COMMENT '访客类型',
  `weekend` tinyint(1) NOT NULL COMMENT '是否周末',
  `revenue` tinyint(1) NOT NULL COMMENT '是否成交 0/1',
  `page_depth` int NOT NULL DEFAULT '0' COMMENT '衍生:总浏览页面数',
  `total_duration` double NOT NULL DEFAULT '0' COMMENT '衍生:总停留秒数',
  `is_bounce` tinyint(1) NOT NULL DEFAULT '0' COMMENT '衍生:跳出率>=0.2',
  PRIMARY KEY (`session_id`),
  KEY `idx_month` (`month_num`),
  KEY `idx_visitor` (`visitor_type`),
  KEY `idx_traffic` (`traffic_type`),
  KEY `idx_revenue` (`revenue`)
) ENGINE=InnoDB AUTO_INCREMENT=12208 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='访客会话明细表';

-- ----------------------------
-- 3. dws_alert_rule —— 转化预警规则（成员二 CRUD 业务表）
-- ----------------------------
DROP TABLE IF EXISTS `dws_alert_rule`;
CREATE TABLE `dws_alert_rule` (
  `rule_id` bigint NOT NULL AUTO_INCREMENT COMMENT '规则主键',
  `rule_name` varchar(100) NOT NULL COMMENT '规则名称',
  `metric` varchar(50) NOT NULL COMMENT '监控指标: conversion_rate/bounce_rate/exit_rate/page_values',
  `operator_cmp` varchar(10) NOT NULL COMMENT '比较符 > >= < <= =',
  `threshold_value` double NOT NULL COMMENT '阈值',
  `traffic_type` int DEFAULT NULL COMMENT '限定流量类型,空=全部',
  `enabled` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否启用',
  `remark` varchar(255) DEFAULT NULL COMMENT '备注',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`rule_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='转化预警规则表';

-- ----------------------------
-- 4. dws_model_result —— 模型评估指标（含混淆矩阵四格）
-- ----------------------------
DROP TABLE IF EXISTS `dws_model_result`;
CREATE TABLE `dws_model_result` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `model_name` varchar(50) NOT NULL COMMENT '模型名',
  `metric_name` varchar(50) NOT NULL COMMENT 'accuracy/auc/precision/recall/f1/tp/fp/tn/fn',
  `metric_value` double NOT NULL,
  `is_best` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='模型评估指标表';

-- ----------------------------
-- 5. dws_feature_importance —— 特征重要性 Top12
-- ----------------------------
DROP TABLE IF EXISTS `dws_feature_importance`;
CREATE TABLE `dws_feature_importance` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `feature_key` varchar(50) NOT NULL COMMENT '特征英文名',
  `feature_cn` varchar(50) NOT NULL COMMENT '特征中文名',
  `importance` double NOT NULL,
  `rank_no` int NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='特征重要性表';

-- ----------------------------
-- Record of dim_month（月份维表 1-12 月补全，解决缺 Jan/Apr 的图表断点）
-- ----------------------------
INSERT INTO `dim_month` (`month_num`, `month_name`, `month_cn`, `month_order`) VALUES
(1, 'Jan', '1月', 1),
(2, 'Feb', '2月', 2),
(3, 'Mar', '3月', 3),
(4, 'Apr', '4月', 4),
(5, 'May', '5月', 5),
(6, 'June', '6月', 6),
(7, 'Jul', '7月', 7),
(8, 'Aug', '8月', 8),
(9, 'Sep', '9月', 9),
(10, 'Oct', '10月', 10),
(11, 'Nov', '11月', 11),
(12, 'Dec', '12月', 12);

-- ----------------------------
-- Record of dws_alert_rule（转化预警规则种子数据）
-- ----------------------------
INSERT INTO `dws_alert_rule` (`rule_id`, `rule_name`, `metric`, `operator_cmp`, `threshold_value`, `traffic_type`, `enabled`, `remark`, `create_time`, `update_time`) VALUES
(1, '整体转化率低于大盘告警', 'conversion_rate', '<', 0.124, NULL, 1, '低于全站历史均值15.47%的80%时触发', '2026-11-04 09:36:52', '2026-11-04 09:36:52'),
(2, '高跳出率流量类型预警', 'bounce_rate', '>', 0.2, NULL, 1, '跳出率阈值法(>=0.2)占比过高', '2026-11-04 09:36:52', '2026-11-04 09:36:52'),
(3, '退出率异常告警', 'exit_rate', '>', 0.1, NULL, 1, '退出率超过10%需排查落地页', '2026-11-04 09:36:52', '2026-11-04 09:36:52'),
(4, '流量类型2转化不足', 'conversion_rate', '<', 0.05, 2, 1, '流量类型2样本量大但转化偏低', '2026-11-04 09:36:52', '2026-11-04 09:36:52'),
(5, '页面价值不足预警', 'page_values', '<', 5.0, NULL, 0, '平均页面价值低于5分', '2026-11-04 09:36:52', '2026-11-04 09:36:52');

SET FOREIGN_KEY_CHECKS = 1;

-- 校验：SELECT COUNT(*) FROM dim_month;              -- 期望 12
--       SELECT COUNT(*) FROM dws_alert_rule;         -- 期望 5
