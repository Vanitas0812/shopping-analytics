package com.datavis.shopping.entity;

/**
 * 特征重要性实体，对应表 dws_feature_importance。
 */
public class FeatureImportance {

    private Long id;
    private String featureKey;
    private String featureCn;
    private Double importance;
    private Integer rankNo;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getFeatureKey() {
        return featureKey;
    }

    public void setFeatureKey(String featureKey) {
        this.featureKey = featureKey;
    }

    public String getFeatureCn() {
        return featureCn;
    }

    public void setFeatureCn(String featureCn) {
        this.featureCn = featureCn;
    }

    public Double getImportance() {
        return importance;
    }

    public void setImportance(Double importance) {
        this.importance = importance;
    }

    public Integer getRankNo() {
        return rankNo;
    }

    public void setRankNo(Integer rankNo) {
        this.rankNo = rankNo;
    }
}
