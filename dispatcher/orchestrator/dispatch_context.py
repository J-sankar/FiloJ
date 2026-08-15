from dataclasses import dataclass
from shared.broker import BrokerClient
import httpx
from dispatcher.orchestrator.webhook_config import WebhookConfigResolver


@dataclass
class DispatchContext:
    broker: BrokerClient
    http_client: httpx.AsyncClient
    config_resolver: WebhookConfigResolver