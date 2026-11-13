package com.datavis.shopping.dto;

/**
 * 通用分箱统计中间结果：区间标签 + 会话数 + 成交数。
 */
public record BucketStat(
        String label,
        long sessions,
        long conversions
) {
}
