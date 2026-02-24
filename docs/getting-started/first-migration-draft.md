# 第一份迁移草案

本页回答三个高频问题：
1. 迁移草案是什么？
2. 草案里必须包含什么？
3. 怎么判断这份草案是否可发布？

## 1. 什么是迁移草案（MigrationDraft）
`MigrationDraft` 是待发布模板的中间对象。

它不是控制指令。它是可审查、可回归、可追踪版本的迁移提案。

## 2. 草案结构
最关键字段：
- `draft_id`: 草案唯一标识。
- `template`: 完整 `ScenarioTemplate`。
- `confidence`: 草案置信度（0-1）。
- `pending_confirmations`: 需要人工确认的事项。
- `risks`: 风险项列表。
- `generation_strategy`: 生成策略（规则优先、混合、降级等）。

## 3. template 必须包含什么
一个可发布 template 至少要明确：
- 场景定义：`scene_metadata`
- 字段字典：`field_dictionary`
- 目标函数：`objective`
- 约束集合：`constraints`
- 预测配置：`prediction`
- 优化配置：`optimization`
- 安全规则：`guardrail`

简化示例：
```json
{
  "draft_id": "draft-123",
  "template": {
    "template_id": "demo-line-template",
    "version": "draft-1",
    "scene_metadata": {"scene_id": "demo-line", "scenario_type": "optimization", "tags": [], "granularity_sec": 60, "execution_window_sec": 300},
    "field_dictionary": {"fields": [{"field_name": "energy_cost", "semantic_label": "cost", "unit": "$/h", "dimension": "dimensionless", "observable": true, "controllable": false, "missing_strategy": "required"}], "alias_map": {}},
    "objective": {"terms": [{"field_name": "energy_cost", "direction": "min", "weight": 1.0}], "normalize_weights": false},
    "constraints": [],
    "prediction": {"feature_fields": ["energy_cost"], "horizon_steps": 3, "model_signature": "rule-bootstrap:v1"},
    "optimization": {"solver_name": "projected-heuristic", "max_iterations": 60, "tolerance": 1e-6, "time_budget_ms": 300},
    "guardrail": {"rules": [{"field_name": "energy_cost", "max_delta": 0.2, "action": "clip"}], "fallback_policy": "keep_previous"}
  },
  "confidence": 0.84,
  "pending_confirmations": ["Confirm objective term weights"],
  "risks": [],
  "generation_strategy": "rule_only"
}
```

## 4. 怎样才算可发布草案
发布前默认有两关：
1. **草案校验**（`/v1/templates/validate`）
2. **质量门禁**（`/v1/templates/quality-check`，或 publish 内置）

建议最低要求：
- 校验 `valid = true`
- 质量 `passed = true`
- `pending_confirmations` 处理完成

## 5. 常见误区
- 误区：只有 objective 就能发布。  
  正解：还必须有约束和安全规则，否则风险不可控。
- 误区：草案生成后不用人工看。  
  正解：低置信度和 `pending_confirmations` 必须人工确认。
