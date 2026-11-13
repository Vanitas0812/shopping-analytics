package com.datavis.shopping.dto;

/**
 * 跳出率 / 退出率分箱行。
 *
 * <p>metric 为机器可读的英文枚举（bounce_rate / exit_rate），供前端按值拆分序列；
 * metricCn 为对应的中文业务名（跳出率 / 退出率），供图例直接展示，避免前端硬编码映射。
 * 两序列各 5 档，区间口径一致：0 / (0,0.02) / [0.02,0.05) / [0.05,0.1) / [0.1,0.2]。</p>
 */
public record BounceExitDTO(
        String metric,
        String metricCn,
        String rangeLabel,
        long sessions,
        long conversions,
        double conversionRate
) {
}
