# FAQ

## Q1: 这个库和普通优化框架有什么区别？
它强调迁移治理，不仅是求解，还包括点位标准化、草案生成、质量门禁和可发布流程。

## Q2: 没有 LLM 还能用吗？
可以。迁移助手默认规则优先，LLM 是可选增强。

## Q3: 为什么不直接下发控制指令？
v0.2 定位是迁移基础设施与仿真评估，不承担自动闭环控制职责。

## Q4: 如何接入现有模型？
实现 `PredictorProtocol` 并注入 `PredictionOptimizationPipeline`。

## Q5: Legacy YAML 还要长期保留吗？
不建议。建议迁移后固化为 standard YAML。
