<p align="center">
  <img src="assets/logo.svg" alt="EasyShift-MaaS logo" width="220" />
</p>

<h1 align="center">EasyShift-MaaS</h1>
<p align="center"><strong>工业 MAAS 迁移基础库：点位标准化 + 迁移草案 + 质量门禁 + 仿真评测</strong></p>

<p align="center">
  YAML Catalog | Redis/MySQL Indexing | Agentic Draft | Quality Gate | Docker + Nuitka
</p>

## 1. 这个库到底解决什么问题
在工业/B 端场景里，真正困难通常不是“写一个优化器”，而是：
- 现场点位很多（几百到几千），命名混乱，语义不统一。
- 预测/优化/约束/安全边界散落在脚本里，迁移成本高。
- 新场景上线前缺少统一、可解释、可审计的发布标准。

EasyShift-MaaS 的定位就是解决这三件事：
1. **点位标准化**：YAML -> `PointCatalog` + `FieldDictionary`
2. **迁移标准化**：生成 `MigrationDraft`（迁移草案）
3. **发布标准化**：`validate + quality-check` 通过后才发布模板

> v0.2 默认不做自动闭环控制下发，只做迁移、评估和仿真输出。

## 2. 你需要提供什么输入
最少要提供三类输入：
1. 点位与数据源
   - 标准或 legacy YAML
   - Redis/MySQL 连接引用（`conn_ref`）
2. 场景信息
   - `scene_metadata`
3. 字段语义
   - `field_dictionary`

可选输入：
- 自然语言要求（`nl_requirements`）
- 回归样本（`regression_samples`）
- 质量门禁阈值（`TemplateQualityGate`）

## 3. 你将得到什么输出
1. `ContextBuildResult`
   - `scene_context`（可执行上下文）
   - `snapshot`（点位读取结果、缺失字段、质量标记、延迟）
2. `MigrationDraft`
   - 可发布模板草案 + 风险 + 待确认项
3. `TemplateQualityReport`
   - 结构、语义、可解性、安全覆盖、回归表现评分
4. `PipelineResult`
   - 预测结果、优化建议值、**安全规则判定结果**、最终建议值

## 4. 迁移草案应该长什么样（重点）
`MigrationDraft` 不是一句提示词结果，而是完整结构化对象：

```json
{
  "draft_id": "draft-xxxx",
  "template": {
    "template_id": "demo-line-template",
    "version": "draft-1",
    "scene_metadata": {
      "scene_id": "demo-line",
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
        }
      ],
      "alias_map": {}
    },
    "objective": {
      "terms": [
        { "field_name": "energy_cost", "direction": "min", "weight": 1.0 }
      ],
      "normalize_weights": false
    },
    "constraints": [],
    "prediction": {
      "feature_fields": ["energy_cost"],
      "horizon_steps": 3,
      "model_signature": "rule-bootstrap:v1"
    },
    "optimization": {
      "solver_name": "projected-heuristic",
      "max_iterations": 60,
      "tolerance": 1e-6,
      "time_budget_ms": 300
    },
    "guardrail": {
      "rules": [
        { "field_name": "energy_cost", "max_delta": 0.2, "action": "clip" }
      ],
      "fallback_policy": "keep_previous"
    }
  },
  "confidence": 0.82,
  "pending_confirmations": ["Confirm objective term weights"],
  "risks": [],
  "generation_strategy": "rule_only"
}
```

### 4.1 一份“可发布草案”至少要满足
- `objective` 非空。
- `prediction.feature_fields` 全部在 `field_dictionary` 中。
- `constraints` 无冲突。
- 安全规则覆盖关键目标/可控字段。
- `validate` 和 `quality-check` 都通过。

## 5. 使用方式（最短路径）
1. 导入点位 YAML：`POST /v1/catalogs/import`
2. 构建上下文：`POST /v1/contexts/build`
3. 生成草案：`POST /v1/templates/generate`
4. 校验草案：`POST /v1/templates/validate`
5. 质量评估：`POST /v1/templates/quality-check`
6. 发布模板：`POST /v1/templates/publish`
7. 仿真/评测：`POST /v1/pipeline/simulate` 或 `/v1/pipeline/evaluate`

## 6. 预期效果（建议你用这些指标衡量）
- 迁移效率：新场景迁移周期是否明显缩短。
- 模板质量：质量门禁通过率，失败原因是否可解释。
- 稳定性：仿真中的违规率、不可解率、回归匹配率。
- 可复用性：新场景复用既有模板与组件的比例。

## 7. 运行方式
### 7.1 本地启动
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn easyshift_maas.api.app:app --reload --port 8000
```

### 7.2 Docker 联调
```bash
docker compose up --build
```

### 7.3 Nuitka 打包
```bash
pip install '.[build]'
./scripts/build_nuitka.sh
```

## 8. API 总览
- Catalog / Context
  - `POST /v1/catalogs/import`
  - `GET /v1/catalogs/{catalog_id}`
  - `POST /v1/contexts/build`
- Template
  - `POST /v1/templates/generate`
  - `POST /v1/templates/validate`
  - `POST /v1/templates/quality-check`
  - `POST /v1/templates/publish`
  - `GET /v1/templates/{template_id}`
  - `GET /v1/templates/base`
- Pipeline
  - `POST /v1/pipeline/simulate`
  - `POST /v1/pipeline/evaluate`
- Health
  - `GET /health`

## 9. 文档站
- 在线文档（GitHub Pages）：<https://shunyuwu-shaun.github.io/AgenticB/>
- 本地预览：
```bash
pip install '.[docs]'
mkdocs serve
```

## 10. 术语替换（避免抽象）
- `守护裁决` -> **安全规则判定结果**
- `守护规则` -> **安全规则**
- `发布门禁` -> **质量门禁（可配置阈值）**

## 11. 非泄漏声明
- 本仓库仅包含 synthetic 示例。
- 不包含任何商用 demo 资产。
- CI 含敏感扫描：`tools/sensitive_scan.py`

## 12. License
Apache-2.0
