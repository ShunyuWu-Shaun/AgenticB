# 迁移草案定义

`MigrationDraft` 是发布前的标准配置载体。它记录了目标、约束、安全规则和来源信息。

## 为什么需要迁移草案
1. 把场景知识从脚本中抽离成可版本化对象。
2. 让 LLM 输出进入可校验结构，支持版本管理和审计。
3. 让失败定位、回归比较和发布审计有统一依据。

## 字段说明
1. `template`
- 真正执行的场景模板，包含 objective/constraints/guardrail/prediction。

2. `confidence`
- 当前草案置信度，范围 0 到 1。

3. `pending_confirmations`
- 需要人工确认的事项。

4. `risks`
- 风险项列表，例如 LLM 降级、字段语义不完整。

5. `generation_strategy`
- 草案生成路径，例如 `llm_primary` 或 `rule_fallback`。

6. `trace`
- 自动修正流程的每轮记录。

7. `source_mappings`
- legacy 点位到标准字段的映射来源。

8. `llm_metadata`
- 使用的模型和供应商元信息。

## 发布前检查
要进入发布，草案必须通过：
1. `POST /v1/templates/validate`
2. `POST /v1/templates/quality-check`

## 常见失败原因
1. objective 字段不存在于 `field_dictionary`。
2. 同一字段约束相互冲突。
3. 关键目标字段缺少安全规则。
4. 回归样本中违规率高，评分低于阈值。
