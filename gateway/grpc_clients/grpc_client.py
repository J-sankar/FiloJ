import grpc.aio
from grpc import RpcError
from gateway.generated import auth_pb2_grpc,auth_pb2
from gateway.core.config import SERVICES
from shared.logger import get_logger
import asyncio

logger = get_logger(__name__)

auth_url = SERVICES.get("auth")
async def run(api_key:str):
    async with grpc.aio.insecure_channel("localhost:50051") as channel:
        stub = auth_pb2_grpc.AuthServiceStub(channel)
        try:
            response = await stub.ValidateKey(auth_pb2.ValidateKeyRequest(api_key="FiloJ_jayan4_jT8KQ2omAAq8GpY_vyjFInVz5h_ClnogNEzuk9hsA0w"))
            logger.info(f"RESULT: {response}")
        except RpcError as e :
            logger.exception(f"Grpc Error: {e.details()}")
        
        except Exception :
            logger.exception("Some error occured")


if __name__ == "__main__":
    asyncio.run(run("api_key"))
