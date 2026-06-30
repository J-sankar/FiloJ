from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from gateway.utils.headers import HeaderBuilder
from gateway.core.security import decode_token
from httpx import AsyncClient
from gateway.core.config import TIMEOUTS, SERVICES
from shared.logger import get_logger
import httpx

logger = get_logger(__name__)


def get_service_url(service: str) -> str:
    url = SERVICES.get(service)
    if not url:
        logger.error(f"ERROR: {service} not found in gateway")
        raise HTTPException(404, f"Service '{service}' not found")
    return url


def get_timeout(service: str) -> float:

    return TIMEOUTS.get(service, TIMEOUTS["default"])


async def proxy_request(
    service: str, path: str, request: Request, developer_id: str = "", plan: str = ""
) -> StreamingResponse:
    target = get_service_url(service)
    timeout = get_timeout(service)
    logger.info(f"Incoming method: {request.method}")  # add this
    proxy_url = f"{target}/{path}"
    logger.debug(proxy_url)
    if service == "auth" and path == "  api/key":
        logger.debug("here ?")
        token = decode_token(request)
        developer_id = token.get("sub")
        plan = token.get("plan")
    headers = HeaderBuilder.from_request(request, developer_id, plan).to_dict()
    logger.debug(headers)
    logger.info(f"Forwarding to: {proxy_url}")
    params = dict(request.query_params)
    logger.info(f"Gateway: {service}/{path} | method : {request.method}")
    client: AsyncClient = request.app.state.http_client
    try:
        req = client.build_request(
            method=request.method,
            url=proxy_url,
            headers=headers,
            content=request.stream(),
            params=params,
            timeout=timeout,  
        )

        response = await client.send(req, stream=True)

        async def cleanup():
            await response.aclose()

        streaming_response = StreamingResponse(
            content=response.aiter_bytes(),
            status_code=response.status_code,
            headers=_filter_response_headers(response.headers),
            media_type=response.headers.get("content-type"),
            background=BackgroundTask(cleanup),
        )
        for cookie in response.headers.get_list("set-cookie"):
            streaming_response.headers.append("set-cookie", cookie)
        return streaming_response

    except httpx.ConnectError:
        logger.error(f"Service {service} unavailable")
        raise HTTPException(503, f"Service {service} unavailable")

    except httpx.TimeoutException:
        logger.error(f"Connection time out for service {service}")
        raise HTTPException(504, f"Service {service} timed out")
    except Exception as e:
        logger.error(f"Gateway error: {str(e)}")
        raise HTTPException(502, "Bad gateway")


def _filter_response_headers(headers) -> dict:

    allowed = {
        "content-type",
        "content-disposition",
        "cache-control",
        "x-request-id",
    }
    return {k: v for k, v in headers.items() if k.lower() in allowed}
