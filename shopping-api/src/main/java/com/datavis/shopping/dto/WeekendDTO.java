package com.datavis.shopping.dto;

/**
 * 周末对比行。
 */
public record WeekendDTO(
        int weekend,
        long sessions,
        long conversions,
        double conversionRate
) {
}
