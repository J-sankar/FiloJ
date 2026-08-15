import grpc.aio
from grpc import RpcError
from auth_service.grpc.generated import auth_pb2_grpc
from fastapi import  status
from shared.logger import get_logger
from dispatcher.core.exceptions import WebhookException
from dispatcher.grpc_clients.generated import auth_pb2

logger = get_logger(__name__)


class AuthGrpcClient:
    """Global gRPC Client for Auth"""
    def __init__(self):
        self.target = "localhost:50051"
        self.channel = grpc.aio.insecure_channel(self.target)
        self.stub = auth_pb2_grpc.AuthServiceStub(self.channel)
        logger.info(f"gRPC Client (Auth): Connected to {self.target}")

    async def look_up_webhook_config(self, developer_id:str) -> auth_pb2.WebhookConfigResponse :
        """Look up Webhook Configurations"""
        try:
            request:auth_pb2.WebhookConfigRequest = auth_pb2.WebhookConfigRequest(developer_id=developer_id)
            response = await self.stub.LookupWebhookConfig(request)
            return response
        except RpcError as e:
            logger.warning(f"gRPC Client (Auth)| ERROR : {e.details()} |Code : {e.code()}",exc_info=True)

            if e.code() == grpc.StatusCode.UNAUTHENTICATED :
                raise WebhookException(
                    code=status.HTTP_401_UNAUTHORIZED,
                    details= e.details()
                )
            
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise WebhookException(
                    code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    details= e.details()
                )
            if e.code() == grpc.StatusCode.NOT_FOUND :
                raise WebhookException(
                    code=status.HTTP_400_BAD_REQUEST,
                    details=e.details()
                )
            
            raise WebhookException(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details="Internal authentication error")
        
        except Exception as e:
            logger.error(f"gRPC Client (Auth) | Some Error Occured: {str(e).lower()}",exc_info=True)
            raise WebhookException(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details="Internal Server Error"
            )
        

    async def close(self):
        """Gracefully close connection during shutdown """
        await self.channel.close()
        logger.info("gRPC(Auth): Connection closed")
        
        
