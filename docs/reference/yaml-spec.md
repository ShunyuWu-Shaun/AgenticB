# YAML 规范

## 1. Standard 模式
适用于新项目或已标准化项目。

```yaml
scene:
  scene_id: demo-line
  scenario_type: optimization

datasources:
  redis_main:
    kind: redis
    conn_ref: env:REFLEXFLOW_REDIS_CONN
  mysql_main:
    kind: mysql
    conn_ref: env:REFLEXFLOW_MYSQL_CONN

point_catalog:
  catalog_id: demo-line-catalog
  source_profile: redis_main
  bindings:
    - point_id: P_TEMP_01
      source_type: redis
      source_ref: plant:temp:01
      field_name: reactor_temp
      unit: C

field_dictionary:
  fields:
    - field_name: reactor_temp
      semantic_label: temperature
      unit: C
      observable: true
      controllable: true
      missing_strategy: required
```

## 2. Legacy 模式
适用于真实工业遗留结构。

### 2.1 顶层点位键
```yaml
AB10PT101: AB10PT101
AB10FT201: AB10FT201
```

### 2.2 分组大字典
`mechanism_v1.yml` 这类结构可以直接导入：

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
1. 从分组里提取点位。
2. 生成唯一 `point_id`。
3. 保留原始 `source_ref`，即使存在重复 tag。
4. 自动推断 `field_dictionary`。

## 3. 大规模点位建议
当点位规模到 1k 到 5k：
1. 优先使用 `legacy` 模式直接导入分组 YAML。
2. 不要手写 `bindings`。
3. 先导入后检查 `pending_confirmations` 和 `warnings`。
4. 再按业务补齐 `semantic_label` 和 `controllable`。

## 4. 字段建议
1. `field_name` 使用稳定可读命名。
2. `semantic_label` 优先使用标准词，如 cost、temperature、pressure。
3. `controllable=true` 的字段必须配置安全规则。
