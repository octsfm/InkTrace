from __future__ import annotations

from application.services.ai.output_validation_service import OutputValidationService


def test_output_validation_service_accepts_valid_plain_text_output() -> None:
    service = OutputValidationService()

    result = service.validate("plain_text", "这是合法输出")

    assert result.success is True
    assert result.error_code == ""


def test_output_validation_service_rejects_invalid_plain_text_output() -> None:
    service = OutputValidationService()

    result = service.validate("plain_text", "")

    assert result.success is False
    assert result.error_code == "output_schema_invalid"


def test_output_validation_service_accepts_valid_selection_rewrite_schema_output() -> None:
    service = OutputValidationService()

    result = service.validate(
        "selection_rewrite_schema",
        {
            "rewritten_text": "月光静静落在旧窗台上",
            "diff_summary": "补强环境描写",
            "risk_notes": ["保持原剧情事实"],
        },
    )

    assert result.success is True
    assert result.parsed_output["rewritten_text"] == "月光静静落在旧窗台上"
    assert result.parsed_output["diff_summary"] == "补强环境描写"


def test_output_validation_service_rejects_selection_rewrite_schema_without_rewritten_text() -> None:
    service = OutputValidationService()

    result = service.validate(
        "selection_rewrite_schema",
        {
            "rewritten_text": "   ",
            "diff_summary": "补强环境描写",
            "risk_notes": [],
        },
    )

    assert result.success is False
    assert result.error_code == "output_schema_invalid"
