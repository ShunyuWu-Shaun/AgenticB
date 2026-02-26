# 输入与输出契约

本页给出接口输入类型、字段含义、最小可运行内容和输出结构。

## 1. Agentic 输入
接口：`POST /v1/agentic/run`

### 必填字段
1. `scene_metadata`
- `scene_id: str`
- `scenario_type: str`
- `tags: list[str]`
- `granularity_sec: int`
- `execution_window_sec: int`

2. `field_dictionary`
- `fields: list[FieldDefinition]`
- `alias_map: dict[str, str]`

3. `nl_requirements`
- 类型：`list[str]`
- 内容：业务目标和安全约束的自然语言描述

### 可选字段
1. `legacy_points: list[str]`
2. `raw_yaml_text: str`
3. `max_iterations: int`
4. `gate: TemplateQualityGate`
5. `regression_samples: list[SimulationSample]`

## 2. Catalog 输入
接口：`POST /v1/catalogs/import`

### Standard
- 适用于已经标准化的项目。
- 需要显式 `point_catalog.bindings`。

### Legacy
- 适用于真实工业遗留结构。
- 支持 `inputs`、`real_time_inputs` 这种分组大字典。
- 支持重复 source tag。

示例：

```yaml
inputs:
  coal_net_calorific_value: AMICS_BALAR1503
  coal_received_moisture: AMICS_BALAR1505

real_time_inputs:
  air_preheater_outlet_oxygen_content_A1: RAA10BQ101
  air_preheater_outlet_oxygen_content_A2: RAA10BQ101
  airheater_outlet_temp_A1: RAA10BT301
```

系统会自动：
1. 生成唯一 `point_id`
2. 保留原始 `source_ref`
3. 推断 `field_dictionary`

## 3. 自然语言输入建议
`nl_requirements` 建议用短句，每句一个约束或目标。

示例：
1. 最小化总能耗。
2. 主蒸汽压力不低于 30MPa。
3. 温度单次调整幅度不超过 20。
4. 安全边界优先于经济性目标。

## 4. 核心输出
### `ParserResult`
- `mappings`
- `unmapped_points`
- `confidence`

### `MigrationDraft`
- `template`
- `confidence`
- `trace`
- `source_mappings`
- `llm_metadata`

### `AgenticRunReport`
- `status`
- `reflections`
- `final_draft`
- `blocked_reason`

### `TemplateQualityReport`
- `structural_score`
- `semantic_score`
- `solvability_score`
- `guardrail_coverage`
- `regression_score`
- `passed`

## 5. 常见输入错误
1. `field_dictionary` 空或字段名重复。
2. `nl_requirements` 过于泛化，没有边界条件。
3. legacy YAML 中把配置块误写成点位块。
4. `max_iterations` 太小，无法完成修正流程。
