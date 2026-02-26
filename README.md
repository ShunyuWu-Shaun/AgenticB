<p align="center">
  <img src="assets/branding/logo.png" alt="ReflexFlow-MaaS logo" width="180" />
</p>

<h1 align="center">ReflexFlow-MaaS</h1>
<p align="center"><strong>LLM 多 Agent 迁移流水线，用于工业预测-优化配置自动化</strong></p>

<p align="center">
  Kimi / Qwen / DeepSeek / OpenAI | YAML Catalog | Redis/MySQL | Deterministic Gate
</p>

<p align="center">
  <img src="assets/branding/framework.png" alt="ReflexFlow-MaaS framework" width="900" />
</p>

## 1. 这个库解决什么问题
工业场景里，迁移常见卡点有三类：
1. 点位命名混乱，字段语义不统一。
2. 目标、约束、安全规则散在脚本里，复用和审计困难。
3. LLM 直接产出配置会有幻觉风险，缺少发布前硬校验。

ReflexFlow-MaaS 的设计是明确分工：
1. LLM 负责理解和翻译。
2. 确定性代码负责校验和阻断。
3. 失败后自动给出修正指令并进入下一轮。

## 2. 核心流程
主链路：Parser Agent -> Generator Agent -> Deterministic Gate -> Critic Agent -> 自动修正流程

- Parser Agent
  - 输入：legacy 点位列表或原始 YAML
  - 输出：`ParserResult`
- Generator Agent
  - 输入：`SceneMetadata + FieldDictionary + nl_requirements`
  - 输出：`MigrationDraft`
- Deterministic Gate
  - 执行：`validate + quality-check`
  - 结果：通过或阻断
- Critic Agent
  - 输入：失败草案和错误列表
  - 输出：可执行修正指令

## 3. 输入类型与具体格式
### 3.1 Agentic 最小输入
`POST /v1/agentic/run` 最小请求体：

```json
{
  "scene_metadata": {
    "scene_id": "line_a",
    "scenario_type": "optimization",
    "tags": ["boiler"],
    "granularity_sec": 60,
    "execution_window_sec": 300
  },
  "field_dictionary": {
    "fields": [
      {
        "field_name": "energy_cost",
        "semantic_label": "cost",
        "unit": "$/h",
        "dimension": "dimensionless",
        "observable": true,
        "controllable": false,
        "missing_strategy": "required"
      }
    ],
    "alias_map": {}
  },
  "nl_requirements": [
    "在满足安全边界前提下最小化能耗"
  ]
}
```

### 3.2 可选输入
1. `legacy_points`
- 直接传入历史点位名列表。
2. `raw_yaml_text`
- 直接传原始 YAML 文本，Parser Agent 会做语义映射。
3. `gate`
- 自定义发布前评分阈值检查。
4. `regression_samples`
- 回归样本，提升质量评估可信度。

### 3.3 Catalog 输入
`POST /v1/catalogs/import` 支持两种模式：
1. `standard`
- 已标准化结构。
2. `legacy`
- 工业遗留结构，支持 `inputs`、`real_time_inputs` 这类分组大字典。

## 4. 自然语言交互如何发挥作用
自然语言入口是 `nl_requirements`，通常由一句或多句业务约束组成。

示例：
1. 最小化总能耗，主汽压力不低于 30MPa。
2. 保持出口温度稳定，单次调整幅度不超过 20。
3. 优先保证安全边界，再优化效率。

Agent 的作用分配：
1. Parser Agent
- 把现场命名映射为标准字段。
2. Generator Agent
- 把自然语言诉求转成 objective/constraints/guardrail。
3. Critic Agent
- 基于失败日志输出下一轮修正指令。

你不需要手写 prompt 链路，调用 `/v1/agentic/run` 即可得到完整运行报告。

## 5. 迁移草案输出长什么样
`MigrationDraft` 是发布前可审计对象，关键字段：
1. `template`
- 目标、约束、安全规则、预测配置。
2. `trace`
- 每轮自动修正记录。
3. `source_mappings`
- legacy 点位映射来源。
4. `llm_metadata`
- 使用的模型和供应商信息。

