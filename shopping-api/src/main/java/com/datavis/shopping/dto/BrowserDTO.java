package com.datavis.shopping.dto;

/**
 * 浏览器构成行（Browser 为匿名编码）。
 */
public record BrowserDTO(
        int browser,
        long sessions,
        double pct
) {
}
