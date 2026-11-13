package com.datavis.shopping.controller.m2;

import com.datavis.shopping.common.PageResult;
import com.datavis.shopping.common.Result;
import com.datavis.shopping.dto.BrowserDTO;
import com.datavis.shopping.dto.ConfusionMatrixDTO;
import com.datavis.shopping.dto.FeatureImportanceDTO;
import com.datavis.shopping.dto.ModelMetricDTO;
import com.datavis.shopping.dto.OsDTO;
import com.datavis.shopping.dto.PageValueBinDTO;
import com.datavis.shopping.dto.SpecialDayDTO;
import com.datavis.shopping.dto.VisitorPurchaseDTO;
import com.datavis.shopping.entity.AlertRule;
import com.datavis.shopping.service.AlertRuleService;
import com.datavis.shopping.service.MemberTwoService;
import com.datavis.shopping.service.SessionService;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 成员二接口：转化预测与精细化运营大屏 + 预警规则 CRUD。
 */
@RestController
@RequestMapping("/api/m2")
public class MemberTwoController {

    private final MemberTwoService memberTwoService;
    private final AlertRuleService alertRuleService;
    private final SessionService sessionService;

    public MemberTwoController(MemberTwoService memberTwoService,
                               AlertRuleService alertRuleService,
                               SessionService sessionService) {
        this.memberTwoService = memberTwoService;
        this.alertRuleService = alertRuleService;
        this.sessionService = sessionService;
    }

    /** PageValues 价值分箱。 */
    @GetMapping("/pagevalues")
    public Result<List<PageValueBinDTO>> pageValues() {
        return Result.ok(sessionService.getPageValues());
    }

    /** 模型指标对比。 */
    @GetMapping("/model/metrics")
    public Result<List<ModelMetricDTO>> modelMetrics() {
        return Result.ok(memberTwoService.getModelMetrics());
    }

    /** 混淆矩阵，默认 RandomForest。 */
    @GetMapping("/model/confusion")
    public Result<ConfusionMatrixDTO> modelConfusion(
            @RequestParam(required = false) String model) {
        ConfusionMatrixDTO dto = memberTwoService.getConfusion(model);
        if (dto == null) {
            return Result.fail(500, "模型不存在: " + model);
        }
        return Result.ok(dto);
    }

    /** 特征重要性 Top12。 */
    @GetMapping("/feature-importance")
    public Result<List<FeatureImportanceDTO>> featureImportance() {
        return Result.ok(memberTwoService.getFeatureImportance());
    }

    /** 特殊日期接近度分布。 */
    @GetMapping("/special-day")
    public Result<List<SpecialDayDTO>> specialDay() {
        return Result.ok(sessionService.getSpecialDay());
    }

    /** 操作系统构成 Top8。 */
    @GetMapping("/os")
    public Result<List<OsDTO>> os() {
        return Result.ok(sessionService.getOs());
    }

    /** 浏览器构成。 */
    @GetMapping("/browser")
    public Result<List<BrowserDTO>> browser() {
        return Result.ok(sessionService.getBrowser());
    }

    /** 设备构成汇总（OS + 浏览器），便于大屏一次取全。 */
    @GetMapping("/device")
    public Result<DeviceComposition> device() {
        return Result.ok(new DeviceComposition(sessionService.getOs(), sessionService.getBrowser()));
    }

    /** 设备构成聚合结构。 */
    public record DeviceComposition(List<OsDTO> os, List<BrowserDTO> browser) {
    }

    /** 访客类型 × 周末 成交热力数据。 */
    @GetMapping("/visitor-purchase")
    public Result<List<VisitorPurchaseDTO>> visitorPurchase() {
        return Result.ok(sessionService.getVisitorPurchase());
    }

    // ==================== 预警规则 CRUD ====================

    /** 全部规则列表。 */
    @GetMapping("/rule/list")
    public Result<List<AlertRule>> ruleList() {
        return Result.ok(alertRuleService.list());
    }

    /** 分页 + 关键字查询。 */
    @GetMapping("/rule/page")
    public Result<PageResult<AlertRule>> rulePage(
            @RequestParam(defaultValue = "1") int pageNum,
            @RequestParam(defaultValue = "10") int pageSize,
            @RequestParam(required = false) String keyword) {
        return Result.ok(alertRuleService.page(pageNum, pageSize, keyword));
    }

    /** 按主键查询规则。 */
    @GetMapping("/rule/{id}")
    public Result<AlertRule> ruleById(@PathVariable Long id) {
        AlertRule rule = alertRuleService.getById(id);
        if (rule == null) {
            return Result.fail(500, "规则不存在: " + id);
        }
        return Result.ok(rule);
    }

    /** 新增规则。 */
    @PostMapping("/rule")
    public Result<AlertRule> ruleCreate(@RequestBody AlertRule rule) {
        return Result.ok("新增成功", alertRuleService.create(rule));
    }

    /** 更新规则。 */
    @PutMapping("/rule/{id}")
    public Result<AlertRule> ruleUpdate(@PathVariable Long id, @RequestBody AlertRule rule) {
        AlertRule updated = alertRuleService.update(id, rule);
        if (updated == null) {
            return Result.fail(500, "规则不存在: " + id);
        }
        return Result.ok("更新成功", updated);
    }

    /** 启用/停用切换。 */
    @PutMapping("/rule/{id}/toggle")
    public Result<AlertRule> ruleToggle(@PathVariable Long id) {
        AlertRule toggled = alertRuleService.toggle(id);
        if (toggled == null) {
            return Result.fail(500, "规则不存在: " + id);
        }
        return Result.ok("切换成功", toggled);
    }

    /** 删除规则。 */
    @DeleteMapping("/rule/{id}")
    public Result<Boolean> ruleDelete(@PathVariable Long id) {
        boolean deleted = alertRuleService.delete(id);
        if (!deleted) {
            return Result.fail(500, "规则不存在: " + id);
        }
        return Result.ok("删除成功", true);
    }
}
