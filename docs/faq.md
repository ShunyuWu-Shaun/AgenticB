# FAQ

## Q1: 这个库和普通优化框架有什么区别
它提供完整迁移链路：点位语义映射、草案生成、发布前评分阈值检查、失败后自动修正流程。

## Q2: 没有 LLM 还能用吗
可以。系统会降级到规则路径，仍可输出可校验草案。

## Q3: 为什么不直接下发控制指令
v0.3 定位是配置迁移和仿真评估。自动闭环控制不在当前版本范围内。

## Q4: 如何接入现有模型
实现 `PredictorProtocol` 并注入 `PredictionOptimizationPipeline`。详见 [Python SDK 扩展点](reference/python-sdk.md)。

## Q5: 如何定位发布失败原因
优先看：
1. `MigrationValidationReport.issues`
2. `TemplateQualityReport.issues`
3. `AgenticRunReport.reflections`

## Q6: 可以接哪些模型服务
支持 OpenAI 兼容协议。已适配 Kimi、Qwen、DeepSeek、OpenAI 的配置方式。
