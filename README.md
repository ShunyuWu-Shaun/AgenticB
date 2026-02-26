<p align="center">
  <img src="assets/branding/logo.png" alt="EasyShift-MaaS logo" width="180" />
</p>

<h1 align="center">EasyShift-MaaS</h1>
<p align="center"><strong>LLM 驱动多 Agent 迁移流水线，用于工业预测-优化配置自动化</strong></p>

<p align="center">
  Kimi / Qwen / DeepSeek / OpenAI | YAML Catalog | Redis/MySQL | Deterministic Quality Gate
</p>

<p align="center">
  <img src="assets/branding/framework.png" alt="EasyShift-MaaS framework" width="900" />
</p>

## 1. 这个库解决什么问题
工业现场常见问题有三类：
1. 遗留点位命名混乱，字段语义很难统一。
2. 迁移配置依赖人工经验，目标、约束和安全边界容易漏配。
3. 直接让 LLM 生成配置有幻觉风险，缺少硬性校验会把错误配置带到发布阶段。

EasyShift-MaaS v0.3 的做法是：
1. LLM 负责语义理解与结构化草案生成。
2. 确定性代码负责校验、评分和阻断。
3. 失败时走自动修正流程，直到通过或达到迭代上限。

## 2. 核心运行逻辑
主链路是 Parser -> Generator -> Deterministic Gate -> Critic -> 自动修正流程。

- Parser Agent：把 legacy 点位映射到标准字段字典。
- Generator Agent：把自然语言需求转成 `MigrationDraft`。
- Deterministic Gate：执行 `validate + quality-check`。
- Critic Agent：读取失败日志并给出明确修正指令。
- Workflow：按最大迭代次数反复修正。

## 3. 你要提供的输入
最小输入：
1. `scene_metadata`
2. `field_dictionary`
3. `nl_requirements`

可选输入：
1. `legacy_points` 或 `raw_yaml_text`
2. `TemplateQualityGate`
3. `regression_samples`

## 4. 你会得到的输出
1. `ParserResult`：点位映射、未映射点、映射置信度。
2. `MigrationDraft`：目标、约束、安全规则、预测特征、风险说明。
3. `MigrationValidationReport`：字段合法性、约束冲突率、安全规则覆盖率。
4. `TemplateQualityReport`：结构、语义、可解性、安全覆盖、回归评分。
5. `AgenticRunReport`：每轮失败原因、修正指令、最终状态。

## 5. 迁移草案结构说明
迁移草案是发布前的结构化配置对象。它至少包含以下模块：
1. `objective`：优化目标及权重。
2. `constraints`：运行边界和可行域。
3. `guardrail`：安全规则，覆盖关键目标字段。
4. `prediction`：预测使用的特征和时域。
5. `trace`：自动修正流程记录。
6. `source_mappings`：legacy 点位到标准字段的来源映射。

示例：

```json
{
  "draft_id": "draft-6e7f...",
  "template": {
    "template_id": "line-a-template",
    "version": "draft-1",
    "scene_metadata": {
      "scene_id": "line-a",
      "scenario_type": "optimization",
      "tags": ["synthetic"],
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
        },
        {
          "field_name": "boiler_temp",
          "semantic_label": "temperature",
          "unit": "C",
          "dimension": "dimensionless",
          "observable": true,
          "controllable": true,
          "missing_strategy": "required"
        }
      ],
      "alias_map": {}
    },
    "objective": {
      "terms": [
        {"field_name": "energy_cost", "direction": "min", "weight": 0.6},
        {"field_name": "boiler_temp", "direction": "max", "weight": 0.4}
      ],
      "normalize_weights": false
    },
    "constraints": [
      {
        "name": "boiler_temp_ge_0",
        "field_name": "boiler_temp",
        "operator": "ge",
        "lower_bound": 180.0,
        "priority": 20,
        "severity": "hard"
      }
    ],
    "prediction": {
      "feature_fields": ["energy_cost", "boiler_temp"],
      "horizon_steps": 3,
      "model_signature": "llm-draft:v1"
    },
    "optimization": {
      "solver_name": "projected-heuristic",
      "max_iterations": 80,
      "tolerance": 0.000001,
      "time_budget_ms": 400
    },
    "guardrail": {
      "rules": [
        {"field_name": "boiler_temp", "min_value": 150.0, "max_value": 900.0, "max_delta": 40.0, "action": "clip"},
        {"field_name": "energy_cost", "max_delta": 0.2, "action": "clip"}
      ],
      "fallback_policy": "keep_previous"
    }
  },
  "confidence": 0.84,
  "pending_confirmations": ["Review whether correction instruction has been fully applied"],
  "risks": [],
  "generation_strategy": "llm_primary",
  "trace": [],
  "source_mappings": [
    {"legacy_name": "B_T_01", "standard_name": "boiler_temp", "confidence": 0.93, "reasoning": "abbreviation mapping"}
  ],
  "llm_metadata": {
    "role": "generator",
    "vendor": "qwen",
    "model": "qwen-plus"
  }
}
```

