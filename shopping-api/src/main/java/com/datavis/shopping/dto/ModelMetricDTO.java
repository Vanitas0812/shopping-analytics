package com.datavis.shopping.dto;

/**
 * 模型指标行，两模型：LogisticRegression、RandomForest。
 */
public record ModelMetricDTO(
        String modelName,
        double accuracy,
        double auc,
        double precision,
        double recall,
        double f1
) {
}
