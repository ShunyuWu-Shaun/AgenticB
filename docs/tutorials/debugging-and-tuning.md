# 调参与故障排查

## 1. 发布被质量门禁阻断
看 `TemplateQualityReport.issues`：
- `SEMANTIC_LOW`: 字段名不匹配。
- `SOLVABILITY_LOW`: 约束冲突或求解预算不足。
- `GUARDRAIL_LOW`: 安全规则覆盖不足。

## 2. 上下文构建失败
- 现象：`missing fields in snapshot`
- 排查顺序：
  1. `catalog.bindings` 的 `source_ref` 是否正确。
  2. `conn_ref` 是否可解析（env/file）。
  3. 数据源是否连通。

## 3. 仿真结果持续被拦截
- 检查 `guardrail.violations`。
- 检查 `max_delta` 是否过小。
- 检查优化建议是否被约束推到边界。

## 4. 1k-5k 点位性能问题
- 提高 `DataSourceOptions.batch_size`（在可承受范围内）。
- 优化 MySQL 索引列（point_id 列必须建索引）。
- 对低频字段进行按需拉取（`fields` 参数）。

## 5. 低置信度草案
- 扩充 `field_dictionary` 语义标签。
- 提供明确的 `nl_requirements`。
- 必要时人工直接编辑 `ScenarioTemplate` 后再校验。
