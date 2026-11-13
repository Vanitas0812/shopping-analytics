package com.datavis.shopping.dto;

/**
 * 全局 KPI 的 SQL 聚合原始结果，比率在 service 层统一换算并保留 4 位小数。
 */
public record OverviewRaw(
        long totalSessions,
        long totalRevenue,
        double avgPageDepth,
        double avgDuration,
        double avgBounceRate,
        double avgExitRate,
        long newVisitorCount,
        long returningVisitorCount
) {
}
