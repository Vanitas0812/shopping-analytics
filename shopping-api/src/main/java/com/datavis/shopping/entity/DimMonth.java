package com.datavis.shopping.entity;

/**
 * 月份维表实体，对应表 dim_month。
 */
public class DimMonth {

    private Integer monthNum;
    private String monthName;
    private String monthCn;
    private Integer monthOrder;

    public Integer getMonthNum() {
        return monthNum;
    }

    public void setMonthNum(Integer monthNum) {
        this.monthNum = monthNum;
    }

    public String getMonthName() {
        return monthName;
    }

    public void setMonthName(String monthName) {
        this.monthName = monthName;
    }

    public String getMonthCn() {
        return monthCn;
    }

    public void setMonthCn(String monthCn) {
        this.monthCn = monthCn;
    }

    public Integer getMonthOrder() {
        return monthOrder;
    }

    public void setMonthOrder(Integer monthOrder) {
        this.monthOrder = monthOrder;
    }
}
