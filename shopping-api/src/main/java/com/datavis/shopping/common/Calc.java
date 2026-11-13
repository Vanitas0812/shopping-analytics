package com.datavis.shopping.common;

import java.math.BigDecimal;
import java.math.RoundingMode;

/**
 * 数值计算工具：比率统一保留 4 位小数，避免出现 0.15630000000000002 之类的浮点尾差。
 */
public final class Calc {

    private Calc() {
    }

    /** 比率/占比保留 4 位小数（四舍五入）。 */
    public static double round4(double value) {
        if (Double.isNaN(value) || Double.isInfinite(value)) {
            return 0D;
        }
        return BigDecimal.valueOf(value).setScale(4, RoundingMode.HALF_UP).doubleValue();
    }

    /** 分子/分母，分母为 0 时返回 0。全口径比率统一返回 0~1 小数，前端自行 ×100 显示百分比。 */
    public static double ratio(long numerator, long denominator) {
        if (denominator == 0L) {
            return 0D;
        }
        return round4((double) numerator / (double) denominator);
    }

    /** 空值兜底为 0。 */
    public static double dbl(Double value) {
        return value == null ? 0D : value;
    }
}
