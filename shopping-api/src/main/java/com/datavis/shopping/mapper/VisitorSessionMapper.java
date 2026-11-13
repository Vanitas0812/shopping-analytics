package com.datavis.shopping.mapper;

import com.datavis.shopping.dto.BucketStat;
import com.datavis.shopping.dto.OverviewRaw;
import com.datavis.shopping.entity.VisitorSession;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

/**
 * 访客会话明细数据访问层（JdbcTemplate 真实访问 MySQL）。
 * 所有统计均为运行时 SQL 聚合，不存在任何硬编码结果。
 */
@Repository
public class VisitorSessionMapper {

    private static final String BASE_COLUMNS =
            "session_id, administrative, administrative_duration, informational, informational_duration, "
            + "product_related, product_related_duration, bounce_rates, exit_rates, page_values, special_day, "
            + "month, month_num, operating_systems, browser, region, traffic_type, visitor_type, weekend, revenue, "
            + "page_depth, total_duration, is_bounce";

    private static final String INSERT_SQL =
            "INSERT INTO ods_visitor_session (administrative, administrative_duration, informational, "
            + "informational_duration, product_related, product_related_duration, bounce_rates, exit_rates, "
            + "page_values, special_day, month, month_num, operating_systems, browser, region, traffic_type, "
            + "visitor_type, weekend, revenue, page_depth, total_duration, is_bounce) "
            + "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)";

    private static final String UPDATE_SQL =
            "UPDATE ods_visitor_session SET administrative=?, administrative_duration=?, informational=?, "
            + "informational_duration=?, product_related=?, product_related_duration=?, bounce_rates=?, exit_rates=?, "
            + "page_values=?, special_day=?, month=?, month_num=?, operating_systems=?, browser=?, region=?, "
            + "traffic_type=?, visitor_type=?, weekend=?, revenue=?, page_depth=?, total_duration=?, is_bounce=? "
            + "WHERE session_id=?";

    private final JdbcTemplate jdbcTemplate;

