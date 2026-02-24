# 迁移草案定义

## 定义
`MigrationDraft` 是“迁移建议”的标准结构。

它包含两部分：
- **模板本体**：`ScenarioTemplate`
- **迁移元信息**：置信度、风险、待确认项、生成策略

## 字段级说明
### `template`
- `template_id/version`: 模板标识与版本。
- `scene_metadata`: 场景标识、时间粒度、执行窗口。
- `field_dictionary`: 字段语义字典。
- `objective`: 目标函数定义（最小化/最大化 + 权重）。
- `constraints`: 硬约束/软约束（上下界/等式）。
- `prediction`: 预测特征与时域。
- `optimization`: 求解器预算与收敛参数。
- `guardrail`: 安全规则（最小/最大/最大变化量）。

### `confidence`
迁移助手对草案可靠性的估计值（0~1）。

### `pending_confirmations`
必须人工确认的信息，比如：
- 权重是否符合业务优先级。
- 约束强弱（hard/soft）是否正确。

### `risks`
风险清单，如：
- 约束覆盖不足。
- 安全规则覆盖不足。

### `generation_strategy`
草案生成方式，例如：
- `rule_only`
- `hybrid_llm_rule`
- `rule_only_low_confidence`

## 最小可发布草案检查清单
- `template.objective.terms` 非空。
- `prediction.feature_fields` 均在 `field_dictionary` 中。
- `constraints` 无冲突。
- 安全规则覆盖目标字段和可控字段。
- `validate` 与 `quality-check` 均通过。

## 实践建议
- 把业务关键字段先标成 `controllable=true`，再补安全规则。
- `pending_confirmations` 要作为发布前工单项关闭。
- 每次发布必须保存草案快照以支持回溯。
