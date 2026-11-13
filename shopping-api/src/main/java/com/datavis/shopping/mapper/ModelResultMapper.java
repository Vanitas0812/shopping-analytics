package com.datavis.shopping.mapper;

import com.datavis.shopping.entity.ModelResult;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * 模型评估指标数据访问层。
 */
@Repository
public class ModelResultMapper {

    private static final RowMapper<ModelResult> ROW_MAPPER = (rs, rowNum) -> {
        ModelResult m = new ModelResult();
        m.setId(rs.getLong("id"));
        m.setModelName(rs.getString("model_name"));
        m.setMetricName(rs.getString("metric_name"));
        m.setMetricValue(rs.getDouble("metric_value"));
        m.setIsBest(rs.getInt("is_best"));
        return m;
    };

    private final JdbcTemplate jdbcTemplate;

    public ModelResultMapper(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** 全量指标行。 */
    public List<ModelResult> selectAll() {
        return jdbcTemplate.query("SELECT id, model_name, metric_name, metric_value, is_best "
                + "FROM dws_model_result ORDER BY model_name, metric_name", ROW_MAPPER);
    }

    /** 指定模型的全量指标行。 */
    public List<ModelResult> selectByModel(String modelName) {
        return jdbcTemplate.query("SELECT id, model_name, metric_name, metric_value, is_best "
                + "FROM dws_model_result WHERE model_name = ? ORDER BY metric_name", ROW_MAPPER, modelName);
    }
}
