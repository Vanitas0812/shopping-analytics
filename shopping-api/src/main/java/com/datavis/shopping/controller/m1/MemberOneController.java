package com.datavis.shopping.controller.m1;

import com.datavis.shopping.common.PageResult;
import com.datavis.shopping.common.Result;
import com.datavis.shopping.dto.BounceExitDTO;
import com.datavis.shopping.dto.MonthlyTrendDTO;
import com.datavis.shopping.dto.OverviewDTO;
import com.datavis.shopping.dto.PageDepthDTO;
import com.datavis.shopping.dto.RegionDTO;
import com.datavis.shopping.dto.TrafficSourceDTO;
import com.datavis.shopping.dto.VisitorTypeDTO;
import com.datavis.shopping.dto.WeekendDTO;
import com.datavis.shopping.entity.VisitorSession;
import com.datavis.shopping.service.MemberOneService;
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
 * 成员一接口：用户行为与流量运营大屏 + 会话明细 CRUD。
 */
@RestController
@RequestMapping("/api/m1")
public class MemberOneController {

    private final MemberOneService memberOneService;
    private final SessionService sessionService;

    public MemberOneController(MemberOneService memberOneService, SessionService sessionService) {
        this.memberOneService = memberOneService;
        this.sessionService = sessionService;
    }

    /** 全局 KPI 卡。 */
    @GetMapping("/overview")
    public Result<OverviewDTO> overview() {
        return Result.ok(memberOneService.getOverview());
    }

    /** 月度访问与转化趋势（1-12 月齐全）。 */
    @GetMapping("/monthly-trend")
    public Result<List<MonthlyTrendDTO>> monthlyTrend() {
        return Result.ok(memberOneService.getMonthlyTrend());
    }

    /** 访客类型对比。 */
    @GetMapping("/visitor-type")
    public Result<List<VisitorTypeDTO>> visitorType() {
        return Result.ok(memberOneService.getVisitorType());
    }

    /** 流量类型效率 Top10。 */
    @GetMapping("/traffic-source")
    public Result<List<TrafficSourceDTO>> trafficSource() {
        return Result.ok(memberOneService.getTrafficSource());
    }

    /** 页面访问深度分层。 */
    @GetMapping("/page-depth")
    public Result<List<PageDepthDTO>> pageDepth() {
        return Result.ok(memberOneService.getPageDepth());
    }

    /** 跳出率 / 退出率分箱。 */
    @GetMapping("/bounce-exit")
    public Result<List<BounceExitDTO>> bounceExit() {
        return Result.ok(memberOneService.getBounceExit());
    }

    /** 区域分布（Region 为匿名编码）。 */
    @GetMapping("/region")
    public Result<List<RegionDTO>> region() {
        return Result.ok(memberOneService.getRegion());
    }

    /** 周末对比。 */
    @GetMapping("/weekend")
    public Result<List<WeekendDTO>> weekend() {
        return Result.ok(memberOneService.getWeekend());
    }

    // ==================== 会话明细 CRUD ====================

    /** 分页查询会话明细。 */
    @GetMapping("/session/page")
    public Result<PageResult<VisitorSession>> sessionPage(
            @RequestParam(defaultValue = "1") int pageNum,
            @RequestParam(defaultValue = "10") int pageSize,
            @RequestParam(required = false) String month,
            @RequestParam(required = false) String visitorType,
            @RequestParam(required = false) Integer revenue) {
        return Result.ok(sessionService.page(pageNum, pageSize, month, visitorType, revenue));
    }

    /** 按主键查询单条会话。 */
    @GetMapping("/session/{id}")
    public Result<VisitorSession> sessionById(@PathVariable Long id) {
        VisitorSession session = sessionService.getById(id);
        if (session == null) {
            return Result.fail(500, "会话不存在: " + id);
        }
        return Result.ok(session);
    }

    /** 新增会话。 */
    @PostMapping("/session")
    public Result<VisitorSession> sessionCreate(@RequestBody VisitorSession session) {
        return Result.ok("新增成功", sessionService.create(session));
    }

    /** 更新会话。 */
    @PutMapping("/session/{id}")
    public Result<VisitorSession> sessionUpdate(@PathVariable Long id,
                                                @RequestBody VisitorSession session) {
        VisitorSession updated = sessionService.update(id, session);
        if (updated == null) {
            return Result.fail(500, "会话不存在: " + id);
        }
        return Result.ok("更新成功", updated);
    }

    /** 删除会话。 */
    @DeleteMapping("/session/{id}")
    public Result<Boolean> sessionDelete(@PathVariable Long id) {
        boolean deleted = sessionService.delete(id);
        if (!deleted) {
            return Result.fail(500, "会话不存在: " + id);
        }
        return Result.ok("删除成功", true);
    }
}
