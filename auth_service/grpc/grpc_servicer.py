from auth_service.grpc.generated import auth_pb2
from shared.logger import get_logger
from auth_service.grpc.generated import auth_pb2_grpc
from shared.database import AsyncSesssionLocal
from auth_service.core.exceptions import InvalidApiKeyError, InactiveApiKeyError, InactiveDeveloperError
from auth_service.services.auth import validate_api_key
import grpc


logger = get_logger(__name__)

class AuthService(auth_pb2_grpc.AuthServiceServicer):

    async def ValidateKey(self, request, context):
        logger.debug(f"obtained request for api: {request.api_key[:8]}")
        
        async with AsyncSesssionLocal() as db:
            try:
                developer = await validate_api_key(api_key=request.api_key,db=db)
            except (InactiveDeveloperError,InvalidApiKeyError,InactiveApiKeyError) as e:
                logger.warning(f"Auth failed: {str(e).lower()}")
                return context.abort(
                    grpc.StatusCode.UNAUTHENTICATED,
                    str(e).lower()
                )
            except Exception as e:
                logger.warning(f"Auth failed: {str(e).lower()}")
                return context.abort(
                    grpc.StatusCode.INTERNAL,
                    str(e).lower()
                )

        return auth_pb2.ValidateKeyResponse(valid=True, plan=developer.plan)