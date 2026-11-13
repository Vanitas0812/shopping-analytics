package com.datavis.shopping.dto;

/**
 * 访客类型对比行。
 */
public record VisitorTypeDTO(
        String visitorType,
        long sessions,
        long conversions,
        double conversionRate,
        double pct
) {
}
