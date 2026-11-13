package com.datavis.shopping.entity;

/**
 * 访客会话明细实体，对应表 ods_visitor_session。
 */
public class VisitorSession {

    private Long sessionId;
    private Integer administrative;
    private Double administrativeDuration;
    private Integer informational;
    private Double informationalDuration;
    private Integer productRelated;
    private Double productRelatedDuration;
    private Double bounceRates;
    private Double exitRates;
    private Double pageValues;
    private Double specialDay;
    private String month;
    private Integer monthNum;
    private Integer operatingSystems;
    private Integer browser;
    private Integer region;
    private Integer trafficType;
    private String visitorType;
    private Integer weekend;
    private Integer revenue;
    private Integer pageDepth;
    private Double totalDuration;
    private Integer isBounce;

    public Long getSessionId() {
        return sessionId;
    }

    public void setSessionId(Long sessionId) {
        this.sessionId = sessionId;
    }

    public Integer getAdministrative() {
        return administrative;
    }

    public void setAdministrative(Integer administrative) {
        this.administrative = administrative;
    }

    public Double getAdministrativeDuration() {
        return administrativeDuration;
    }

    public void setAdministrativeDuration(Double administrativeDuration) {
        this.administrativeDuration = administrativeDuration;
    }

    public Integer getInformational() {
        return informational;
    }

    public void setInformational(Integer informational) {
        this.informational = informational;
    }

    public Double getInformationalDuration() {
        return informationalDuration;
    }

    public void setInformationalDuration(Double informationalDuration) {
        this.informationalDuration = informationalDuration;
    }

    public Integer getProductRelated() {
        return productRelated;
    }

    public void setProductRelated(Integer productRelated) {
        this.productRelated = productRelated;
    }

    public Double getProductRelatedDuration() {
        return productRelatedDuration;
    }

    public void setProductRelatedDuration(Double productRelatedDuration) {
        this.productRelatedDuration = productRelatedDuration;
    }

    public Double getBounceRates() {
        return bounceRates;
    }

    public void setBounceRates(Double bounceRates) {
        this.bounceRates = bounceRates;
    }

    public Double getExitRates() {
        return exitRates;
    }

    public void setExitRates(Double exitRates) {
        this.exitRates = exitRates;
    }

    public Double getPageValues() {
        return pageValues;
    }

    public void setPageValues(Double pageValues) {
        this.pageValues = pageValues;
    }

    public Double getSpecialDay() {
        return specialDay;
    }

    public void setSpecialDay(Double specialDay) {
        this.specialDay = specialDay;
    }

    public String getMonth() {
        return month;
    }

    public void setMonth(String month) {
        this.month = month;
    }

    public Integer getMonthNum() {
        return monthNum;
    }

    public void setMonthNum(Integer monthNum) {
        this.monthNum = monthNum;
    }

    public Integer getOperatingSystems() {
        return operatingSystems;
    }

    public void setOperatingSystems(Integer operatingSystems) {
        this.operatingSystems = operatingSystems;
    }

    public Integer getBrowser() {
        return browser;
    }

    public void setBrowser(Integer browser) {
        this.browser = browser;
    }

    public Integer getRegion() {
        return region;
    }

    public void setRegion(Integer region) {
        this.region = region;
    }

    public Integer getTrafficType() {
        return trafficType;
    }

    public void setTrafficType(Integer trafficType) {
        this.trafficType = trafficType;
    }

    public String getVisitorType() {
        return visitorType;
    }

    public void setVisitorType(String visitorType) {
        this.visitorType = visitorType;
    }

    public Integer getWeekend() {
        return weekend;
    }

    public void setWeekend(Integer weekend) {
        this.weekend = weekend;
    }

    public Integer getRevenue() {
        return revenue;
    }

    public void setRevenue(Integer revenue) {
        this.revenue = revenue;
    }

    public Integer getPageDepth() {
        return pageDepth;
    }

    public void setPageDepth(Integer pageDepth) {
        this.pageDepth = pageDepth;
    }

    public Double getTotalDuration() {
        return totalDuration;
    }

    public void setTotalDuration(Double totalDuration) {
        this.totalDuration = totalDuration;
    }

    public Integer getIsBounce() {
        return isBounce;
    }

    public void setIsBounce(Integer isBounce) {
        this.isBounce = isBounce;
    }
}
