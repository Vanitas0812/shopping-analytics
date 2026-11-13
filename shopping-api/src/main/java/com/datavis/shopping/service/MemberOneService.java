package com.datavis.shopping.service;

import com.datavis.shopping.common.Calc;
import com.datavis.shopping.dto.BounceExitDTO;
import com.datavis.shopping.dto.BucketStat;
import com.datavis.shopping.dto.MonthlyTrendDTO;
import com.datavis.shopping.dto.OverviewDTO;
import com.datavis.shopping.dto.OverviewRaw;
import com.datavis.shopping.dto.PageDepthDTO;
import com.datavis.shopping.dto.RegionDTO;
import com.datavis.shopping.dto.TrafficSourceDTO;
import com.datavis.shopping.dto.VisitorTypeDTO;
import com.datavis.shopping.dto.WeekendDTO;
import com.datavis.shopping.mapper.VisitorSessionMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 成员一：用户行为与流量运营大屏业务层。
 * 所有数值均来自 ods_visitor_session 的实时 SQL 聚合。
 */
@Service
public class MemberOneService {

    /** 页面深度分层固定顺序（保证图表 X 轴稳定）。 */
    private static final List<String> DEPTH_ORDER =
            List.of("1-5", "6-15", "16-30", "31-60", "60+");

    /** 跳出率分箱固定顺序。 */
    private static final List<String> BOUNCE_ORDER =
            List.of("0", "(0,0.02)", "[0.02,0.05)", "[0.05,0.1)", "[0.1,0.2]");

    private final VisitorSessionMapper sessionMapper;

    public MemberOneService(VisitorSessionMapper sessionMapper) {
        this.sessionMapper = sessionMapper;
    }

    /** 全局 KPI 卡。 */
    @Transactional(readOnly = true)
    public OverviewDTO getOverview() {
        OverviewRaw raw = sessionMapper.selectOverviewRaw();
        long total = raw.totalSessions();
        return new OverviewDTO(
                total,
                raw.totalRevenue(),
                Calc.ratio(raw.totalRevenue(), total),
                Calc.round4(raw.avgPageDepth()),
                Calc.round4(raw.avgDuration()),
                Calc.round4(raw.avgBounceRate()),
                Calc.round4(raw.avgExitRate()),
                Calc.ratio(raw.newVisitorCount(), total),
                Calc.ratio(raw.returningVisitorCount(), total));
    }

    /** 月度趋势，1-12 月齐全。 */
    @Transactional(readOnly = true)
    public List<MonthlyTrendDTO> getMonthlyTrend() {
        List<VisitorSessionMapper.MonthlyRow> rows = sessionMapper.selectMonthlyTrend();
        List<MonthlyTrendDTO> result = new ArrayList<>(rows.size());
        for (VisitorSessionMapper.MonthlyRow row : rows) {
            result.add(new MonthlyTrendDTO(
                    row.monthNum(), row.monthCn(), row.sessions(), row.conversions(),
                    Calc.ratio(row.conversions(), row.sessions())));
        }
        return result;
    }

    /**
     * 访客类型对比。
     * 注意：pct 与 conversionRate 同为 0~1 小数（占比），前端统一 ×100 显示百分比。
     */
    @Transactional(readOnly = true)
    public List<VisitorTypeDTO> getVisitorType() {
        List<BucketStat> rows = sessionMapper.selectVisitorType();
        long total = rows.stream().mapToLong(BucketStat::sessions).sum();
        List<VisitorTypeDTO> result = new ArrayList<>(rows.size());
        for (BucketStat row : rows) {
            result.add(new VisitorTypeDTO(row.label(), row.sessions(), row.conversions(),
                    Calc.ratio(row.conversions(), row.sessions()),
                    Calc.ratio(row.sessions(), total)));
        }
        return result;
    }

    /** 流量类型 Top10。 */
    @Transactional(readOnly = true)
    public List<TrafficSourceDTO> getTrafficSource() {
        List<BucketStat> rows = sessionMapper.selectTrafficSourceTop10();
        List<TrafficSourceDTO> result = new ArrayList<>(rows.size());
        for (BucketStat row : rows) {
            result.add(new TrafficSourceDTO(Integer.parseInt(row.label()), row.sessions(),
                    row.conversions(), Calc.ratio(row.conversions(), row.sessions())));
        }
        return result;
    }

    /** 页面访问深度分层。 */
    @Transactional(readOnly = true)
    public List<PageDepthDTO> getPageDepth() {
        return orderedBuckets(sessionMapper.selectPageDepthBuckets(), DEPTH_ORDER).stream()
                .map(b -> new PageDepthDTO(b.label(), b.sessions(), b.conversions(),
                        Calc.ratio(b.conversions(), b.sessions())))
                .toList();
    }

    /**
     * 跳出率 / 退出率分箱：一次返回 10 条（跳出 5 档 + 退出 5 档），
     * 每行带 metric（bounce_rate / exit_rate）与 metricCn（跳出率 / 退出率），
     * 供大屏拆成两条序列做双序列对比，图例可直接用 metricCn 展示中文。
     * 区间口径两序列完全一致，缺失档补 0。
     */
    @Transactional(readOnly = true)
    public List<BounceExitDTO> getBounceExit() {
        List<BounceExitDTO> result = new ArrayList<>(BOUNCE_ORDER.size() * 2);
        appendRateSeries(result, "bounce_rate", "跳出率", sessionMapper.selectBounceRateBuckets());
        appendRateSeries(result, "exit_rate", "退出率", sessionMapper.selectExitRateBuckets());
        return result;
    }

    /** 按固定区间顺序拼接一条比率序列。 */
    private void appendRateSeries(List<BounceExitDTO> target, String metric, String metricCn,
                                  List<BucketStat> rows) {
        for (BucketStat b : orderedBuckets(rows, BOUNCE_ORDER)) {
            target.add(new BounceExitDTO(metric, metricCn, b.label(), b.sessions(), b.conversions(),
                    Calc.ratio(b.conversions(), b.sessions())));
        }
    }

    /** 区域分布（Region 为匿名编码，按编码分组）。 */
    @Transactional(readOnly = true)
    public List<RegionDTO> getRegion() {
        List<BucketStat> rows = sessionMapper.selectRegion();
        List<RegionDTO> result = new ArrayList<>(rows.size());
        for (BucketStat row : rows) {
            result.add(new RegionDTO(Integer.parseInt(row.label()), row.sessions(), row.conversions(),
                    Calc.ratio(row.conversions(), row.sessions())));
        }
        return result;
    }

    /** 周末对比。 */
    @Transactional(readOnly = true)
    public List<WeekendDTO> getWeekend() {
        List<BucketStat> rows = sessionMapper.selectWeekend();
        List<WeekendDTO> result = new ArrayList<>(rows.size());
        for (BucketStat row : rows) {
            result.add(new WeekendDTO(Integer.parseInt(row.label()), row.sessions(), row.conversions(),
                    Calc.ratio(row.conversions(), row.sessions())));
        }
        return result;
    }

    /** 按固定顺序重排分箱结果，缺失区间补 0，保证图表坐标轴不错位。 */
    private List<BucketStat> orderedBuckets(List<BucketStat> rows, List<String> order) {
        Map<String, BucketStat> index = new LinkedHashMap<>();
        for (String label : order) {
            index.put(label, new BucketStat(label, 0L, 0L));
        }
        for (BucketStat row : rows) {
            index.put(row.label(), row);
        }
        return new ArrayList<>(index.values());
    }
}
