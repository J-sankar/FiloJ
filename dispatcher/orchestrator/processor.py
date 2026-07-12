import httpx
from redis.asyncio import Redis
from shared.logger import get_logger
from dispatcher.core.exceptions import WebhookException
from dispatcher.orchestrator.dispatch_context import DispatchContext
from dispatcher.utils.signer import sign_request_body
from dispatcher.utils.headers import prepare_headers
from dispatcher.utils.retry import (should_retry,build_retry_message,build_dead_letter_message)
from aio_pika.abc import AbstractIncomingMessage

import json

logger = get_logger(__name__)


async def process_webhook(message:AbstractIncomingMessage,redis:Redis, ctx: DispatchContext):
    try:
        async with message.process(requeue=True):    
            raw_body = message.body.decode()
            payload = json.loads(raw_body)
            developer_id:str = payload.get("developer_id",None)
            file_id:str = payload.get("file_id",None)
            status:str = payload.get("status","None")
            result:dict = payload.get("result",None)
            attempt:int = payload.get("attempt", 0)
            event:str = payload.get("event",None)
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
            response = await http_client.post(url=webhook_url,content=raw_body,headers=headers)
            if str(response.status_code).startswith("3"):
                raise httpx.HTTPStatusError("No redirects allowed",response=response) 
            response.raise_for_status()
            logger.info(f"Webhook dispatched | Response :{response.status_code}")
            return response
    except httpx.HTTPStatusError as e:
        status_code = str(e.response.status_code)
        if status_code.startswith("5") or status_code == "429" :
            if should_retry(attempt):
                attempt_payload, header = build_retry_message(payload,attempt)
                await broker.publish("webhook.retry",event,attempt_payload,header)
                return 
            else:
                dead_payload = build_dead_letter_message(payload,str(e).lower())
                await broker.publish("dlx.exchange","webhook.dead",dead_payload)
                return
        dead_payload = build_dead_letter_message(payload,str(e).lower())
        await broker.publish("dlx.exchange","webhook.dead",dead_payload)
        return
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        if should_retry(attempt):
                attempt_payload, header = build_retry_message(payload,attempt)
                await broker.publish("webhook.retry",event,attempt_payload,header)
                return
        else:
                dead_payload = build_dead_letter_message(payload,str(e).lower())
                await broker.publish("dlx.exchange","webhook.dead",dead_payload)
                return
    except WebhookException as e:
        dead_payload = build_dead_letter_message(payload,str(e).lower())
        await broker.publish("dlx.exchange","webhook.dead",dead_payload)
        return
    except Exception :
         raise 
         
    
    

