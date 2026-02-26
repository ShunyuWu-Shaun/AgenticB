# v0.2 -> v0.3 迁移说明

## 1. 变化概览
v0.3 是破坏性升级，核心变化是引入多 Agent 自动修正流程。

主要变更：
1. 旧的 `POST /v1/templates/generate` 已移除。
2. 新增 `/v1/agentic/*` 系列接口。
3. `MigrationDraft` 增加 `trace`、`source_mappings`、`llm_metadata` 字段。
4. API 默认版本升级到 `0.3.0`。

## 2. 路由对照
| v0.2 | v0.3 |
|---|---|
| `POST /v1/templates/generate` | `POST /v1/agentic/generate-draft` |
| 无 | `POST /v1/agentic/parse-points` |
| 无 | `POST /v1/agentic/review-draft` |
| 无 | `POST /v1/agentic/run` |

保留路由：
- `/v1/templates/validate`
- `/v1/templates/quality-check`
- `/v1/templates/publish`
- `/v1/pipeline/simulate`
- `/v1/pipeline/evaluate`
- `/v1/catalogs/import`
- `/v1/contexts/build`

## 3. 代码迁移建议
1. 若你之前只调用 `templates/generate`，请改为：
   - `agentic/parse-points` -> `agentic/generate-draft` -> `templates/validate` -> `templates/quality-check` -> `templates/publish`
2. 若你需要自动修正，直接调用 `agentic/run`。
3. 若你有自己的模型，优先封装成 `PredictorProtocol` 并接入 pipeline。

## 4. 环境变量
新增或推荐：
- `REFLEXFLOW_LLM_VENDOR`
- `REFLEXFLOW_LLM_BASE_URL`
- `REFLEXFLOW_LLM_API_KEY`
- `REFLEXFLOW_LLM_MODEL_PARSER`
- `REFLEXFLOW_LLM_MODEL_GENERATOR`
- `REFLEXFLOW_LLM_MODEL_CRITIC`
- `REFLEXFLOW_LLM_TIMEOUT_SEC`

兼容说明：
- 代码仍兼容读取旧前缀 `EASYSHIFT_LLM_*`，建议新部署统一切换到 `REFLEXFLOW_LLM_*`。

## 5. 回滚策略
如需短期回滚到 v0.2：
1. 回退到 `0.2.x` tag。
2. 恢复旧接口调用路径。
3. 清理 v0.3 新字段依赖。
