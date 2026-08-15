from typing import Any
from uuid import UUID

from shared.broker import BrokerClient
from shared.logger import get_logger


logger = get_logger(__name__)


class WebhookDispatchError(RuntimeError):
    """Raised when a webhook payload cannot be prepared or published."""


async def dispatch_to_webhook(
    broker: BrokerClient,
    event: str,
    file_id: UUID | str,
    status: str,
    result: dict[str, Any],
    developer_id:str,
) -> None:
    if not event.strip():
        raise ValueError("event is required")
    if not status.strip():
        raise ValueError("status is required")

    try:
        payload = {
            "event": event,
            "file_id": str(file_id),
            "status": status,
            "result": result,
            "developer_id": developer_id
        }
        logger.debug(payload)
        await broker.publish("webhook.retry", event, payload=payload)
    except (TypeError, ValueError) as exc:
        logger.exception("Invalid webhook payload")
        raise WebhookDispatchError("Failed to prepare webhook payload") from exc
    except Exception as exc:
        logger.exception("Failed to publish webhook event")
        raise WebhookDispatchError("Failed to publish webhook event") from exc

    logger.info("Published to webhook exchange")