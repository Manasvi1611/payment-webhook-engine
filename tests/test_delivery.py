"""Tests for Celery delivery task — retry logic and DLQ routing."""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.worker.tasks import MAX_RETRIES, deliver_event

EVENT_KWARGS = dict(
    event_id="evt-test-001",
    subscriber_id=1,
    subscriber_url="http://subscriber.example.com/webhook",
    subscriber_secret="test-secret-key",
    event_type="payment.success",
    payload={"transaction_id": "txn_001", "amount": 5000},
)


def _mock_http_client(raise_error=None):
    mock_client = MagicMock()
    if raise_error:
        mock_client.post.side_effect = raise_error
    else:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    return mock_client


def test_successful_delivery_logs_success():
    with (
        patch("app.worker.tasks.httpx.Client") as mock_cls,
        patch("app.worker.tasks._update_delivery_log") as mock_log,
    ):
        mock_cls.return_value = _mock_http_client()
        deliver_event.apply(kwargs=EVENT_KWARGS)

    mock_log.assert_called_once()
    args = mock_log.call_args.args
    assert args[4] == "success"   # status
    assert args[6] is None         # no error_message


def test_successful_delivery_includes_hmac_signature_header():
    with (
        patch("app.worker.tasks.httpx.Client") as mock_cls,
        patch("app.worker.tasks._update_delivery_log"),
    ):
        mock_client = _mock_http_client()
        mock_cls.return_value = mock_client
        deliver_event.apply(kwargs=EVENT_KWARGS)

    headers = mock_client.post.call_args.kwargs["headers"]
    assert "X-Webhook-Signature" in headers
    assert len(headers["X-Webhook-Signature"]) == 64  # SHA-256 hex digest
    assert headers["X-Webhook-Event"] == "payment.success"


def test_failed_delivery_at_max_retries_goes_to_dlq():
    with (
        patch("app.worker.tasks.httpx.Client") as mock_cls,
        patch("app.worker.tasks._update_delivery_log"),
        patch("app.worker.tasks.send_to_dlq") as mock_dlq,
    ):
        mock_cls.return_value = _mock_http_client(
            raise_error=httpx.ConnectError("Connection refused")
        )
        deliver_event.apply(kwargs=EVENT_KWARGS, retries=MAX_RETRIES - 1)

    mock_dlq.assert_called_once()
    call_args = mock_dlq.call_args.args
    assert call_args[0] == EVENT_KWARGS["event_id"]
    assert call_args[1] == EVENT_KWARGS["subscriber_id"]


def test_failed_delivery_at_max_retries_logs_dead_letter():
    with (
        patch("app.worker.tasks.httpx.Client") as mock_cls,
        patch("app.worker.tasks._update_delivery_log") as mock_log,
        patch("app.worker.tasks.send_to_dlq"),
    ):
        mock_cls.return_value = _mock_http_client(
            raise_error=httpx.ConnectError("Connection refused")
        )
        deliver_event.apply(kwargs=EVENT_KWARGS, retries=MAX_RETRIES - 1)

    mock_log.assert_called_once()
    args = mock_log.call_args.args
    assert args[4] == "dead_letter"


def test_exponential_backoff_countdown_on_first_failure():
    """On first failure (retries=0) the retry countdown must be 2^0 = 1 second.

    Celery's apply() swallows exceptions raised inside the task, so we capture
    the kwargs passed to self.retry() via a side_effect and assert on them after
    apply() returns.
    """
    captured = {}

    with (
        patch("app.worker.tasks.httpx.Client") as mock_cls,
        patch("app.worker.tasks._update_delivery_log"),
    ):
        mock_cls.return_value = _mock_http_client(
            raise_error=httpx.ConnectError("refused")
        )

        def capturing_retry(*args, **kwargs):
            captured.update(kwargs)
            raise Exception("stop-retry")  # Celery catches this internally

        with patch.object(deliver_event, "retry", side_effect=capturing_retry):
            deliver_event.apply(kwargs=EVENT_KWARGS, retries=0)

    assert "countdown" in captured, "self.retry() was never called"
    assert captured["countdown"] == 1  # 2 ** 0
