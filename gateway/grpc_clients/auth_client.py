import grpc.aio
from grpc import RpcError
from gateway.generated import auth_pb2_grpc,auth_pb2
from fastapi import HTTPException, status
from shared.logger import get_logger


logger = get_logger(__name__)


class AuthGrpcClient:
    """Global gRPC Client for Auth"""
    def __init__(self):
        self.target = "localhost:50051"
        self.channel = grpc.aio.insecure_channel(self.target)
        self.stub = auth_pb2_grpc.AuthServiceStub(self.channel)
        logger.info(f"gRPC Client (Auth): Connected to {self.target}")

    async def validate_key(self, api_key:str) -> auth_pb2.ValidateKeyResponse :
        """Validates API KEY with Auth service with gRPC"""
        try:
            request:auth_pb2.ValidateKeyRequest = auth_pb2.ValidateKeyRequest(api_key=api_key)
            response = await self.stub.ValidateKey(request)
            return response
        except RpcError as e:
            logger.warning(f"gRPC Client (Auth)| ERROR : {e.details()} |Code : {e.code()}",exc_info=True)

            if e.code() == grpc.StatusCode.UNAUTHENTICATED :
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail= e.details()
                )
            
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail= e.details()
                )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal authentication error")
        
        except Exception as e:
            logger.error(f"gRPC Client (Auth) | Some Error Occured: {str(e).lower()}",exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error"
            )
        

    async def close(self):
        """Gracefully close connection during shutdown """
        await self.channel.close()
        
        

