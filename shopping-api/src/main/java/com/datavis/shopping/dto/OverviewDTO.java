package com.datavis.shopping.dto;

/**
 * 成员一全局 KPI 卡数据。
 */
public record OverviewDTO(
        long totalSessions,
        long totalRevenue,
        double conversionRate,
        double avgPageDepth,
        double avgDuration,
        double bounceRate,
        double exitRate,
        double newVisitorRate,
        double returningRate
) {
}
