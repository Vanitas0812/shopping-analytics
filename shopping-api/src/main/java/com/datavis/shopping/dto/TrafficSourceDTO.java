package com.datavis.shopping.dto;

/**
 * 流量类型效率行（Top10）。
 */
public record TrafficSourceDTO(
        int trafficType,
        long sessions,
        long conversions,
        double conversionRate
) {
}