发布前硬条件：
1. `validate` 通过。
2. `quality-check` 达到阈值。
3. 失败时必须经过自动修正流程或人工修订。

## 6. 快速使用
### 6.1 安装与启动
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,docs]'
uvicorn easyshift_maas.api.app:app --reload --port 8000
```

### 6.2 配置 LLM
```bash
export EASYSHIFT_LLM_VENDOR=qwen
export EASYSHIFT_LLM_API_KEY=your_api_key
export EASYSHIFT_LLM_MODEL_PARSER=qwen-plus
export EASYSHIFT_LLM_MODEL_GENERATOR=qwen-plus
export EASYSHIFT_LLM_MODEL_CRITIC=qwen-plus
export EASYSHIFT_LLM_TIMEOUT_SEC=30
```

支持：`kimi`、`qwen`、`deepseek`、`openai`。也可直接设置 `EASYSHIFT_LLM_BASE_URL` 走自定义 OpenAI 兼容网关。

### 6.3 一次完整调用
1. 解析点位
```bash
curl -X POST http://127.0.0.1:8000/v1/agentic/parse-points \
  -H 'content-type: application/json' \
  -d '{
    "field_dictionary": {"fields": [{"field_name":"energy_cost","semantic_label":"cost","unit":"$/h"}], "alias_map": {}},
    "legacy_points": ["E_COST_01", "B_T_01"]
  }'
```

2. 运行完整链路
```bash
curl -X POST http://127.0.0.1:8000/v1/agentic/run \
  -H 'content-type: application/json' \
  -d '{
    "scene_metadata": {"scene_id": "line-a", "scenario_type": "optimization", "tags": ["synthetic"], "granularity_sec": 60, "execution_window_sec": 300},
    "field_dictionary": {"fields": [{"field_name":"energy_cost","semantic_label":"cost","unit":"$/h"}], "alias_map": {}},
    "nl_requirements": ["minimize energy cost while keeping safe operation"],
    "legacy_points": ["E_COST_01", "B_T_01"],
    "max_iterations": 3
  }'
```

3. 发布通过门禁的草案
```bash
curl -X POST http://127.0.0.1:8000/v1/templates/publish \
  -H 'content-type: application/json' \
  -d '{"draft": {...}, "validate_before_publish": true, "enforce_quality_gate": true}'
```

## 7. API 总览
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
- Pipeline
  - `POST /v1/pipeline/simulate`
  - `POST /v1/pipeline/evaluate`
- Data
  - `POST /v1/catalogs/import`
  - `GET /v1/catalogs/{catalog_id}`
  - `POST /v1/contexts/build`
- Health
  - `GET /health`

## 8. 常见问题与调整
1. 点位映射置信度低
   - 补充 `field_dictionary.alias_map`
   - 提供更多 legacy 点位样例
2. 质量评分不达标
   - 先看 `quality_report.issues`
   - 调整约束冲突和安全规则覆盖
3. 反复阻断无法发布
   - 查看 `AgenticRunReport.reflections`
   - 按每轮 `correction_instruction` 修改输入或字段字典
4. LLM 不可用
   - 系统会自动降级到规则路径
   - 检查 `EASYSHIFT_LLM_*` 环境变量

## 9. 部署
### Docker Compose
```bash
docker compose up --build
```

### Nuitka
```bash
pip install '.[build]'
./scripts/build_nuitka.sh
```

## 10. 文档站
- 在线文档: [https://shunyuwu-shaun.github.io/EasyShift-MaaS/](https://shunyuwu-shaun.github.io/EasyShift-MaaS/)
- 本地预览:
```bash
mkdocs serve
```

## 11. 非泄漏声明
- 本仓库只包含 synthetic 示例。
- 未包含任何商用 demo 资产。
- CI 包含敏感扫描：`tools/sensitive_scan.py`

## 12. License
Apache-2.0
