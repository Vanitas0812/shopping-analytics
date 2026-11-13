package com.datavis.shopping.dto;

/**
 * 混淆矩阵，默认模型 RandomForest。
 */
public record ConfusionMatrixDTO(
        String modelName,
        long tp,
        long fp,
        long tn,
        long fn
) {
}
