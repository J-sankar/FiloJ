from auth_service.grpc.generated import auth_pb2
from shared.logger import get_logger
from auth_service.grpc.generated import auth_pb2_grpc
from shared.database import AsyncSesssionLocal
from auth_service.core.exceptions import (
    InvalidApiKeyError,
    InactiveApiKeyError,
    InactiveDeveloperError,
    DeveloperNotFoundError,
    WebhookConfigNotFoundError
)
from auth_service.services.auth import get_api_key_developer,get_webhook_config
from shared.plan_limits import PLAN_LIMITS
import grpc


logger = get_logger(__name__)


class AuthService(auth_pb2_grpc.AuthServiceServicer):
    async def LookupApiKey(self, request, context):
        logger.debug(f"obtained request for api: {request.key_hash[:8]}")

        async with AsyncSesssionLocal() as db:
            try:
                developer, status = await get_api_key_developer(
                    key_hash=request.key_hash, db=db
                )
            except (
                InactiveDeveloperError,
                InvalidApiKeyError,
                InactiveApiKeyError,
            ) as e:
                logger.warning(f"Auth failed: {str(e).lower()}")
                await context.abort(grpc.StatusCode.UNAUTHENTICATED, str(e).lower())
            except Exception as e:
                logger.warning(f"Auth failed: {str(e).lower()}")
                await context.abort(grpc.StatusCode.INTERNAL, str(e).lower())
        plan_limits = PLAN_LIMITS.get(developer.plan, None)
        requests_per_hour = plan_limits.get("requests_per_hour")
        max_file_size_bytes = plan_limits.get("max_file_size_bytes", 0)
        storage_quota_bytes = plan_limits.get("storage_quota_bytes", 0)

        return auth_pb2.ApiKeyLookupResponse(
            found=1,
            status=status,
            plan=developer.plan,
            requests_per_hour=requests_per_hour,
            max_file_size_bytes=max_file_size_bytes,
            storage_quota_bytes=storage_quota_bytes,
            developer_id=str(developer.id),
        )

    async def LookupWebhookConfig(self, request, context):
        logger.debug(
            f"Obtained webhook lookup request for developer: {request.developer_id[:8]}"
        )
        async with AsyncSesssionLocal() as db:
            try:
                webhook_url,webhook_secret = await get_webhook_config(request.developer_id,db)
                return auth_pb2.WebhookConfigResponse(
                    found =1 ,
                    webhook_url=webhook_url,
                    webhook_secret=webhook_secret
                )
            except WebhookConfigNotFoundError as e:
                logger.warning(f"ERROR: {str(e).lower()}")
                return auth_pb2.WebhookConfigResponse(
                    found = 0
                )
            except DeveloperNotFoundError as e:
                logger.exception(f"ERROR: {str(e).lower()}")
                await context.abort(grpc.StatusCode.NOT_FOUND,str(e).lower())
            except Exception as e:
                logger.exception(f"Auth failed: {str(e).lower()}")
                await context.abort(grpc.StatusCode.INTERNAL, str(e).lower())

