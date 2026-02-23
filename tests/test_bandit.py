from agentic_maas.adaptation.bandit import ThompsonSamplingBandit


def test_bandit_updates_and_context_isolation() -> None:
    bandit = ThompsonSamplingBandit(["arm_a", "arm_b"])

    arm = bandit.select_arm()
    assert arm in {"arm_a", "arm_b"}

    bandit.update("arm_a", 1.0)
    bandit.update("arm_a", 0.0)

    snapshot_global = bandit.snapshot()
    assert snapshot_global["arm_a"]["pulls"] == 2

    context = {"site": "A", "shift": "night"}
    bandit.update("arm_b", 1.0, context=context)
    snapshot_ctx = bandit.snapshot(context=context)
    assert snapshot_ctx["arm_b"]["pulls"] == 1

    # Ensure contextual stats do not leak into global stats.
    assert snapshot_global["arm_b"]["pulls"] == 0
