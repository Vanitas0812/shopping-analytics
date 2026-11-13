package com.datavis.shopping.mapper;

import com.datavis.shopping.entity.FeatureImportance;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * 特征重要性数据访问层。
 */
@Repository
public class FeatureImportanceMapper {

    private static final RowMapper<FeatureImportance> ROW_MAPPER = (rs, rowNum) -> {
        FeatureImportance f = new FeatureImportance();
        f.setId(rs.getLong("id"));
        f.setFeatureKey(rs.getString("feature_key"));
        f.setFeatureCn(rs.getString("feature_cn"));
        f.setImportance(rs.getDouble("importance"));
        f.setRankNo(rs.getInt("rank_no"));
        return f;
    };

    private final JdbcTemplate jdbcTemplate;

    public FeatureImportanceMapper(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** 按 rank_no 升序取前 limit 条。 */
    public List<FeatureImportance> selectTop(int limit) {
        return jdbcTemplate.query("SELECT id, feature_key, feature_cn, importance, rank_no "
                + "FROM dws_feature_importance ORDER BY rank_no ASC LIMIT ?", ROW_MAPPER, limit);
    }
}
