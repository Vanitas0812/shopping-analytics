package com.datavis.shopping.dto;

/**
 * 月度趋势行，1-12 月全量，缺失月 sessions=0。
 */
public record MonthlyTrendDTO(
        int monthNum,
        String monthCn,
        long sessions,
        long conversions,
        double conversionRate
) {
}
