package com.datavis.shopping.dto;

/**
 * 特征重要性行（Top12）。
 */
public record FeatureImportanceDTO(
        String featureKey,
        String featureCn,
        double importance,
        int rankNo
) {
}
