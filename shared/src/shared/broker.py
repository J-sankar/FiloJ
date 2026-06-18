from aio_pika import ExchangeType, connect_robust,Message
from aio_pika.abc import AbstractQueue,AbstractExchange
from shared.logger import get_logger
import os
import asyncio
import json


logger = get_logger(__name__)


class BrokerClient:
    """The message broker client for data transmission"""
    def __init__(self):
        self.rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
        self.connection = None
        self.channel = None
        self.prefetch_count = None
        self.exchanges : dict[str, AbstractExchange] = {} 

    async def connect(self,prefetch_count: int = 1):
        """Connect with rabbitmq client,create a channel and setup exchanges"""
        self.prefetch_count = prefetch_count
        self.connection = await connect_robust(self.rabbitmq_url,reconnect_interval=5,timeout=10,fail_fast = False)
        self.connection.reconnect_callbacks.add(self._on_reconnect,)
        logger.info("Rabbitmq connection success")
        self.channel = await self.connection.channel()
        await self.channel.set_qos(self.prefetch_count)
        await self.setup_exchanges()
            
    async def setup_exchanges(self):
        """Declare the exchanges required"""
        self.exchanges["work.tasks"] = await self.channel.declare_exchange(
            name="work.tasks",
            type=ExchangeType.TOPIC,
            durable=True
        ) 

        self.exchanges["system.events"] = await self.channel.declare_exchange(
            name="system.events",
            type=ExchangeType.TOPIC,
            durable=True
        )
        self.exchanges["dlx.exchange"] = await self.channel.declare_exchange("dlx.exchange", type="topic", durable=True)
        logger.debug(f"Exchange setup: Success | found exchanges = {len(self.exchanges)}")


    async def get_configured_queue(self, exchange_name:str, routing_key:str, queue_name:str ) ->AbstractQueue : 
        """
        Used by workers to prepare their listener.
        Creates queue and binds it to the required exchange
        """
        if not self.channel:
            logger.error("BrokerClient not connected")
            raise RuntimeError("BrokerClient is not connected. Call connect() first.")
        if exchange_name not in self.exchanges:
            logger.error(f"Exchange {exchange_name} is not set up.")
            raise KeyError(f"Exchange '{exchange_name}' is not set up.")
         
        exchange = self.exchanges[exchange_name]

        queue = await self.channel.declare_queue(
            queue_name,
            durable= True,
            arguments={
                "x-queue-type": "quorum",
                "x-dead-letter-exchange": "dlx.exchange", 
                "x-dead-letter-routing-key": "failed.scan",
                "x-delivery-limit": 3
            }
        )
        await queue.bind(exchange=exchange,routing_key=routing_key)
        logger.info(f"queue {queue_name} setup and binds exchange {exchange_name} | routing key: {routing_key}")
        return queue

    async def _on_reconnect(self, connection):
        """Re-create channel and exchanges after a reconnect"""
        logger.warning("RabbitMQ reconnected — rebuilding channel and exchanges")
        self.channel = await connection.channel()
        await self.channel.set_qos(prefetch_count=self.prefetch_count)  
        self.exchanges.clear()
        await self.setup_exchanges()

    async def publish(self, exchange_name:str, routing_key: str, payload:dict):
        """Publish messages to exchange specified"""
        if not self.channel:
            logger.error("BrokerClient not connected")
            raise RuntimeError("BrokerClient is not connected. Call connect() first.")
        if exchange_name not in self.exchanges:
            logger.error(f"Exchange {exchange_name} is not set up.")
            raise KeyError(f"Exchange '{exchange_name}' is not set up.")

        message_body = json.dumps(payload).encode() 
        exchange = self.exchanges[exchange_name]
        
        await exchange.publish(
            message= Message(
                body=message_body,
                content_type="application/json"
            ),
            routing_key=routing_key
        )

    async def close(self):
        """Safely close the connection"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()

async def test_connection():
    broker = BrokerClient()
    await broker.connect(prefetch_count=2)
    await broker.get_configured_queue("work.tasks","task.#", "scanner-queue")
    await broker.publish("work.tasks", "task.image", {"job_id": 23456})


if __name__ == "__main__":
    asyncio.run(test_connection())