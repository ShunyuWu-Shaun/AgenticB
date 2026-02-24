# 教程：Legacy YAML 迁移

目标：把旧式点位配置快速迁移到标准结构。

## Legacy 特征
- 顶层有大量点位键。
- 可能带 `redis_config` 或 `mysql_config`。
- 字段语义信息不完整。

## 迁移步骤
1. 使用 `mode=legacy` 导入。
2. 查看响应里的：
   - `warnings`
   - `pending_confirmations`
3. 导出并人工补齐：
   - 字段语义（`semantic_label`）
   - 单位（`unit`）
   - 可控性（`controllable`）
4. 转成标准 YAML 长期维护。

## 导入示例
```bash
curl -X POST http://127.0.0.1:8000/v1/catalogs/import \
  -H 'Content-Type: application/json' \
  -d '{"mode":"legacy","yaml_path":"./src/easyshift_maas/examples/data/catalog_legacy.yaml"}'
```

## 建议
- Legacy 模式只用于过渡，不建议长期依赖。
- 每次迁移都应产出标准 YAML 版本并入库。
