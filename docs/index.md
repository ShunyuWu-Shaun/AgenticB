# ReflexFlow-MaaS 文档

![ReflexFlow-MaaS Logo](assets/branding/logo.png)

ReflexFlow-MaaS 是用于工业预测-优化配置迁移的多 Agent 框架。

它的分工明确：
1. LLM 负责语义理解与结构化草案生成。
2. 确定性代码负责校验、评分和阻断。
3. 自动修正流程在失败后给出下一轮修改建议。

![ReflexFlow-MaaS Framework](assets/branding/framework.png)

## 核心价值
1. 把 legacy 点位名称转换成标准字段字典。
2. 把自然语言需求转换成可发布的迁移草案。
3. 在发布前统一执行质量门禁，降低错误配置上线风险。

## 推荐阅读顺序
1. [项目定位](getting-started/overview.md)
2. [10分钟上手](getting-started/quickstart.md)
3. [架构与运行逻辑](concepts/architecture.md)
4. [迁移草案定义](concepts/migration-draft.md)
5. [HTTP API](reference/http-api.md)

## 文档站发布地址
- [https://shunyuwu-shaun.github.io/ReflexFlow-MaaS/](https://shunyuwu-shaun.github.io/ReflexFlow-MaaS/)
