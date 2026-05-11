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
