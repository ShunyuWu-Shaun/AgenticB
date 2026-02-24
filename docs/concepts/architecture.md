# 架构与运行逻辑

## 四层结构
1. Core 层
   - 定义统一契约。
   - 执行预测、优化、安全规则判定。
2. Ingestion 层
   - 解析 YAML。
   - 管理点位 catalog。
   - 从 Redis/MySQL 读取快照。
3. Agentic + Quality 层
   - 生成迁移草案。
   - 校验草案正确性。
   - 评估模板质量。
4. Service 层
   - 对外 HTTP API。
   - 管理模板发布与查询。

## 核心数据流
1. `catalog import`
   - 输入 YAML。
   - 输出 `PointCatalog + FieldDictionary`。
2. `context build`
   - 输入 `catalog_id`。
   - 输出 `SceneContext`。
3. `template generate`
   - 输入场景元信息与字段字典。
   - 输出 `MigrationDraft`。
4. `validate + quality-check`
   - 输出是否可发布。
5. `simulate/evaluate`
   - 输出预测结果、优化建议、安全规则判定与最终建议值。

## 执行链说明
`PredictionOptimizationPipeline` 的顺序固定：
1. `Predictor.predict(...)`
2. `Optimizer.solve(...)`
3. `Guardrail.validate(...)`

输出 `PipelineResult`。

## 为什么要有安全规则判定层
优化器给出的建议可能数学上可解，但业务上不可执行。  
安全规则判定层负责：
- 拦截越界建议。
- 裁剪过大变化幅度。
- 提供回退值。

它是执行前的最后一道保护。
