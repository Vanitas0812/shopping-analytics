package com.datavis.shopping.dto;

/**
 * 区域分布行（Region 为匿名编码）。
 */
public record RegionDTO(
        int region,
        long sessions,
        long conversions,
        double conversionRate
) {
}
