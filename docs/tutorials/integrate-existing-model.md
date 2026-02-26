# 教程：集成现有预测模型

目标：把你已有的模型/求解器接入 ReflexFlow-MaaS，复用现有业务逻辑。

## 可插拔接口
- `PredictorProtocol.predict(context, spec) -> PredictionResult`
- `OptimizerProtocol.solve(prediction, objective, constraints, optimization, context) -> OptimizationPlan`
- `GuardrailProtocol.validate(plan, context, guardrail) -> GuardrailDecision`

## 示例：替换 Predictor
```python
from easyshift_maas.core.contracts import PredictionResult
from easyshift_maas.core.pipeline import PredictionOptimizationPipeline

class MyPredictor:
    def __init__(self, model):
        self.model = model

    def predict(self, context, spec):
        preds = self.model.predict(context.values, spec.feature_fields)
        return PredictionResult(
            predictions=preds,
            model_signature="my-model:v3",
            diagnostics={"source": "custom"},
        )

pipeline = PredictionOptimizationPipeline(
    predictor=MyPredictor(model=...),
)
```

## 集成建议
1. 先替换 Predictor，复用默认 Optimizer 和安全规则。
2. 通过 `simulate/evaluate` 验证差异。
3. 再决定是否替换 Optimizer。

## 注意事项
- 输出字段必须与 `field_dictionary` 一致。
- 自定义组件异常应返回可诊断错误信息。
- 每次替换都应跑回归样本。
