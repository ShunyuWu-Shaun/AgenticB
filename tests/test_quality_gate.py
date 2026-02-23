from agentic_maas.evaluation.gate import QualityGate
from agentic_maas.types import EvalReport


def test_quality_gate_pass_and_fail() -> None:
    gate = QualityGate(min_pass_rate=0.95, max_latency_p95=500.0, max_safety_violations=0)

    ok_report = EvalReport(
        scenario_id="s1",
        pass_rate=0.97,
        latency_p95=300.0,
        safety_violations=0,
        false_positive_rate=0.01,
        false_negative_rate=0.02,
    )
    fail_report = EvalReport(
        scenario_id="s2",
        pass_rate=0.90,
        latency_p95=700.0,
        safety_violations=1,
        false_positive_rate=0.1,
        false_negative_rate=0.2,
    )

    assert gate.check(ok_report)[0] is True
    ok, reasons = gate.check(fail_report)
    assert ok is False
    assert len(reasons) == 3
