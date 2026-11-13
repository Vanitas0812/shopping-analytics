package com.datavis.shopping.dto;

/**
 * PageValues 价值分箱行。
 */
public record PageValueBinDTO(
        String binLabel,
        long sessions,
        long conversions,
        double conversionRate
) {
}
