from unittest.mock import patch

from app.agent import run_once
from app.config import Settings


@patch("app.agent.send_metrics")
@patch("app.agent.collect_system_metrics")
def test_run_once_collects_formats_and_sends(mock_collect, mock_send):
    mock_collect.return_value = {
        "timestamp": "2026-10-07T10:00:00+00:00",
        "hostname": "test-host",
        "cpu": {"percent": 5.0},
        "memory": {"percent": 30.0},
        "system": {"load_1m": 0.1},
    }
    mock_send.return_value = {"status_code": 201, "response": {}}
    settings = Settings("http://api:8000/metrics", 5, 3)

    result = run_once(settings)

    assert result["status_code"] == 201
    kwargs = mock_send.call_args.kwargs
    assert kwargs["endpoint"] == "http://api:8000/metrics"
    assert kwargs["timeout"] == 3
    assert kwargs["payload"]["data"]["hostname"] == "test-host"
