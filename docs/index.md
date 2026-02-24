# EasyShift-MaaS 文档

EasyShift-MaaS 是一个面向工业/B 端场景的 **迁移型 Agentic + 预测-优化复用框架**。

它主要解决三件事：
1. 把现场零散点位配置（通常是 YAML + Redis/MySQL 键）整理成统一的数据契约。
2. 把“旧场景的预测-优化逻辑”迁移成可复用模板，而不是散落脚本。
3. 在发布前做可解释的质量校验，避免“能跑但不可靠”的模板上线。

## 你可以得到什么
- 统一点位模型：`PointCatalog` + `FieldDictionary`
- 统一迁移草案：`MigrationDraft`
- 统一执行链：预测 -> 优化 -> 安全规则判定 -> 仿真输出
- 统一发布门禁：结构校验 + 语义校验 + 可解性 + 安全覆盖 + 回归结果

## 这个项目不做什么
- 不直接下发自动闭环控制指令。
- 不携带任何商用 demo 代码或数据。

## 推荐阅读顺序
1. [项目定位](getting-started/overview.md)
2. [10分钟上手](getting-started/quickstart.md)
3. [迁移草案定义](concepts/migration-draft.md)
4. [模板正确性与质量门禁](concepts/template-quality.md)
5. [标准YAML工业流程教程](tutorials/industrial-standard-yaml.md)

## 在线文档发布
- GitHub Pages（默认）：`https://shunyuwu-shaun.github.io/AgenticB/`

> 若页面暂未出现，请确认仓库 Settings -> Pages 已启用 `GitHub Actions` 作为 Source。
