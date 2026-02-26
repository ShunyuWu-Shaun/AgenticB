# 第一份迁移草案

本页解释迁移草案最小结构、正确性要求和发布条件。

## 1. 最小结构
一份可运行草案至少要有：
1. `scene_metadata`
2. `field_dictionary`
3. `objective`
4. `constraints`
5. `prediction`
6. `optimization`
7. `guardrail`

## 2. 推荐生成方式
通过接口生成：
- `POST /v1/agentic/generate-draft`
- 或 `POST /v1/agentic/run`

## 3. 校验顺序
1. `POST /v1/templates/validate`
2. `POST /v1/templates/quality-check`
3. `POST /v1/templates/publish`

## 4. 常见不通过原因
1. objective 使用了不存在字段。
2. 同一字段上界和下界冲突。
3. 安全规则未覆盖关键目标字段。
4. 回归得分低于门限。

## 5. 建议动作
1. 查看 `MigrationValidationReport.issues`。
2. 查看 `TemplateQualityReport.issues`。
3. 按 `AgenticRunReport.reflections` 中修正指令改配置后重试。
