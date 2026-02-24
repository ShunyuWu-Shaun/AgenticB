# 模板正确性与质量门禁

## 为什么需要质量门禁
能运行不等于可发布。

质量门禁用于回答：
- 模板是否结构完整。
- 字段语义是否一致。
- 优化是否可解。
- 安全规则是否覆盖关键变量。
- 回归样本下是否稳定。

## 五层评估维度
1. `structural_score`
   - schema 合法性、字段完整性。
2. `semantic_score`
   - 目标/约束/特征/安全规则字段能否在字典中解析。
3. `solvability_score`
   - 回归样本中求解器返回 `solved` 的比例。
4. `guardrail_coverage`
   - 目标字段 + 可控字段被安全规则覆盖的比例。
5. `regression_score`
   - 回归样本上的期望匹配率与违规率综合分。

## 默认阈值
- `structural >= 0.98`
- `semantic >= 0.98`
- `solvability >= 0.95`
- `guardrail >= 0.95`
- `regression >= 0.90`
- `overall >= 0.95`

## 如何调用
- `POST /v1/templates/quality-check`
- 或直接 `POST /v1/templates/publish`（默认内置质量门禁）

## 结果如何解读
`passed=false` 时，优先看 `issues`：
- `STRUCTURAL_LOW`：先修模板结构。
- `SEMANTIC_LOW`：修字段映射。
- `SOLVABILITY_LOW`：修约束冲突或求解参数。
- `GUARDRAIL_LOW`：补安全规则。
- `REGRESSION_LOW`：补样本或调整目标权重。

## 实战建议
- 发布前至少提供一组真实分布回归样本。
- 不要只用合成样本决定最终发布。
- 把质量结果和模板版本一同归档。
