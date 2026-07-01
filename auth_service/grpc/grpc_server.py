
import grpc.aio
import grpc
import asyncio
import signal
from grpc_health.v1 import health,health_pb2_grpc
from auth_service.grpc.generated import auth_pb2_grpc
from auth_service.grpc.grpc_servicer import AuthService
from shared.logger import get_logger

logger = get_logger(__name__)


async def shutdown(server:grpc.aio.Server):
    logger.info("Shutting down gRPC server")
    await server.stop(grace=5)
    logger.info("gRPC server stopped")


async def server():
    server = grpc.aio.server(
        options=[
            ("grpc.keepalive_time_ms", 10000),
            ("grpc.keepalive_timeout_ms", 5000),
            ("grpc.keepalive_permit_without_calls", True),
            ("grpc.max_connection_idle_ms", 30000),
        ]
    )
    auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthService(), server)

    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer,server)

    server.add_insecure_port("[::]:50051")

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM,signal.SIGINT):
        loop.add_signal_handler(sig,    lambda: asyncio.create_task(shutdown(server)))
    await server.start()
    logger.info("Auth gRPC server started on port 50051")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(server())
