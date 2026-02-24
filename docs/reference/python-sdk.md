# Python SDK 扩展点

## 自定义预测器
实现：`PredictorProtocol`

```python
class MyPredictor:
    def predict(self, context, spec):
        ...
```

## 自定义优化器
实现：`OptimizerProtocol`

```python
class MyOptimizer:
    def solve(self, prediction, objective, constraints, optimization, context):
        ...
```

## 自定义安全规则判定器
实现：`GuardrailProtocol`

```python
class MyGuardrail:
    def validate(self, plan, context, guardrail):
        ...
```

## 组装执行链
```python
from easyshift_maas.core.pipeline import PredictionOptimizationPipeline

pipeline = PredictionOptimizationPipeline(
    predictor=MyPredictor(),
    optimizer=MyOptimizer(),
    guardrail=MyGuardrail(),
)
```

## 数据接入扩展
- 新数据源：实现 `SourceSnapshotProviderProtocol`。
- 新 YAML 解析策略：实现/扩展 `CatalogLoaderProtocol`。
- 新密钥系统：实现 `SecretResolverProtocol`。

## 建议
- 所有扩展都要保持与 `contracts.py` 契约一致。
- 先通过 unit test 再接入 API。
