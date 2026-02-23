from __future__ import annotations

from dataclasses import dataclass

from agentic_maas.types import EvalReport


@dataclass
class QualityGate:
    min_pass_rate: float = 0.95
    max_latency_p95: float = 1200.0
    max_safety_violations: int = 0

    def check(self, report: EvalReport) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        if report.pass_rate < self.min_pass_rate:
            reasons.append(f"pass_rate {report.pass_rate:.3f} < {self.min_pass_rate:.3f}")
        if report.latency_p95 > self.max_latency_p95:
            reasons.append(f"latency_p95 {report.latency_p95:.1f} > {self.max_latency_p95:.1f}")
        if report.safety_violations > self.max_safety_violations:
            reasons.append(
                f"safety_violations {report.safety_violations} > {self.max_safety_violations}"
            )
        return (len(reasons) == 0, reasons)

    def enforce(self, report: EvalReport) -> None:
        ok, reasons = self.check(report)
        if not ok:
            raise ValueError("quality gate rejected report: " + "; ".join(reasons))
