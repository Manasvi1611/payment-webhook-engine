"""Integration tests for event ingestion API."""
from unittest.mock import MagicMock, patch


async def test_ingest_valid_event_returns_200(client):
    with patch("app.routers.events.deliver_event") as mock_task:
        mock_task.delay = MagicMock()
        response = await client.post(
            "/events/",
            json={
                "event_type": "payment.success",
                "payload": {"transaction_id": "txn_001", "amount": 5000},
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "payment.success"
    assert "id" in data
    assert "queued_at" in data


async def test_ingest_invalid_event_type_returns_422(client):
    response = await client.post(
        "/events/",
        json={"event_type": "payment.unknown", "payload": {"amount": 100}},
    )
    assert response.status_code == 422


async def test_ingest_missing_payload_returns_422(client):
    response = await client.post(
        "/events/",
        json={"event_type": "payment.success"},
    )
    assert response.status_code == 422


async def test_event_queued_for_matching_subscriber(client):
    """Delivery task is dispatched only for subscribers with matching event type."""
    # Create a subscriber that listens to payment.success
    sub_resp = await client.post(
        "/subscribers/",
        json={
            "name": "MerchantA",
            "url": "https://merchant-a.example.com/webhooks",
            "events": ["payment.success"],
            "secret": "s3cr3t",
        },
    )
    assert sub_resp.status_code == 200

    with patch("app.routers.events.deliver_event") as mock_task:
        mock_task.delay = MagicMock()
        await client.post(
            "/events/",
            json={"event_type": "payment.success", "payload": {"amount": 100}},
        )
        # Exactly one subscriber matched
        mock_task.delay.assert_called_once()
        call_kwargs = mock_task.delay.call_args.kwargs
        assert call_kwargs["event_type"] == "payment.success"
        assert call_kwargs["subscriber_url"] == "https://merchant-a.example.com/webhooks"


async def test_event_not_dispatched_for_non_matching_subscriber(client):
    """Delivery task is NOT dispatched when no subscriber matches the event type."""
    await client.post(
        "/subscribers/",
        json={
            "name": "MerchantB",
            "url": "https://merchant-b.example.com/webhooks",
            "events": ["payment.refunded"],
            "secret": "s3cr3t",
        },
    )

    with patch("app.routers.events.deliver_event") as mock_task:
        mock_task.delay = MagicMock()
        await client.post(
            "/events/",
            json={"event_type": "payment.failed", "payload": {"amount": 200}},
        )
        mock_task.delay.assert_not_called()
