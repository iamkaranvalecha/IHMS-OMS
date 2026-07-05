"""Unit tests for structured logging."""

import json
import logging

import pytest
from src.observability.context import bind_log_context, clear_log_context, reset_log_context
from src.observability.logging import JsonLogFormatter, configure_logging


def test_json_formatter_emits_required_fields() -> None:
    token = bind_log_context(
        request_id="req-1",
        correlation_id="corr-1",
        trace_id="trace-1",
    )
    try:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hold placed",
            args=(),
            exc_info=None,
        )
        record.step = "place_hold"
        record.hold_id = "hold-abc"

        payload = json.loads(JsonLogFormatter().format(record))
        assert payload["message"] == "hold placed"
        assert payload["level"] == "INFO"
        assert payload["request_id"] == "req-1"
        assert payload["correlation_id"] == "corr-1"
        assert payload["trace_id"] == "trace-1"
        assert payload["step"] == "place_hold"
        assert payload["hold_id"] == "hold-abc"
        assert "timestamp" in payload
    finally:
        reset_log_context(token)
        clear_log_context()


def test_configure_logging_json_mode(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", json_format=True)
    logger = logging.getLogger("test.configure.stdout")
    token = bind_log_context(request_id="req-json")
    try:
        logger.info("hello structured")
        captured = capsys.readouterr().out.strip()
        payload = json.loads(captured.splitlines()[-1])
        assert payload["message"] == "hello structured"
        assert payload["request_id"] == "req-json"
    finally:
        reset_log_context(token)
        clear_log_context()
