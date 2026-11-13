package com.datavis.shopping.dto;

/**
 * 页面访问深度分层行。
 */
public record PageDepthDTO(
        String depthLabel,
        long sessions,
        long conversions,
        double conversionRate
) {
}
