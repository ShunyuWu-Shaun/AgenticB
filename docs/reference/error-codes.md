# 错误码与处理建议

## 校验类
- `OBJ_EMPTY`: 目标项为空。
- `OBJ_FIELD_UNKNOWN`: 目标字段不在字典中。
- `PRED_FEATURE_UNKNOWN`: 预测特征不在字典中。
- `CONSTRAINT_FIELD_UNKNOWN`: 约束字段不在字典中。
- `CONSTRAINT_CONFLICT_*`: 约束冲突。

建议：先修 `field_dictionary` 与 `constraints`。

## 质量门禁类
- `STRUCTURAL_LOW`
- `SEMANTIC_LOW`
- `SOLVABILITY_LOW`
- `GUARDRAIL_LOW`
- `REGRESSION_LOW`
- `OVERALL_LOW`

建议：按 `issues` 顺序逐项修复，别只调 `overall_min`。

## 数据源类
- `missing fields in snapshot`
- `redis_error:*`
- `mysql_error:*`

建议：检查 `conn_ref`、source_ref、数据源连通性。

## API 层
- `400`: 业务失败。
- `404`: 资源不存在。
- `422`: 请求格式错误。
