from application.services.token_budget_manager import TokenBudgetManager


def test_build_capacity_plan_for_8k():
    manager = TokenBudgetManager()
    plan = manager.build_capacity_plan("moonshot-v1-8k", 8192)
    assert plan["model_tier"] == "8k"
    assert int(plan["batch_size_chapters"]) >= 1
    assert int(plan["budget_tokens"]) > 0
    assert int((plan.get("stage_cap_tokens") or {}).get("global_analysis") or 0) > 0


def test_build_capacity_plan_for_128k():
    manager = TokenBudgetManager()
    plan = manager.build_capacity_plan("moonshot-v1-128k", 131072)
    assert plan["model_tier"] == "128k"
    assert int(plan["batch_size_chapters"]) >= 10
    assert int(plan["chapter_soft_limit_chars"]) > int(plan["chunk_size_chars"])


def test_estimate_stage_tokens_is_stable():
    manager = TokenBudgetManager()
    payload = {"outline_digest": {"premise": "测试"}, "batch_digests": [{"batch_no": 1, "digest": "A"}]}
    estimate = manager.estimate_stage_tokens(payload)
    assert isinstance(estimate, int)
    assert estimate > 0
