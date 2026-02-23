from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any

from agentic_maas.types import CanaryDeployment, EvalReport, MigrationTask


class InMemoryStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._migrations: dict[str, MigrationTask] = {}
        self._eval_reports: dict[str, EvalReport] = {}
        self._deployments: dict[str, CanaryDeployment] = {}
        self._audit_events: list[dict[str, Any]] = []

    def save_migration(self, task: MigrationTask) -> None:
        with self._lock:
            self._migrations[task.migration_id] = task
            self.audit("migration_saved", {"migration_id": task.migration_id, "status": task.status})

    def get_migration(self, migration_id: str) -> MigrationTask | None:
        with self._lock:
            return self._migrations.get(migration_id)

    def save_eval_report(self, report: EvalReport) -> None:
        with self._lock:
            self._eval_reports[report.scenario_id] = report
            self.audit("eval_saved", {"scenario_id": report.scenario_id, "pass_rate": report.pass_rate})

    def get_eval_report(self, scenario_id: str) -> EvalReport | None:
        with self._lock:
            return self._eval_reports.get(scenario_id)

    def save_deployment(self, deployment: CanaryDeployment) -> None:
        with self._lock:
            self._deployments[deployment.deployment_id] = deployment
            self.audit(
                "deployment_saved",
                {
                    "deployment_id": deployment.deployment_id,
                    "status": deployment.status,
                    "migration_id": deployment.migration_id,
                },
            )

    def get_deployment(self, deployment_id: str) -> CanaryDeployment | None:
        with self._lock:
            return self._deployments.get(deployment_id)

    def audit(self, event_type: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._audit_events.append(
                {
                    "event_type": event_type,
                    "payload": payload,
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                }
            )

    def list_audit_events(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._audit_events)
