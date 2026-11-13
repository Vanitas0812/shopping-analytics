package com.datavis.shopping.mapper;

import com.datavis.shopping.entity.AlertRule;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.List;

/**
 * 转化预警规则数据访问层（JdbcTemplate 真实访问 MySQL）。
 */
@Repository
public class AlertRuleMapper {

    private static final String BASE_COLUMNS =
            "rule_id, rule_name, metric, operator_cmp, threshold_value, traffic_type, "
            + "enabled, remark, create_time, update_time";

    private static final String INSERT_SQL =
            "INSERT INTO dws_alert_rule (rule_name, metric, operator_cmp, threshold_value, "
            + "traffic_type, enabled, remark) VALUES (?,?,?,?,?,?,?)";

    private static final String UPDATE_SQL =
            "UPDATE dws_alert_rule SET rule_name=?, metric=?, operator_cmp=?, threshold_value=?, "
            + "traffic_type=?, enabled=?, remark=? WHERE rule_id=?";

    private static final RowMapper<AlertRule> ROW_MAPPER = (rs, rowNum) -> {
        AlertRule r = new AlertRule();
        r.setRuleId(rs.getLong("rule_id"));
        r.setRuleName(rs.getString("rule_name"));
        r.setMetric(rs.getString("metric"));
        r.setOperatorCmp(rs.getString("operator_cmp"));
        double threshold = rs.getDouble("threshold_value");
        r.setThresholdValue(rs.wasNull() ? null : threshold);
        int trafficType = rs.getInt("traffic_type");
        r.setTrafficType(rs.wasNull() ? null : trafficType);
        r.setEnabled(rs.getInt("enabled"));
        r.setRemark(rs.getString("remark"));
        Timestamp createTime = rs.getTimestamp("create_time");
        r.setCreateTime(createTime == null ? null : createTime.toLocalDateTime());
        Timestamp updateTime = rs.getTimestamp("update_time");
        r.setUpdateTime(updateTime == null ? null : updateTime.toLocalDateTime());
        return r;
    };

    private final JdbcTemplate jdbcTemplate;

    public AlertRuleMapper(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** 全部规则，启用优先、再按创建时间倒序。 */
    public List<AlertRule> selectAll() {
        return jdbcTemplate.query("SELECT " + BASE_COLUMNS + " FROM dws_alert_rule "
                + "ORDER BY enabled DESC, rule_id ASC", ROW_MAPPER);
    }

    /** 关键字分页总数（匹配规则名/指标/备注）。 */
    public long countByKeyword(String keyword) {
        StringBuilder sql = new StringBuilder("SELECT COUNT(*) FROM dws_alert_rule WHERE 1=1");
        List<Object> args = new ArrayList<>();
        appendKeywordWhere(sql, args, keyword);
        Long n = jdbcTemplate.queryForObject(sql.toString(), Long.class, args.toArray());
        return n == null ? 0L : n;
    }

    /** 关键字分页查询。 */
    public List<AlertRule> selectPage(String keyword, int offset, int pageSize) {
        StringBuilder sql = new StringBuilder("SELECT ").append(BASE_COLUMNS)
                .append(" FROM dws_alert_rule WHERE 1=1");
        List<Object> args = new ArrayList<>();
        appendKeywordWhere(sql, args, keyword);
        sql.append(" ORDER BY rule_id ASC LIMIT ? OFFSET ?");
        args.add(pageSize);
        args.add(offset);
        return jdbcTemplate.query(sql.toString(), ROW_MAPPER, args.toArray());
    }

    private void appendKeywordWhere(StringBuilder sql, List<Object> args, String keyword) {
        if (keyword != null && !keyword.isBlank()) {
            String like = "%" + keyword.trim() + "%";
            sql.append(" AND (rule_name LIKE ? OR metric LIKE ? OR remark LIKE ?)");
            args.add(like);
            args.add(like);
            args.add(like);
        }
    }

    /** 按主键查询。 */
    public AlertRule selectById(Long ruleId) {
        List<AlertRule> list = jdbcTemplate.query(
                "SELECT " + BASE_COLUMNS + " FROM dws_alert_rule WHERE rule_id = ?", ROW_MAPPER, ruleId);
        return list.isEmpty() ? null : list.get(0);
    }

    /** 新增规则，返回自增主键。 */
    public long insert(AlertRule rule) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbcTemplate.update(con -> {
            PreparedStatement ps = con.prepareStatement(INSERT_SQL, Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, rule.getRuleName());
            ps.setString(2, rule.getMetric());
            ps.setString(3, rule.getOperatorCmp());
            ps.setDouble(4, rule.getThresholdValue() == null ? 0D : rule.getThresholdValue());
            if (rule.getTrafficType() == null) {
                ps.setNull(5, java.sql.Types.INTEGER);
            } else {
                ps.setInt(5, rule.getTrafficType());
            }
            ps.setInt(6, rule.getEnabled() == null ? 1 : rule.getEnabled());
            ps.setString(7, rule.getRemark());
            return ps;
        }, keyHolder);
        Number key = keyHolder.getKey();
        return key == null ? 0L : key.longValue();
    }

    /** 更新规则。 */
    public int update(AlertRule rule) {
        return jdbcTemplate.update(UPDATE_SQL,
                rule.getRuleName(), rule.getMetric(), rule.getOperatorCmp(),
                rule.getThresholdValue() == null ? 0D : rule.getThresholdValue(),
                rule.getTrafficType(), rule.getEnabled() == null ? 1 : rule.getEnabled(),
                rule.getRemark(), rule.getRuleId());
    }

    /** 启用/停用切换。 */
    public int toggle(Long ruleId) {
        return jdbcTemplate.update(
                "UPDATE dws_alert_rule SET enabled = CASE WHEN enabled = 1 THEN 0 ELSE 1 END WHERE rule_id = ?",
                ruleId);
    }

    /** 删除规则。 */
    public int deleteById(Long ruleId) {
        return jdbcTemplate.update("DELETE FROM dws_alert_rule WHERE rule_id = ?", ruleId);
    }
}
