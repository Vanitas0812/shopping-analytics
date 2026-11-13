package com.datavis.shopping.service;

import com.datavis.shopping.common.Calc;
import com.datavis.shopping.common.PageResult;
import com.datavis.shopping.dto.BrowserDTO;
import com.datavis.shopping.dto.BucketStat;
import com.datavis.shopping.dto.OsDTO;
import com.datavis.shopping.dto.PageDepthDTO;
import com.datavis.shopping.dto.PageValueBinDTO;
import com.datavis.shopping.dto.SpecialDayDTO;
import com.datavis.shopping.dto.VisitorPurchaseDTO;
import com.datavis.shopping.entity.VisitorSession;
import com.datavis.shopping.mapper.VisitorSessionMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 会话明细业务层：分页查询与增删改查（成员一使用）。
 */
@Service
public class SessionService {

    private final VisitorSessionMapper sessionMapper;

    public SessionService(VisitorSessionMapper sessionMapper) {
        this.sessionMapper = sessionMapper;
    }

    /** 分页查询，支持月份 / 访客类型 / 是否成交过滤。 */
    @Transactional(readOnly = true)
    public PageResult<VisitorSession> page(int pageNum, int pageSize, String month,
                                           String visitorType, Integer revenue) {
        int safePageNum = Math.max(pageNum, 1);
        int safePageSize = Math.min(Math.max(pageSize, 1), 200);
        long total = sessionMapper.countByCondition(month, visitorType, revenue);
        int offset = (safePageNum - 1) * safePageSize;
        List<VisitorSession> list = sessionMapper.selectPage(month, visitorType, revenue, offset, safePageSize);
        return PageResult.of(total, safePageNum, safePageSize, list);
    }

    /** 按主键查询单条。 */
    @Transactional(readOnly = true)
    public VisitorSession getById(Long sessionId) {
        return sessionMapper.selectById(sessionId);
    }

    /** 新增会话，返回新增后的完整对象。 */
    @Transactional(rollbackFor = Exception.class)
    public VisitorSession create(VisitorSession session) {
        normalize(session);
        long id = sessionMapper.insert(session);
        session.setSessionId(id);
        return session;
    }

    /** 更新会话，返回更新后的完整对象；记录不存在返回 null。 */
    @Transactional(rollbackFor = Exception.class)
    public VisitorSession update(Long sessionId, VisitorSession session) {
        if (sessionMapper.selectById(sessionId) == null) {
            return null;
        }
        session.setSessionId(sessionId);
        normalize(session);
        sessionMapper.update(session);
        return sessionMapper.selectById(sessionId);
    }

    /** 删除会话。 */
    @Transactional(rollbackFor = Exception.class)
    public boolean delete(Long sessionId) {
        return sessionMapper.deleteById(sessionId) > 0;
    }

    /**
     * 入参归一化：衍生列若未显式提供，则由基础字段按统一口径推算，
     * 保证新增/更新的行与清洗管道口径一致。
     */
    private void normalize(VisitorSession s) {
        if (s.getAdministrative() == null) {
            s.setAdministrative(0);
        }
        if (s.getInformational() == null) {
            s.setInformational(0);
        }
        if (s.getProductRelated() == null) {
            s.setProductRelated(0);
        }
        if (s.getAdministrativeDuration() == null) {
            s.setAdministrativeDuration(0D);
        }
        if (s.getInformationalDuration() == null) {
            s.setInformationalDuration(0D);
        }
        if (s.getProductRelatedDuration() == null) {
            s.setProductRelatedDuration(0D);
        }
        if (s.getBounceRates() == null) {
            s.setBounceRates(0D);
        }
        if (s.getExitRates() == null) {
            s.setExitRates(0D);
        }
        if (s.getPageValues() == null) {
            s.setPageValues(0D);
        }
        if (s.getSpecialDay() == null) {
            s.setSpecialDay(0D);
        }
        if (s.getOperatingSystems() == null) {
            s.setOperatingSystems(1);
        }
        if (s.getBrowser() == null) {
            s.setBrowser(1);
        }
        if (s.getRegion() == null) {
            s.setRegion(1);
        }
        if (s.getTrafficType() == null) {
            s.setTrafficType(1);
        }
        if (s.getVisitorType() == null || s.getVisitorType().isBlank()) {
            s.setVisitorType("Returning_Visitor");
        }
        if (s.getWeekend() == null) {
            s.setWeekend(0);
        }
        if (s.getRevenue() == null) {
            s.setRevenue(0);
        }
        // 月份主键：未给 monthNum 时按月份名反查，仍无法确定则归为 1 月
        if (s.getMonthNum() == null) {
            s.setMonthNum(monthNumOf(s.getMonth()));
        }
        if (s.getMonth() == null || s.getMonth().isBlank()) {
            s.setMonth(monthNameOf(s.getMonthNum()));
        }
        // 衍生列：未显式提供则推算
        if (s.getPageDepth() == null) {
            s.setPageDepth(s.getAdministrative() + s.getInformational() + s.getProductRelated());
        }
        if (s.getTotalDuration() == null) {
            s.setTotalDuration(Calc.round4(s.getAdministrativeDuration()
                    + s.getInformationalDuration() + s.getProductRelatedDuration()));
        }
        if (s.getIsBounce() == null) {
            s.setIsBounce(s.getBounceRates() >= 0.2D ? 1 : 0);
        }
    }