    public VisitorSessionMapper(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    private static final RowMapper<VisitorSession> SESSION_ROW_MAPPER = (rs, rowNum) -> {
        VisitorSession v = new VisitorSession();
        v.setSessionId(rs.getLong("session_id"));
        v.setAdministrative(rs.getInt("administrative"));
        v.setAdministrativeDuration(rs.getDouble("administrative_duration"));
        v.setInformational(rs.getInt("informational"));
        v.setInformationalDuration(rs.getDouble("informational_duration"));
        v.setProductRelated(rs.getInt("product_related"));
        v.setProductRelatedDuration(rs.getDouble("product_related_duration"));
        v.setBounceRates(rs.getDouble("bounce_rates"));
        v.setExitRates(rs.getDouble("exit_rates"));
        v.setPageValues(rs.getDouble("page_values"));
        v.setSpecialDay(rs.getDouble("special_day"));
        v.setMonth(rs.getString("month"));
        v.setMonthNum(rs.getInt("month_num"));
        v.setOperatingSystems(rs.getInt("operating_systems"));
        v.setBrowser(rs.getInt("browser"));
        v.setRegion(rs.getInt("region"));
        v.setTrafficType(rs.getInt("traffic_type"));
        v.setVisitorType(rs.getString("visitor_type"));
        v.setWeekend(rs.getInt("weekend"));
        v.setRevenue(rs.getInt("revenue"));
        v.setPageDepth(rs.getInt("page_depth"));
        v.setTotalDuration(rs.getDouble("total_duration"));
        v.setIsBounce(rs.getInt("is_bounce"));
        return v;
    };

    private static final RowMapper<BucketStat> BUCKET_ROW_MAPPER = (rs, rowNum) ->
            new BucketStat(rs.getString(1), rs.getLong(2), rs.getLong(3));

    private static final RowMapper<BucketStat> INT_BUCKET_ROW_MAPPER = (rs, rowNum) ->
            new BucketStat(String.valueOf(rs.getInt(1)), rs.getLong(2), rs.getLong(3));

    // ==================== 全局 KPI ====================

    /** 全局 KPI 聚合。 */
    public OverviewRaw selectOverviewRaw() {
        String sql = "SELECT COUNT(*) AS total_sessions, "
                + "COALESCE(SUM(revenue),0) AS total_revenue, "
                + "COALESCE(AVG(page_depth),0) AS avg_page_depth, "
                + "COALESCE(AVG(total_duration),0) AS avg_duration, "
                + "COALESCE(AVG(bounce_rates),0) AS avg_bounce_rate, "
                + "COALESCE(AVG(exit_rates),0) AS avg_exit_rate, "
                + "COALESCE(SUM(visitor_type='New_Visitor'),0) AS new_cnt, "
                + "COALESCE(SUM(visitor_type='Returning_Visitor'),0) AS ret_cnt "
                + "FROM ods_visitor_session";
        return jdbcTemplate.queryForObject(sql, (rs, rowNum) -> new OverviewRaw(
                rs.getLong("total_sessions"),
                rs.getLong("total_revenue"),
                rs.getDouble("avg_page_depth"),
                rs.getDouble("avg_duration"),
                rs.getDouble("avg_bounce_rate"),
                rs.getDouble("avg_exit_rate"),
                rs.getLong("new_cnt"),
                rs.getLong("ret_cnt")));
    }

    /** 会话总行数。 */
    public long countAll() {
        Long n = jdbcTemplate.queryForObject("SELECT COUNT(*) FROM ods_visitor_session", Long.class);
        return n == null ? 0L : n;
    }

    // ==================== 成员一统计 ====================

    /** 月度趋势：以 dim_month 左连接聚合，保证 1-12 月齐全，缺失月为 0。 */
    public List<MonthlyRow> selectMonthlyTrend() {
        String sql = "SELECT dm.month_cn, COALESCE(t.sessions,0) AS sessions, COALESCE(t.conversions,0) AS conversions, dm.month_num "
                + "FROM dim_month dm LEFT JOIN ("
                + "  SELECT month_num, COUNT(*) AS sessions, COALESCE(SUM(revenue),0) AS conversions "
                + "  FROM ods_visitor_session GROUP BY month_num"
                + ") t ON dm.month_num = t.month_num ORDER BY dm.month_order";
        return jdbcTemplate.query(sql, MONTHLY_ROW_MAPPER);
    }

    private static final RowMapper<MonthlyRow> MONTHLY_ROW_MAPPER = (rs, rowNum) -> new MonthlyRow(
            rs.getInt("month_num"), rs.getString("month_cn"),
            rs.getLong("sessions"), rs.getLong("conversions"));

    /** 月度趋势专用行（携带 monthNum）。 */
    public record MonthlyRow(int monthNum, String monthCn, long sessions, long conversions) {
    }

    /** 访客类型对比。 */
    public List<BucketStat> selectVisitorType() {
        String sql = "SELECT visitor_type, COUNT(*) AS sessions, COALESCE(SUM(revenue),0) AS conversions "
                + "FROM ods_visitor_session GROUP BY visitor_type ORDER BY sessions DESC";
        return jdbcTemplate.query(sql, (rs, rowNum) -> new BucketStat(
                rs.getString("visitor_type"), rs.getLong("sessions"), rs.getLong("conversions")));
    }

    /** 流量类型 Top10（按会话数降序）。 */
    public List<BucketStat> selectTrafficSourceTop10() {
        String sql = "SELECT traffic_type, COUNT(*) AS sessions, COALESCE(SUM(revenue),0) AS conversions "
                + "FROM ods_visitor_session GROUP BY traffic_type "
                + "ORDER BY sessions DESC, traffic_type ASC LIMIT 10";
        return jdbcTemplate.query(sql, INT_BUCKET_ROW_MAPPER);
    }

    /** 页面深度分层：0-5 归入 1-5 档，保证各档之和等于全量会话数。 */
    public List<BucketStat> selectPageDepthBuckets() {
        String sql = "SELECT CASE "
                + "  WHEN page_depth <= 5 THEN '1-5' "
                + "  WHEN page_depth <= 15 THEN '6-15' "
                + "  WHEN page_depth <= 30 THEN '16-30' "
                + "  WHEN page_depth <= 60 THEN '31-60' "
                + "  ELSE '60+' END AS bucket_label, "
                + "COUNT(*) AS sessions, COALESCE(SUM(revenue),0) AS conversions "
                + "FROM ods_visitor_session GROUP BY bucket_label";
        return jdbcTemplate.query(sql, BUCKET_ROW_MAPPER);
    }

    /** 跳出率分箱。 */
    public List<BucketStat> selectBounceRateBuckets() {
        return selectRateBuckets("bounce_rates");
    }

    /** 退出率分箱（区间口径与跳出率一致）。 */
    public List<BucketStat> selectExitRateBuckets() {
        return selectRateBuckets("exit_rates");
    }

    /**
     * 比率分箱通用实现。列名由内部常量传入（不接受外部输入），避免 SQL 注入。
     */
    private List<BucketStat> selectRateBuckets(String column) {
        String sql = "SELECT CASE "
                + "  WHEN " + column + " <= 0 THEN '0' "
                + "  WHEN " + column + " < 0.02 THEN '(0,0.02)' "
                + "  WHEN " + column + " < 0.05 THEN '[0.02,0.05)' "
                + "  WHEN " + column + " < 0.1 THEN '[0.05,0.1)' "
                + "  ELSE '[0.1,0.2]' END AS bucket_label, "
                + "COUNT(*) AS sessions, COALESCE(SUM(revenue),0) AS conversions "
                + "FROM ods_visitor_session GROUP BY bucket_label";
        return jdbcTemplate.query(sql, BUCKET_ROW_MAPPER);
    }

    /** 区域分布（Region 为匿名编码）。 */
    public List<BucketStat> selectRegion() {
        String sql = "SELECT region, COUNT(*) AS sessions, COALESCE(SUM(revenue),0) AS conversions "
                + "FROM ods_visitor_session GROUP BY region ORDER BY sessions DESC, region ASC";
        return jdbcTemplate.query(sql, INT_BUCKET_ROW_MAPPER);
    }

    /** 周末对比。 */
    public List<BucketStat> selectWeekend() {
        String sql = "SELECT weekend, COUNT(*) AS sessions, COALESCE(SUM(revenue),0) AS conversions "
                + "FROM ods_visitor_session GROUP BY weekend ORDER BY weekend ASC";
        return jdbcTemplate.query(sql, INT_BUCKET_ROW_MAPPER);
    }

    // ==================== 成员二统计 ====================

    /** PageValues 价值分箱。 */
    public List<BucketStat> selectPageValueBuckets() {
        String sql = "SELECT CASE "
                + "  WHEN page_values <= 0 THEN '=0' "
                + "  WHEN page_values < 10 THEN '(0,10)' "
                + "  WHEN page_values < 30 THEN '[10,30)' "
                + "  WHEN page_values < 60 THEN '[30,60)' "
                + "  WHEN page_values < 100 THEN '[60,100)' "
                + "  ELSE '100+' END AS bucket_label, "
                + "COUNT(*) AS sessions, COALESCE(SUM(revenue),0) AS conversions "
                + "FROM ods_visitor_session GROUP BY bucket_label";
        return jdbcTemplate.query(sql, BUCKET_ROW_MAPPER);
    }

    /** 特殊日期接近度分布。 */
    public List<BucketStat> selectSpecialDay() {
        String sql = "SELECT special_day, COUNT(*) AS sessions, COALESCE(SUM(revenue),0) AS conversions "
                + "FROM ods_visitor_session GROUP BY special_day ORDER BY special_day ASC";
        return jdbcTemplate.query(sql, (rs, rowNum) -> new BucketStat(
                String.valueOf(rs.getDouble("special_day")), rs.getLong("sessions"), rs.getLong("conversions")));
    }

    /** 操作系统构成 Top8（OS 为匿名编码）。 */
    public List<BucketStat> selectOperatingSystemTop8() {
        String sql = "SELECT operating_systems, COUNT(*) AS sessions "
                + "FROM ods_visitor_session GROUP BY operating_systems "
                + "ORDER BY sessions DESC, operating_systems ASC LIMIT 8";
        return jdbcTemplate.query(sql, (rs, rowNum) ->
                new BucketStat(String.valueOf(rs.getInt("operating_systems")), rs.getLong("sessions"), 0L));
    }

    /** 浏览器构成（Browser 为匿名编码）。 */
    public List<BucketStat> selectBrowser() {
        String sql = "SELECT browser, COUNT(*) AS sessions "
                + "FROM ods_visitor_session GROUP BY browser "
                + "ORDER BY sessions DESC, browser ASC";
        return jdbcTemplate.query(sql, (rs, rowNum) ->
                new BucketStat(String.valueOf(rs.getInt("browser")), rs.getLong("sessions"), 0L));
    }

    /** 访客类型 × 周末 交叉统计。 */
    public List<VisitorPurchaseRow> selectVisitorPurchase() {
        String sql = "SELECT visitor_type, weekend, COUNT(*) AS sessions, COALESCE(SUM(revenue),0) AS conversions "
                + "FROM ods_visitor_session GROUP BY visitor_type, weekend "
                + "ORDER BY visitor_type ASC, weekend ASC";
        return jdbcTemplate.query(sql, (rs, rowNum) -> new VisitorPurchaseRow(
                rs.getString("visitor_type"), rs.getInt("weekend"),
                rs.getLong("sessions"), rs.getLong("conversions")));
    }

    /** 访客类型×周末交叉行。 */
    public record VisitorPurchaseRow(String visitorType, int weekend, long sessions, long conversions) {
    }

    // ==================== 会话明细 CRUD ====================

    /** 分页总数（支持月份/访客类型/是否成交过滤）。 */
    public long countByCondition(String month, String visitorType, Integer revenue) {
        StringBuilder sql = new StringBuilder("SELECT COUNT(*) FROM ods_visitor_session WHERE 1=1");
        List<Object> args = new ArrayList<>();
        appendSessionWhere(sql, args, month, visitorType, revenue);
        Long n = jdbcTemplate.queryForObject(sql.toString(), Long.class, args.toArray());
        return n == null ? 0L : n;
    }

    /** 分页查询。 */
    public List<VisitorSession> selectPage(String month, String visitorType, Integer revenue,
                                           int offset, int pageSize) {
        StringBuilder sql = new StringBuilder("SELECT ").append(BASE_COLUMNS)
                .append(" FROM ods_visitor_session WHERE 1=1");
        List<Object> args = new ArrayList<>();
        appendSessionWhere(sql, args, month, visitorType, revenue);
        sql.append(" ORDER BY session_id ASC LIMIT ? OFFSET ?");
        args.add(pageSize);
        args.add(offset);
        return jdbcTemplate.query(sql.toString(), SESSION_ROW_MAPPER, args.toArray());
    }

    private void appendSessionWhere(StringBuilder sql, List<Object> args,
                                    String month, String visitorType, Integer revenue) {
        if (month != null && !month.isBlank()) {
            sql.append(" AND month = ?");
            args.add(month.trim());
        }
        if (visitorType != null && !visitorType.isBlank()) {
            sql.append(" AND visitor_type = ?");
            args.add(visitorType.trim());
        }
        if (revenue != null) {
            sql.append(" AND revenue = ?");
            args.add(revenue);
        }
    }

    /** 按主键查询单条。 */
    public VisitorSession selectById(Long sessionId) {
        String sql = "SELECT " + BASE_COLUMNS + " FROM ods_visitor_session WHERE session_id = ?";
        List<VisitorSession> list = jdbcTemplate.query(sql, SESSION_ROW_MAPPER, sessionId);
        return list.isEmpty() ? null : list.get(0);
    }

    /** 新增会话，返回自增主键。 */
    public long insert(VisitorSession v) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbcTemplate.update(con -> {
            PreparedStatement ps = con.prepareStatement(INSERT_SQL, Statement.RETURN_GENERATED_KEYS);
            ps.setInt(1, nz(v.getAdministrative()));
            ps.setDouble(2, nzd(v.getAdministrativeDuration()));
            ps.setInt(3, nz(v.getInformational()));
            ps.setDouble(4, nzd(v.getInformationalDuration()));
            ps.setInt(5, nz(v.getProductRelated()));
            ps.setDouble(6, nzd(v.getProductRelatedDuration()));
            ps.setDouble(7, nzd(v.getBounceRates()));
            ps.setDouble(8, nzd(v.getExitRates()));
            ps.setDouble(9, nzd(v.getPageValues()));
            ps.setDouble(10, nzd(v.getSpecialDay()));
            ps.setString(11, v.getMonth());
            ps.setInt(12, nz(v.getMonthNum()));
            ps.setInt(13, nz(v.getOperatingSystems()));
            ps.setInt(14, nz(v.getBrowser()));
            ps.setInt(15, nz(v.getRegion()));
            ps.setInt(16, nz(v.getTrafficType()));
            ps.setString(17, v.getVisitorType());
            ps.setInt(18, nz(v.getWeekend()));
            ps.setInt(19, nz(v.getRevenue()));
            ps.setInt(20, nz(v.getPageDepth()));
            ps.setDouble(21, nzd(v.getTotalDuration()));
            ps.setInt(22, nz(v.getIsBounce()));
            return ps;
        }, keyHolder);
        Number key = keyHolder.getKey();
        return key == null ? 0L : key.longValue();
    }

