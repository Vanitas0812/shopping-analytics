package com.datavis.shopping.mapper;

import com.datavis.shopping.entity.DimMonth;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * 月份维表数据访问层。
 */
@Repository
public class DimMonthMapper {

    private static final RowMapper<DimMonth> ROW_MAPPER = (rs, rowNum) -> {
        DimMonth m = new DimMonth();
        m.setMonthNum(rs.getInt("month_num"));
        m.setMonthName(rs.getString("month_name"));
        m.setMonthCn(rs.getString("month_cn"));
        m.setMonthOrder(rs.getInt("month_order"));
        return m;
    };

    private final JdbcTemplate jdbcTemplate;

    public DimMonthMapper(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** 全量月份维表，按 month_order 升序。 */
    public List<DimMonth> selectAll() {
        return jdbcTemplate.query(
                "SELECT month_num, month_name, month_cn, month_order FROM dim_month ORDER BY month_order",
                ROW_MAPPER);
    }
}
