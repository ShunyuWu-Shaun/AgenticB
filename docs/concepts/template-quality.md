# 模板正确性与发布前评分阈值检查

## 正确模板定义
正确模板需要同时满足五层条件：
1. 结构正确：schema 完整，类型合法。
2. 语义正确：所有字段引用都能在字典中解析。
3. 可解性：回归样本下求解成功率达标。
4. 安全覆盖：关键目标和可控字段有安全规则覆盖。
5. 回归表现：匹配率和违规率达到门限。

## 默认门限
- `structural_score >= 0.98`
- `semantic_score >= 0.98`
- `solvability_score >= 0.95`
- `guardrail_coverage >= 0.95`
- `regression_score >= 0.90`
- `overall_score >= 0.95`

## 调用方式
`POST /v1/templates/quality-check`

输入：
1. `draft` 或 `template`
2. 可选 `gate`
3. 可选 `regression_samples`

输出：
- `TemplateQualityReport`
- `passed`
- `issues`

## 失败排查顺序
1. 先看 `STRUCTURAL_*` 和 `SEMANTIC_*`。
2. 再看 `SOLVABILITY_*` 和 `GUARDRAIL_*`。
3. 最后看 `REGRESSION_*` 和 `OVERALL_*`。
