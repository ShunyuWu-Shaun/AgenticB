# YAML 规范

## Standard 模式

```yaml
scene:
  scene_id: demo-line
  scenario_type: optimization

datasources:
  redis_main:
    kind: redis
    conn_ref: env:EASYSHIFT_REDIS_CONN
  mysql_main:
    kind: mysql
    conn_ref: env:EASYSHIFT_MYSQL_CONN

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

template_override:
  notes: custom override
```

## Legacy 模式

```yaml
redis_config:
  host: 127.0.0.1
  port: 6379

AB10PT101: AB10PT101
AB10FT201: AB10FT201
```

系统会自动：
- 识别点位键。
- 生成 `PointBinding`。
- 提供 `pending_confirmations`。

## 字段建议
- `field_name` 使用稳定且可读的业务字段。
- `semantic_label` 尽量标准化（cost/temperature/pressure 等）。
- `controllable=true` 的字段必须配置安全规则。
