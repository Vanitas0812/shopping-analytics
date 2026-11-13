package com.datavis.shopping.controller.common;

import com.datavis.shopping.common.Result;
import com.datavis.shopping.dto.HealthDTO;
import com.datavis.shopping.entity.DimMonth;
import com.datavis.shopping.service.CommonService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 通用接口：健康检查与字典。
 */
@RestController
@RequestMapping("/api/common")
public class CommonController {

    private final CommonService commonService;

    public CommonController(CommonService commonService) {
        this.commonService = commonService;
    }

    /** 健康检查：{status:"UP", rows:<会话表行数>}。 */
    @GetMapping("/health")
    public Result<HealthDTO> health() {
        return Result.ok(commonService.health());
    }

    /** 月份维表全量。 */
    @GetMapping("/dict/month")
    public Result<List<DimMonth>> monthDict() {
        return Result.ok(commonService.monthDict());
    }

    /** 访客类型取值。 */
    @GetMapping("/dict/visitor-type")
    public Result<List<String>> visitorTypeDict() {
        return Result.ok(commonService.visitorTypeDict());
    }
}
