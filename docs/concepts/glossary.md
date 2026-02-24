# 术语表（去抽象化）

本页把常见抽象词换成可操作描述。

## 核心术语
- **迁移草案（MigrationDraft）**
  - 含义：待发布模板的提案对象。
  - 你需要做什么：人工确认 `pending_confirmations` 后再发布。

- **模板（ScenarioTemplate）**
  - 含义：预测-优化策略的标准结构。
  - 你需要做什么：维护版本，不要散落在脚本。

- **安全规则（Guardrail）**
  - 含义：执行前检查规则，约束建议值范围和变化量。
  - 你需要做什么：确保覆盖目标字段和可控字段。

- **安全规则判定结果（GuardrailDecision）**
  - 含义：对优化建议的判定结果。
  - 结果类型：
    - 通过（approved=true）
    - 拦截（approved=false）
    - 裁剪（approved=true 但值被clip）

- **质量门禁（TemplateQualityGate）**
  - 含义：发布前的评分阈值配置。
  - 你需要做什么：按场景调阈值，保留变更记录。

- **上下文构建（Context Build）**
  - 含义：按 catalog 从 Redis/MySQL 拉点位值，组装 `SceneContext`。
  - 你需要做什么：处理缺失策略（error/drop/zero）。

## 不建议使用的模糊表达
- **安全规则判定结果**：指优化建议经过安全规则检查后的结果，可为通过、拦截或裁剪。
- 上线前看看 建议改为 **执行 validate + quality-check 并保存报告**。
- 模型建议不稳定 建议改为 **回归分数低、违规率高、可解率低**。
