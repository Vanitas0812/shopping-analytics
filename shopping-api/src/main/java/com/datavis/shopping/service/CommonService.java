package com.datavis.shopping.service;

import com.datavis.shopping.dto.HealthDTO;
import com.datavis.shopping.entity.DimMonth;
import com.datavis.shopping.mapper.CommonDictMapper;
import com.datavis.shopping.mapper.DimMonthMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * 通用业务层：健康检查与字典。
 */
@Service
public class CommonService {

    private final CommonDictMapper commonDictMapper;
    private final DimMonthMapper dimMonthMapper;

    public CommonService(CommonDictMapper commonDictMapper, DimMonthMapper dimMonthMapper) {
        this.commonDictMapper = commonDictMapper;
        this.dimMonthMapper = dimMonthMapper;
    }

    /** 健康检查：返回 UP 与真实会话表行数。 */
    @Transactional(readOnly = true)
    public HealthDTO health() {
        return new HealthDTO("UP", commonDictMapper.countSessions());
    }

    /** 月份维表全量。 */
    @Transactional(readOnly = true)
    public List<DimMonth> monthDict() {
        return dimMonthMapper.selectAll();
    }

    /** 访客类型取值。 */
    @Transactional(readOnly = true)
    public List<String> visitorTypeDict() {
        return commonDictMapper.selectVisitorTypes();
    }
}
