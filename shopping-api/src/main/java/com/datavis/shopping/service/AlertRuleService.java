package com.datavis.shopping.service;

import com.datavis.shopping.common.PageResult;
import com.datavis.shopping.entity.AlertRule;
import com.datavis.shopping.mapper.AlertRuleMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Set;

/**
 * 转化预警规则业务层：完整增删改查 + 启用/停用切换。
 */
@Service
public class AlertRuleService {

    /** 允许的监控指标（与前端下拉一致）。 */
    private static final Set<String> ALLOWED_METRICS =
            Set.of("conversion_rate", "bounce_rate", "exit_rate", "page_values");

    /** 允许的比较符。 */
    private static final Set<String> ALLOWED_OPERATORS =
            Set.of(">", ">=", "<", "<=", "=");

    private final AlertRuleMapper alertRuleMapper;

    public AlertRuleService(AlertRuleMapper alertRuleMapper) {
        this.alertRuleMapper = alertRuleMapper;
    }

    /** 全部规则列表。 */
    @Transactional(readOnly = true)
    public List<AlertRule> list() {
        return alertRuleMapper.selectAll();
    }

    /** 关键字分页。 */
    @Transactional(readOnly = true)
    public PageResult<AlertRule> page(int pageNum, int pageSize, String keyword) {
        int safePageNum = Math.max(pageNum, 1);
        int safePageSize = Math.min(Math.max(pageSize, 1), 200);
        long total = alertRuleMapper.countByKeyword(keyword);
        int offset = (safePageNum - 1) * safePageSize;
        List<AlertRule> list = alertRuleMapper.selectPage(keyword, offset, safePageSize);
        return PageResult.of(total, safePageNum, safePageSize, list);
    }

    /** 按主键查询。 */
    @Transactional(readOnly = true)
    public AlertRule getById(Long ruleId) {
        return alertRuleMapper.selectById(ruleId);
    }

    /** 新增规则，返回新增后的完整对象。 */
    @Transactional(rollbackFor = Exception.class)
    public AlertRule create(AlertRule rule) {
        validate(rule);
        normalize(rule);
        long id = alertRuleMapper.insert(rule);
        return alertRuleMapper.selectById(id);
    }

    /** 更新规则，记录不存在返回 null。 */
    @Transactional(rollbackFor = Exception.class)
    public AlertRule update(Long ruleId, AlertRule rule) {
        if (alertRuleMapper.selectById(ruleId) == null) {
            return null;
        }
        validate(rule);
        normalize(rule);
        rule.setRuleId(ruleId);
        alertRuleMapper.update(rule);
        return alertRuleMapper.selectById(ruleId);
    }

    /** 启用/停用切换，返回切换后的对象；记录不存在返回 null。 */
    @Transactional(rollbackFor = Exception.class)
    public AlertRule toggle(Long ruleId) {
        if (alertRuleMapper.selectById(ruleId) == null) {
            return null;
        }
        alertRuleMapper.toggle(ruleId);
        return alertRuleMapper.selectById(ruleId);
    }

    /** 删除规则。 */
    @Transactional(rollbackFor = Exception.class)
    public boolean delete(Long ruleId) {
        return alertRuleMapper.deleteById(ruleId) > 0;
    }

    /** 字段校验：规则名、指标枚举、比较符枚举、阈值必填。 */
    private void validate(AlertRule rule) {
        if (rule == null) {
            throw new IllegalArgumentException("请求体不能为空");
        }
        if (rule.getRuleName() == null || rule.getRuleName().isBlank()) {
            throw new IllegalArgumentException("规则名称不能为空");
        }
        String metric = rule.getMetric() == null ? "" : rule.getMetric().trim();
        if (!ALLOWED_METRICS.contains(metric)) {
            throw new IllegalArgumentException("监控指标非法，可选值: " + ALLOWED_METRICS);
        }
        String operator = rule.getOperatorCmp() == null ? "" : rule.getOperatorCmp().trim();
        if (!ALLOWED_OPERATORS.contains(operator)) {
            throw new IllegalArgumentException("比较符非法，可选值: > >= < <= =");
        }
        if (rule.getThresholdValue() == null) {
            throw new IllegalArgumentException("阈值不能为空");
        }
    }

    /** 入参归一化：去空格、缺省启用。 */
    private void normalize(AlertRule rule) {
        rule.setRuleName(rule.getRuleName().trim());
        rule.setMetric(rule.getMetric().trim());
        rule.setOperatorCmp(rule.getOperatorCmp().trim());
        if (rule.getEnabled() == null) {
            rule.setEnabled(1);
        }
        if (rule.getRemark() != null) {
            String remark = rule.getRemark().trim();
            rule.setRemark(remark.isEmpty() ? null : remark);
        }
    }
}
