package com.datavis.shopping.entity;

/**
 * 模型评估指标实体，对应表 dws_model_result。
 * metric_name 取值：accuracy/auc/precision/recall/f1/tp/fp/tn/fn。
 */
public class ModelResult {

    private Long id;
    private String modelName;
    private String metricName;
    private Double metricValue;
    private Integer isBest;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getModelName() {
        return modelName;
    }

    public void setModelName(String modelName) {
        this.modelName = modelName;
    }

    public String getMetricName() {
        return metricName;
    }

    public void setMetricName(String metricName) {
        this.metricName = metricName;
    }

    public Double getMetricValue() {
        return metricValue;
    }

    public void setMetricValue(Double metricValue) {
        this.metricValue = metricValue;
    }

    public Integer getIsBest() {
        return isBest;
    }

    public void setIsBest(Integer isBest) {
        this.isBest = isBest;
    }
}
