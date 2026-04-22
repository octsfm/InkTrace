from application.services.capacity_planner_service import CapacityPlannerService


def test_capacity_plan_for_8k_model():
    service = CapacityPlannerService()
    plan = service.build_plan("kimi-8k", 8000)
    assert plan["chapter_soft_limit_chars"] == 12000
    assert plan["chunk_size_chars"] == 4000
    assert plan["batch_size_chapters"] == 8
    assert plan["enable_chunking"] is True


def test_capacity_plan_for_32k_model():
    service = CapacityPlannerService()
    plan = service.build_plan("kimi-32k", 32000)
    assert plan["chapter_soft_limit_chars"] == 30000
    assert plan["chunk_size_chars"] == 9000
    assert plan["batch_size_chapters"] == 12


def test_capacity_plan_for_128k_model():
    service = CapacityPlannerService()
    plan = service.build_plan("kimi-128k", 128000)
    assert plan["chapter_soft_limit_chars"] == 90000
    assert plan["chunk_size_chars"] == 24000
    assert plan["batch_size_chapters"] == 20
