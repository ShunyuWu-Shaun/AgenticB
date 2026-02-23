from __future__ import annotations

from datetime import datetime, timezone

from agentic_maas.evaluation.gate import QualityGate
from agentic_maas.store.memory import InMemoryStore
from agentic_maas.types import CanaryDeployment, CanaryRequest, DeploymentStatus


class DeploymentManager:
    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    def create_canary(self, request: CanaryRequest, quality_gate: QualityGate) -> CanaryDeployment:
        ok, reasons = quality_gate.check(request.eval_report)
        deployment = CanaryDeployment(
            migration_id=request.migration_id,
            traffic_percent=request.traffic_percent,
            status=DeploymentStatus.ACTIVE if ok else DeploymentStatus.BLOCKED,
            reason=None if ok else "; ".join(reasons),
        )
        self.store.save_deployment(deployment)
        return deployment

    def rollback(self, deployment_id: str, reason: str) -> CanaryDeployment:
        deployment = self.store.get_deployment(deployment_id)
        if not deployment:
            raise KeyError(f"deployment not found: {deployment_id}")

        rolled_back = deployment.model_copy(
            update={
                "status": DeploymentStatus.ROLLED_BACK,
                "reason": reason,
                "updated_at": datetime.now(tz=timezone.utc),
            }
        )
        self.store.save_deployment(rolled_back)
        return rolled_back