    /** 更新会话。 */
    public int update(VisitorSession v) {
        return jdbcTemplate.update(UPDATE_SQL,
                nz(v.getAdministrative()), nzd(v.getAdministrativeDuration()),
                nz(v.getInformational()), nzd(v.getInformationalDuration()),
                nz(v.getProductRelated()), nzd(v.getProductRelatedDuration()),
                nzd(v.getBounceRates()), nzd(v.getExitRates()), nzd(v.getPageValues()),
                nzd(v.getSpecialDay()), v.getMonth(), nz(v.getMonthNum()),
                nz(v.getOperatingSystems()), nz(v.getBrowser()), nz(v.getRegion()),
                nz(v.getTrafficType()), v.getVisitorType(), nz(v.getWeekend()),
                nz(v.getRevenue()), nz(v.getPageDepth()), nzd(v.getTotalDuration()),
                nz(v.getIsBounce()), v.getSessionId());
    }

    /** 删除会话。 */
    public int deleteById(Long sessionId) {
        return jdbcTemplate.update("DELETE FROM ods_visitor_session WHERE session_id = ?", sessionId);
    }

    private static int nz(Integer value) {
        return value == null ? 0 : value;
    }

    private static double nzd(Double value) {
        return value == null ? 0D : value;
    }
}