发布前硬条件：
1. `POST /v1/templates/validate` 通过。
2. `POST /v1/templates/quality-check` 通过。

## 6. 大规模 YAML 问题是否存在，如何解决
你提到的问题是存在的，主要体现在两点：
1. 点位数量 1k 到 5k 时，手写 `point_catalog.bindings` 成本高。
2. 同一个 source tag 被多个业务字段复用时，容易触发唯一性冲突。

当前版本的解决方式：
1. 使用 `mode=legacy` 直接导入分组字典结构，不需要逐点手写。
2. 支持 `inputs` 和 `real_time_inputs` 这类真实工业 YAML 分组。
3. 对重复 tag 采用业务键生成唯一 `point_id`，`source_ref` 保留原始 tag。

这意味着像 `mechanism_v1.yml` 这类文件可以直接导入并自动标准化。

## 7. 快速开始
### 7.1 安装
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,docs]'
```

### 7.2 启动 API
```bash
uvicorn easyshift_maas.api.app:app --reload --port 8000
```

### 7.3 配置 LLM
```bash
export REFLEXFLOW_LLM_VENDOR=qwen
export REFLEXFLOW_LLM_API_KEY=your_api_key
export REFLEXFLOW_LLM_MODEL_PARSER=qwen-plus
export REFLEXFLOW_LLM_MODEL_GENERATOR=qwen-plus
export REFLEXFLOW_LLM_MODEL_CRITIC=qwen-plus
export REFLEXFLOW_LLM_TIMEOUT_SEC=30
```

支持：`kimi`、`qwen`、`deepseek`、`openai`。
可选：`REFLEXFLOW_LLM_BASE_URL` 指向自定义 OpenAI 兼容网关。

### 7.4 导入 legacy YAML
```bash
curl -X POST http://127.0.0.1:8000/v1/catalogs/import \
  -H 'content-type: application/json' \
  -d '{"mode":"legacy","yaml_path":"/Users/shunyu/Downloads/ClosedLoopOptimization/mechanism_v1.yml"}'
```

### 7.5 运行完整 Agentic 链路
```bash
curl -X POST http://127.0.0.1:8000/v1/agentic/run \
  -H 'content-type: application/json' \
  -d '{
    "scene_metadata": {"scene_id":"boiler_line_1","scenario_type":"optimization","tags":["boiler"],"granularity_sec":60,"execution_window_sec":300},
    "field_dictionary": {"fields":[{"field_name":"energy_cost","semantic_label":"cost","unit":"$/h","dimension":"dimensionless","observable":true,"controllable":false,"missing_strategy":"required"}],"alias_map":{}},
    "nl_requirements": ["最小化能耗，同时保持蒸汽参数稳定"],
    "legacy_points": ["AMICS_BALAR1503", "RAA10BQ101"],
    "max_iterations": 3
  }'
```

## 8. API 总览
- Agentic
  - `POST /v1/agentic/parse-points`
  - `POST /v1/agentic/generate-draft`
  - `POST /v1/agentic/review-draft`
  - `POST /v1/agentic/run`
- Template
  - `POST /v1/templates/validate`
  - `POST /v1/templates/quality-check`
  - `POST /v1/templates/publish`
  - `GET /v1/templates/{template_id}`
- Data
  - `POST /v1/catalogs/import`
  - `GET /v1/catalogs/{catalog_id}`
  - `POST /v1/contexts/build`
- Pipeline
  - `POST /v1/pipeline/simulate`
  - `POST /v1/pipeline/evaluate`

## 9. 文档站
- 在线文档: [https://shunyuwu-shaun.github.io/ReflexFlow-MaaS/](https://shunyuwu-shaun.github.io/ReflexFlow-MaaS/)
- 本地预览:
```bash
mkdocs serve
```

## 10. License
Apache-2.0
