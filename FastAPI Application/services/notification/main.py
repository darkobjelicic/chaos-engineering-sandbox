import os
import asyncio
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import aio_pika
import traceback
import logging
from pythonjsonlogger import jsonlogger

# JSON logging setup
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger = logging.getLogger("notification")
logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler()
fmt = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s')
handler.setFormatter(fmt)
logger.addHandler(handler)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

app = FastAPI(title="Notification Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global za RabbitMQ
rabbitmq_connection = None
rabbitmq_channel = None


async def init_rabbitmq():
    """Inicijalizuje RabbitMQ konekciju sa retry logikom"""
    global rabbitmq_connection, rabbitmq_channel
    max_retries = 5
    
    for attempt in range(max_retries):
        try:
            rabbitmq_connection = await aio_pika.connect_robust(RABBITMQ_URL)
            rabbitmq_channel = await rabbitmq_connection.channel()
            logger.info("✓ Notification service: RabbitMQ connected")
            return True
        except Exception as e:
            logger.warning(f"RabbitMQ connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                logger.error("✗ Notification service: RabbitMQ connection failed after retries")
                return False


async def consume_order_events():
    """Konzumira order.created event-e - sa aio-pika robust consumer loop-om"""
    logger.info("🎯 Notification consumer starting...")
    
    retry_count = 0
    max_retries = 5
    
    while True:
        try:
            if not rabbitmq_channel:
                print("⚠ RabbitMQ nije dostupan, čekam...")
                await asyncio.sleep(5)
                continue
            
            # Pravi exchange i queue (samo prvi put ili nakon greške)
            if retry_count == 0:
                logger.info("📦 Notification: Setting up exchange and queue...")
            
            exchange = await rabbitmq_channel.declare_exchange(
                "orders.events",
                aio_pika.ExchangeType.FANOUT,
                durable=True
            )
            
            queue = await rabbitmq_channel.declare_queue(
                "notification.orders",
                durable=True
            )
            
            await queue.bind(exchange)
            
            # Sapostavi QoS - prefetch samo 1 poruku za obrada
            await rabbitmq_channel.set_qos(prefetch_count=1)
            
            logger.info("✓ Notification service: Listening for order.created events...")
            retry_count = 0  # Reset retry counter na uspešnu konekciju
            
            # Budi-se svaki put kada ima nove poruke (ack enabled)
            async with queue.iterator(no_ack=False) as queue_iter:
                async for message in queue_iter:
                    # Read raw message body
                    try:
                        raw = message.body.decode()
                    except Exception:
                        raw = str(message.body)
                    # Debug-level metadata (won't show at INFO)
                    try:
                        delivery = getattr(message, "delivery_tag", None)
                        rkey = getattr(message, "routing_key", None)
                        ctype = getattr(message, "content_type", None)
                        headers = getattr(message, "headers", None)
                        task = asyncio.current_task()
                        logger.debug(f"raw message received: {raw}")
                        logger.debug(
                            "delivery_tag=%s routing_key=%s content_type=%s headers=%s task=%s",
                            delivery,
                            rkey,
                            ctype,
                            headers,
                            task,
                        )
                    except Exception:
                        logger.debug(f"raw message received (no extra meta): {raw}")

                    async with message.process():
                        try:
                            event_data = json.loads(raw)
                            if event_data.get("event") == "order.created":
                                order_id = event_data.get("order_id")
                                book_id = event_data.get("book_id")
                                user_id = event_data.get("user_id")
                                quantity = event_data.get("quantity")

                                # Send notification (here: log)
                                logger.info(f"📧 NOTIFICATION: Order #{order_id} created by user {user_id}")
                                logger.info(f"   └─ Book ID: {book_id}, Quantity: {quantity}")
                        except Exception as e:
                            logger.exception("Error processing event: %s", e)
            
        except Exception as e:
            logger.exception("Notification consumer error: %s", e)
            retry_count += 1
            wait_time = min(5 * (2 ** retry_count), 30)
            logger.warning(f"⏸ Retrying in {wait_time}s ({retry_count}/{max_retries})...")
            await asyncio.sleep(wait_time)
            
            if retry_count >= max_retries:
                logger.error("✗ Max retries reached, stopping consumer")
                break


# Global flags
rabbitmq_initialized = False
consumer_running = False


@app.get("/health")
def health():
    return {"status": "ok", "service": "notification"}


@app.get("/notify")
async def notify_status():
    """Prikazuje status i inicijalizuje RabbitMQ ako nije inicijalizovan"""
    global rabbitmq_initialized, consumer_running
    
    if not rabbitmq_initialized:
        try:
            logger.info("🔧 Initializing RabbitMQ in notification service...")
            await init_rabbitmq()
            rabbitmq_initialized = True
            consumer_running = True
            logger.info("✓ Starting consumer task...")
            asyncio.create_task(consume_order_events())
            await asyncio.sleep(0.5)
            logger.info("✓ Consumer task created")
        except Exception as e:
            logger.exception("RabbitMQ init failed: %s", e)
            return {"status": "error", "message": str(e)}
    
    return {"status": "ok", "service": "notification", "rabbitmq": "connected" if rabbitmq_initialized else "not_connected"}


@app.on_event("startup")
async def startup():
    # Auto-initialize RabbitMQ and start the consumer at service startup
    logger.info("✓ Notification service started")
    try:
        logger.info("🔧 Auto-initializing RabbitMQ in notification service...")
        ok = await init_rabbitmq()
        if ok:
            global rabbitmq_initialized, consumer_running
            rabbitmq_initialized = True
            consumer_running = True
            logger.info("✓ Starting consumer task (startup)...")
            asyncio.create_task(consume_order_events())
            await asyncio.sleep(0.1)
            logger.info("✓ Consumer task started (startup)")
        else:
            logger.warning("⚠ RabbitMQ init failed at startup; consumer not started")
    except Exception as e:
        logger.exception("Startup RabbitMQ init error: %s", e)

