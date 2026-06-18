import os
import clamd
from shared.logger import get_logger
from tempfile import SpooledTemporaryFile
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = get_logger(__name__)


class ClamAVClient:
    def __init__(self):
        self.host = os.getenv("CLAMAV_HOST", "localhost")
        self.port = os.getenv("CLAMAV_PORT", 3310)
        self.connection = None

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        before_sleep=before_sleep_log(
            logger, 30
        ),  # Auto-logs a warning before it sleeps/retries
        reraise=True,
    )
    async def connect(self, retries: int = 5, delay: int = 5):
        try:
            self.connection = clamd.ClamdNetworkSocket(self.host, self.port, timeout=30)
            await asyncio.to_thread(self.connection.ping)
            logger.info("ClamAV connection success")
            return
        except Exception as e:
            logger.error(f"ClamAV connection failed: {str(e).lower()}")
            raise e

    @retry(
        stop=stop_after_attempt(4),  # Give up after 4 total attempts
        wait=wait_exponential(
            multiplier=1, min=1, max=8
        ),  # Wait 1s, 2s, 4s, 8s between tries
        retry=retry_if_exception_type(
            clamd.ConnectionError
        ),  # ONLY retry on network drops
        before_sleep=before_sleep_log(
            logger, 30
        ),  # Auto-logs a warning before it sleeps/retries
        reraise=True,  # If it fails 4 times, pass the error up to RabbitMQ
    )
    async def scan(self, spoolfile: SpooledTemporaryFile) -> dict:
        try:
            if not self.connection:
                raise RuntimeError("ClamAV not connected. Call connect() first.")
            spoolfile.seek(0)
            scan_res = await asyncio.to_thread(self.connection.instream, spoolfile)
            return scan_res
        except Exception as e:
            logger.error(f"Scan failed: {str(e).lower()}")
            raise e
