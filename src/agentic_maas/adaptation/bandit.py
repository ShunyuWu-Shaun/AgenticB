from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


@dataclass
class ArmStats:
    alpha: float = 1.0
    beta: float = 1.0
    pulls: int = 0
    reward_sum: float = 0.0


class ThompsonSamplingBandit:
    """Contextual Thompson Sampling with bucketed context keys."""

    def __init__(self, arms: list[str]) -> None:
        if not arms:
            raise ValueError("at least one arm is required")
        self._global: dict[str, ArmStats] = {arm: ArmStats() for arm in arms}
        self._contextual: dict[str, dict[str, ArmStats]] = {}

    def select_arm(self, context: dict[str, Any] | None = None) -> str:
        table = self._get_table(context)
        sampled = {
            arm: random.betavariate(stats.alpha, stats.beta) for arm, stats in table.items()
        }
        return max(sampled, key=sampled.get)

    def update(self, arm: str, reward: float, context: dict[str, Any] | None = None) -> None:
        if reward < 0.0 or reward > 1.0:
            raise ValueError("reward must be in [0, 1]")

        table = self._get_table(context)
        if arm not in table:
            raise KeyError(f"unknown arm: {arm}")

        stats = table[arm]
        stats.alpha += reward
        stats.beta += 1.0 - reward
        stats.pulls += 1
        stats.reward_sum += reward

    def snapshot(self, context: dict[str, Any] | None = None) -> dict[str, dict[str, float | int]]:
        table = self._get_table(context)
        return {
            arm: {
                "alpha": stats.alpha,
                "beta": stats.beta,
                "pulls": stats.pulls,
                "avg_reward": (stats.reward_sum / stats.pulls if stats.pulls else 0.0),
            }
            for arm, stats in table.items()
        }

    def _get_table(self, context: dict[str, Any] | None) -> dict[str, ArmStats]:
        if not context:
            return self._global

        key = self._context_key(context)
        if key not in self._contextual:
            self._contextual[key] = {arm: ArmStats() for arm in self._global}
        return self._contextual[key]

    def _context_key(self, context: dict[str, Any]) -> str:
        return "|".join(f"{k}={context[k]}" for k in sorted(context.keys()))
