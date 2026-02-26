# Python SDK 扩展点

## 1. 自定义 LLM 客户端
默认是 `RoleBasedLLMClient`，走 OpenAI 兼容协议。
你可以实现 `LLMClientProtocol` 接入自有网关。

关键方法：
```python
complete_json(role, system_prompt, user_payload, temperature)
```

## 2. 自定义 Agent
### Parser Agent
- 输入：legacy 点位 + 标准字段字典
- 输出：`ParserResult`

### Generator Agent
- 输入：场景信息 + 字段字典 + 业务诉求
- 输出：`MigrationDraft`

### Critic Agent
- 输入：失败草案 + 校验与评分报告
- 输出：`CriticFeedback`

## 3. 自定义工作流
`LangGraphMigrationWorkflow` 支持替换内部 Agent 和门禁器。

```python
workflow = LangGraphMigrationWorkflow(
    parser_agent=my_parser,
    generator_agent=my_generator,
    critic_agent=my_critic,
    validator=my_validator,
    quality_evaluator=my_quality,
)
```

## 4. 自定义预测与优化引擎
实现以下协议可替换执行层：
- `PredictorProtocol`
- `OptimizerProtocol`
- `GuardrailProtocol`

并注入：
```python
pipeline = PredictionOptimizationPipeline(
    predictor=my_predictor,
    optimizer=my_optimizer,
    guardrail=my_guardrail,
)
```

## 5. 接入现有模型建议
1. 先把现有模型封装成 `PredictorProtocol`。
2. 保持输入输出字段名与 `FieldDictionary` 对齐。
3. 先跑 `/v1/pipeline/simulate`，再跑 `/v1/pipeline/evaluate`。
4. 最后接入 `/v1/agentic/run` 做自动草案与门禁串联。
