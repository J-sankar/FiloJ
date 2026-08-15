import json

from aio_pika.abc import AbstractIncomingMessage
from shared.logger import get_logger

from dispatcher.core.exceptions import DispatchError
from dispatcher.orchestrator.delivery import attempt_delivery
from dispatcher.orchestrator.dispatch_context import DispatchContext
from dispatcher.utils.headers import prepare_headers
from dispatcher.utils.retry import (
    build_dead_letter_message,
    build_retry_message,
    should_retry,
)
from dispatcher.utils.signer import sign_request_body

logger = get_logger(__name__)


async def process_webhook(message:AbstractIncomingMessage, ctx: DispatchContext):
    async with message.process(requeue=True):
        try:
            raw_body = message.body.decode()
            payload = json.loads(raw_body)
            logger.debug(payload)
            developer_id:str = payload.get("developer_id",None)
            file_id:str = payload.get("file_id",None)
            status:str = payload.get("status","None")
            result:dict = payload.get("result",None)
            attempt:int = payload.get("attempt", 0)
            event:str = payload.get("event",None)
            logger.info(f"Initiating Webhook dispatch: {message.message_id} | attempt: {attempt}")    
            if not developer_id:
                raise ValueError("Developer id is required")
            config_resolver = ctx.config_resolver
            http_client = ctx.http_client
            broker = ctx.broker
            webhook_url,webhook_secret = await config_resolver.get_webhook_config(developer_id)
            request_body = {
                "file_id":file_id,
                "status" : status,
                "result": result,
                "event" : event
            } 
            raw_body = json.dumps(request_body,separators=(".", ":"))
            signature = sign_request_body(key=webhook_secret,body_str=raw_body)
            headers = prepare_headers(signature)
            await attempt_delivery(http_client,webhook_url,raw_body,headers)
            logger.info("Webhook dispatched")
        except DispatchError as e:
            logger.error(f"DISPATCH ERROR: {str(e).lower()}, retrable: {e.retryable}")
            if e.retryable and should_retry(attempt):
                new_payload, headers = build_retry_message(payload, attempt)
                await broker.publish("webhook.retry", event, new_payload, headers=headers)
            else:
                logger.warning(
                    f"Max webhook attempts reached for {message.message_id}; sending to dead letter"
                )
                dead_payload = build_dead_letter_message(payload, str(e))
                await broker.publish("dlx.exchange", "webhook.dead", dead_payload)
        except ValueError as e:
            logger.exception(f"VALUE ERROR: {str(e.lower())}" ,exc_info=True)  # noqa: G202, RUF010
            return
        except Exception as e:
            logger.exception(f"UNHANDLED EXCEPTION: {str(e).lower()}",exc_info=True)  # noqa: G202
            raise 
            
        
        

