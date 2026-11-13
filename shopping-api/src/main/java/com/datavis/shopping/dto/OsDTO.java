package com.datavis.shopping.dto;

/**
 * 操作系统构成行（OS 为匿名编码，Top8）。
 */
public record OsDTO(
        String osName,
        long sessions,
        double pct
) {
}
