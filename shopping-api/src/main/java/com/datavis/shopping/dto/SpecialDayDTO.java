package com.datavis.shopping.dto;

/**
 * 特殊日期接近度行。
 */
public record SpecialDayDTO(
        double specialDay,
        long sessions,
        long conversions,
        double conversionRate
) {
}
