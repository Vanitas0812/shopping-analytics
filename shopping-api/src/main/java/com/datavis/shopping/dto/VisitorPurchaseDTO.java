package com.datavis.shopping.dto;

/**
 * 访客类型 × 周末 成交热力数据行。
 */
public record VisitorPurchaseDTO(
        String visitorType,
        int weekend,
        long sessions,
        double conversionRate
) {
}
