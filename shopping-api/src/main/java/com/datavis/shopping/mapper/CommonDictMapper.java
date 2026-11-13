package com.datavis.shopping.mapper;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * 通用字典数据访问层：从明细表现场取分组取值，保证字典与数据一致。
 */
@Repository
public class CommonDictMapper {

    private final JdbcTemplate jdbcTemplate;

    public CommonDictMapper(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** 访客类型取值（按会话数降序）。 */
    public List<String> selectVisitorTypes() {
        return jdbcTemplate.queryForList(
                "SELECT visitor_type FROM ods_visitor_session "
                + "GROUP BY visitor_type ORDER BY COUNT(*) DESC", String.class);
    }

    /** 会话表行数。 */
    public long countSessions() {
        Long n = jdbcTemplate.queryForObject("SELECT COUNT(*) FROM ods_visitor_session", Long.class);
        return n == null ? 0L : n;
    }
}
