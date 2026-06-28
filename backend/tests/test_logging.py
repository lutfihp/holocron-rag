from __future__ import annotations

import json

import pytest
import structlog

from app.core.logging import configure_logging


def _capture_stdout(capsys) -> str:
    return capsys.readouterr().out.strip()


def test_configure_logging_json_mode_outputs_valid_json(capsys):
    configure_logging(pretty=False)
    log = structlog.get_logger()
    log.info("test_event", foo="bar", count=42)
    out = _capture_stdout(capsys)
    assert out, "expected JSON output on stdout"
    payload = json.loads(out)
    assert payload["event"] == "test_event"
    assert payload["foo"] == "bar"
    assert payload["count"] == 42
    assert "timestamp" in payload


def test_configure_logging_pretty_mode_does_not_emit_json(capsys):
    configure_logging(pretty=True)
    log = structlog.get_logger()
    log.info("pretty_event", foo="bar")
    out = _capture_stdout(capsys)
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)
    assert "pretty_event" in out


def test_contextvar_correlation_id_appears_in_json(capsys):
    configure_logging(pretty=False)
    structlog.contextvars.bind_contextvars(correlation_id="abc-123")
    try:
        log = structlog.get_logger()
        log.info("bound_event")
        payload = json.loads(_capture_stdout(capsys))
        assert payload["correlation_id"] == "abc-123"
    finally:
        structlog.contextvars.clear_contextvars()
