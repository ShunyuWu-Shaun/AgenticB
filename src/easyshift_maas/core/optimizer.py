from __future__ import annotations

from typing import Protocol

from easyshift_maas.core.contracts import (
    ConstraintOperator,
    ConstraintSpec,
    ObjectiveDirection,
    ObjectiveSpec,
    OptimizationPlan,
    OptimizationSpec,
    PredictionResult,
    SceneContext,
)


class OptimizerProtocol(Protocol):
    def solve(
        self,
        prediction: PredictionResult,
        objective: ObjectiveSpec,
        constraints: list[ConstraintSpec],
        optimization: OptimizationSpec,
        context: SceneContext,
    ) -> OptimizationPlan: ...


class OptimizerRegistry:
    def __init__(self) -> None:
        self._optimizers: dict[str, OptimizerProtocol] = {}

    def register(self, name: str, optimizer: OptimizerProtocol) -> None:
        self._optimizers[name] = optimizer

    def get(self, name: str) -> OptimizerProtocol:
        if name not in self._optimizers:
            raise KeyError(f"optimizer not found: {name}")
        return self._optimizers[name]

    def names(self) -> list[str]:
        return sorted(self._optimizers.keys())


class ProjectedHeuristicOptimizer:
    """A lightweight reference optimizer using objective shifts + constraint projection."""

    def solve(
        self,
        prediction: PredictionResult,
        objective: ObjectiveSpec,
        constraints: list[ConstraintSpec],
        optimization: OptimizationSpec,
        context: SceneContext,
    ) -> OptimizationPlan:
        setpoints = dict(context.values)

        for term in objective.terms:
            base = prediction.predictions.get(term.field_name, context.values.get(term.field_name, 0.0))
            if term.direction == ObjectiveDirection.MIN:
                setpoints[term.field_name] = base * (1.0 - 0.02 * term.weight)
            else:
                setpoints[term.field_name] = base * (1.0 + 0.02 * term.weight)

        infeasible_reasons: list[str] = []
        for constraint in sorted(constraints, key=lambda item: item.priority):
            field = constraint.field_name
            value = setpoints.get(field, context.values.get(field, 0.0))

            if constraint.operator == ConstraintOperator.LE and constraint.upper_bound is not None:
                setpoints[field] = min(value, constraint.upper_bound)
            elif constraint.operator == ConstraintOperator.GE and constraint.lower_bound is not None:
                setpoints[field] = max(value, constraint.lower_bound)
            elif constraint.operator == ConstraintOperator.EQ and constraint.equals_value is not None:
                setpoints[field] = constraint.equals_value
            elif (
                constraint.operator == ConstraintOperator.BETWEEN
                and constraint.lower_bound is not None
                and constraint.upper_bound is not None
            ):
                if constraint.lower_bound > constraint.upper_bound:
                    infeasible_reasons.append(
                        f"{constraint.name}: lower_bound > upper_bound"
                    )
                    continue
                setpoints[field] = min(max(value, constraint.lower_bound), constraint.upper_bound)

        objective_value = self._objective_value(setpoints, objective)
        status = "infeasible" if infeasible_reasons else "solved"

        return OptimizationPlan(
            recommended_setpoints=setpoints,
            objective_value=objective_value,
            solver_status=status,
            diagnostics={
                "solver": optimization.solver_name,
                "iterations": min(optimization.max_iterations, len(objective.terms) + len(constraints) + 1),
                "infeasible_reasons": infeasible_reasons,
            },
        )

    def _objective_value(self, setpoints: dict[str, float], objective: ObjectiveSpec) -> float:
        score = 0.0
        for term in objective.terms:
            value = setpoints.get(term.field_name, 0.0)
            if term.direction == ObjectiveDirection.MIN:
                score += term.weight * value
            else:
                score -= term.weight * value
        return score