    private static final Map<String, Integer> MONTH_NUM = new LinkedHashMap<>();
    private static final Map<Integer, String> MONTH_NAME = new LinkedHashMap<>();

    static {
        String[] names = {"Jan", "Feb", "Mar", "Apr", "May", "June", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"};
        for (int i = 0; i < names.length; i++) {
            MONTH_NUM.put(names[i].toLowerCase(), i + 1);
            MONTH_NAME.put(i + 1, names[i]);
        }
    }

    private static int monthNumOf(String month) {
        if (month == null) {
            return 1;
        }
        Integer num = MONTH_NUM.get(month.trim().toLowerCase());
        return num == null ? 1 : num;
    }

    private static String monthNameOf(int monthNum) {
        return MONTH_NAME.getOrDefault(monthNum, "Jan");
    }

    // ==================== 成员二统计（复用会话明细表） ====================

    /** PageValues 价值分箱固定顺序。 */
    private static final List<String> PV_ORDER =
            List.of("=0", "(0,10)", "[10,30)", "[30,60)", "[60,100)", "100+");

    /** PageValues 分箱。 */
    @Transactional(readOnly = true)
    public List<PageValueBinDTO> getPageValues() {
        List<BucketStat> rows = sessionMapper.selectPageValueBuckets();
        Map<String, BucketStat> index = new LinkedHashMap<>();
        for (String label : PV_ORDER) {
            index.put(label, new BucketStat(label, 0L, 0L));
        }
        for (BucketStat row : rows) {
            index.put(row.label(), row);
        }
        List<PageValueBinDTO> result = new ArrayList<>(index.size());
        for (BucketStat b : index.values()) {
            result.add(new PageValueBinDTO(b.label(), b.sessions(), b.conversions(),
                    Calc.ratio(b.conversions(), b.sessions())));
        }
        return result;
    }

    /** 特殊日期接近度分布。 */
    @Transactional(readOnly = true)
    public List<SpecialDayDTO> getSpecialDay() {
        List<BucketStat> rows = sessionMapper.selectSpecialDay();
        List<SpecialDayDTO> result = new ArrayList<>(rows.size());
        for (BucketStat row : rows) {
            result.add(new SpecialDayDTO(Double.parseDouble(row.label()), row.sessions(),
                    row.conversions(), Calc.ratio(row.conversions(), row.sessions())));
        }
        return result;
    }

    /** 操作系统构成 Top8。pct 为 0~1 小数（占比），前端 ×100 显示。 */
    @Transactional(readOnly = true)
    public List<OsDTO> getOs() {
        List<BucketStat> rows = sessionMapper.selectOperatingSystemTop8();
        long total = sessionMapper.countAll();
        List<OsDTO> result = new ArrayList<>(rows.size());
        for (BucketStat row : rows) {
            result.add(new OsDTO("OS-" + row.label(), row.sessions(), Calc.ratio(row.sessions(), total)));
        }
        return result;
    }

    /** 浏览器构成。pct 为 0~1 小数（占比），前端 ×100 显示。 */
    @Transactional(readOnly = true)
    public List<BrowserDTO> getBrowser() {
        List<BucketStat> rows = sessionMapper.selectBrowser();
        long total = sessionMapper.countAll();
        List<BrowserDTO> result = new ArrayList<>(rows.size());
        for (BucketStat row : rows) {
            result.add(new BrowserDTO(Integer.parseInt(row.label()), row.sessions(),
                    Calc.ratio(row.sessions(), total)));
        }
        return result;
    }

    /** 访客类型 × 周末 成交热力数据。 */
    @Transactional(readOnly = true)
    public List<VisitorPurchaseDTO> getVisitorPurchase() {
        List<VisitorSessionMapper.VisitorPurchaseRow> rows = sessionMapper.selectVisitorPurchase();
        List<VisitorPurchaseDTO> result = new ArrayList<>(rows.size());
        for (VisitorSessionMapper.VisitorPurchaseRow row : rows) {
            result.add(new VisitorPurchaseDTO(row.visitorType(), row.weekend(), row.sessions(),
                    Calc.ratio(row.conversions(), row.sessions())));
        }
        return result;
    }

    /** 页面深度分层（供成员二复用）。 */
    @Transactional(readOnly = true)
    public List<PageDepthDTO> getPageDepth() {
        List<String> order = List.of("1-5", "6-15", "16-30", "31-60", "60+");
        Map<String, BucketStat> index = new LinkedHashMap<>();
        for (String label : order) {
            index.put(label, new BucketStat(label, 0L, 0L));
        }
        for (BucketStat row : sessionMapper.selectPageDepthBuckets()) {
            index.put(row.label(), row);
        }
        return index.values().stream()
                .map(b -> new PageDepthDTO(b.label(), b.sessions(), b.conversions(),
                        Calc.ratio(b.conversions(), b.sessions())))
                .toList();
    }
}
