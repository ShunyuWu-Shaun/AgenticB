# 教程：Legacy YAML 迁移

目标：直接导入真实工业遗留 YAML，并转为可发布模板流程。

## 1. 适用文件形态
以下两类都支持：
1. 顶层点位键。
2. 分组字典，例如 `inputs`、`real_time_inputs`。

`/Users/shunyu/Downloads/ClosedLoopOptimization/mechanism_v1.yml` 属于第二类。

## 2. 为什么不用逐点手写
当点位规模很大时，手写 `point_catalog.bindings` 成本高且容易出错。

当前实现支持：
1. 直接读取分组字典。
2. 自动生成唯一 `point_id`。
3. 原样保留重复 `source_ref`。

## 3. 导入示例
```bash
curl -X POST http://127.0.0.1:8000/v1/catalogs/import \
  -H 'Content-Type: application/json' \
  -d '{"mode":"legacy","yaml_path":"/Users/shunyu/Downloads/ClosedLoopOptimization/mechanism_v1.yml"}'
```

## 4. 导入后检查
重点看两个字段：
1. `warnings`
2. `pending_confirmations`

如果存在待确认项，建议补齐：
1. `semantic_label`
2. `unit`
3. `controllable`

## 5. 进入 Agentic 流程
导入完成后，使用 `/v1/agentic/run` 生成和修正迁移草案。

## 6. 建议
1. Legacy 文件用于快速迁移入口。
2. 迁移完成后建议导出并固化为 standard 版本。
3. 把映射结果和质量报告纳入版本管理。
