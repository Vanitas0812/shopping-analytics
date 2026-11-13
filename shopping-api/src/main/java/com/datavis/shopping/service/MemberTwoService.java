package com.datavis.shopping.service;

import com.datavis.shopping.common.Calc;
import com.datavis.shopping.dto.ConfusionMatrixDTO;
import com.datavis.shopping.dto.FeatureImportanceDTO;
import com.datavis.shopping.dto.ModelMetricDTO;
import com.datavis.shopping.entity.FeatureImportance;
import com.datavis.shopping.entity.ModelResult;
import com.datavis.shopping.mapper.FeatureImportanceMapper;
import com.datavis.shopping.mapper.ModelResultMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 成员二：转化预测与精细化运营大屏业务层（模型评估 / 特征重要性）。
 * 数据来自 dws_model_result 与 dws_feature_importance，均为建模脚本真实产出。
 */
@Service
public class MemberTwoService {

    /** 模型固定展示顺序。 */
    private static final List<String> MODEL_ORDER = List.of("LogisticRegression", "RandomForest");

    /** 默认模型（AUC 最优）。 */
    public static final String DEFAULT_MODEL = "RandomForest";

    /** 特征重要性展示条数。 */
    private static final int FEATURE_TOP_N = 12;

    private final ModelResultMapper modelResultMapper;
    private final FeatureImportanceMapper featureImportanceMapper;

    public MemberTwoService(ModelResultMapper modelResultMapper,
                            FeatureImportanceMapper featureImportanceMapper) {
        this.modelResultMapper = modelResultMapper;
        this.featureImportanceMapper = featureImportanceMapper;
    }

    /** 模型指标对比：两模型各 5 项指标。 */
    @Transactional(readOnly = true)
    public List<ModelMetricDTO> getModelMetrics() {
        List<ModelResult> all = modelResultMapper.selectAll();
        Map<String, Map<String, Double>> grouped = new LinkedHashMap<>();
        for (String model : MODEL_ORDER) {
            grouped.put(model, new HashMap<>());
        }
        for (ModelResult row : all) {
            grouped.computeIfAbsent(row.getModelName(), k -> new HashMap<>())
                    .put(row.getMetricName(), Calc.dbl(row.getMetricValue()));
        }
        List<ModelMetricDTO> result = new ArrayList<>(grouped.size());
        for (Map.Entry<String, Map<String, Double>> entry : grouped.entrySet()) {
            Map<String, Double> m = entry.getValue();
            result.add(new ModelMetricDTO(
                    entry.getKey(),
                    metric(m, "accuracy"),
                    metric(m, "auc"),
                    metric(m, "precision"),
                    metric(m, "recall"),
                    metric(m, "f1")));
        }
        return result;
    }

    private double metric(Map<String, Double> map, String name) {
        return Calc.round4(map.getOrDefault(name, 0D));
    }

    /** 混淆矩阵，model 参数缺省为 RandomForest。 */
    @Transactional(readOnly = true)
    public ConfusionMatrixDTO getConfusion(String model) {
        String target = (model == null || model.isBlank()) ? DEFAULT_MODEL : model.trim();
        List<ModelResult> rows = modelResultMapper.selectByModel(target);
        if (rows.isEmpty()) {
            return null;
        }
        Map<String, Double> m = new HashMap<>();
        for (ModelResult row : rows) {
            m.put(row.getMetricName(), Calc.dbl(row.getMetricValue()));
        }
        return new ConfusionMatrixDTO(
                target,
                Math.round(m.getOrDefault("tp", 0D)),
                Math.round(m.getOrDefault("fp", 0D)),
                Math.round(m.getOrDefault("tn", 0D)),
                Math.round(m.getOrDefault("fn", 0D)));
    }

    /** 特征重要性 Top12。 */
    @Transactional(readOnly = true)
    public List<FeatureImportanceDTO> getFeatureImportance() {
        List<FeatureImportance> rows = featureImportanceMapper.selectTop(FEATURE_TOP_N);
        List<FeatureImportanceDTO> result = new ArrayList<>(rows.size());
        for (FeatureImportance row : rows) {
            result.add(new FeatureImportanceDTO(row.getFeatureKey(), row.getFeatureCn(),
                    Calc.round4(row.getImportance()), row.getRankNo()));
        }
        return result;
    }
}
