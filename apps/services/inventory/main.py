import os
import time
import asyncio
import json
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Field, Session, create_engine, select
import aio_pika
import logging
from pythonjsonlogger import jsonlogger

# JSON logging setup
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger = logging.getLogger("inventory")
logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler()
fmt = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s')
handler.setFormatter(fmt)
logger.addHandler(handler)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres-inventory:5432/inventory_db")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

engine = create_engine(DATABASE_URL, echo=False)

# Global za RabbitMQ
rabbitmq_connection = None
rabbitmq_channel = None


class Inventory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    book_id: int = Field(index=True)
    quantity: int


app = FastAPI(title="Inventory Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Flag za RabbitMQ inicijalizaciju
rabbitmq_initialized = False
consumer_running = False


async def init_rabbitmq():
    """Inicijalizuje RabbitMQ konekciju sa retry logikom"""
    global rabbitmq_connection, rabbitmq_channel
    max_retries = 20

    for attempt in range(max_retries):
        try:
            rabbitmq_connection = await aio_pika.connect_robust(RABBITMQ_URL)
            rabbitmq_channel = await rabbitmq_connection.channel()
            logger.info("✓ Inventory service: RabbitMQ connected")
            return True
        except Exception as e:
            wait = min(2 ** attempt, 30)
            logger.warning(
                f"RabbitMQ connection attempt {attempt + 1}/{max_retries} failed: {e}; retrying in {wait}s"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(wait)
            else:
                logger.error("✗ Inventory service: RabbitMQ connection failed after retries")
                return False


async def consume_order_events():
    """Konzumira order.created event-e i smanjuje zalihe - sa aio-pika robust consumer loop-om"""
    logger.info("🎯 Inventory consumer starting...")
    
    retry_count = 0
    max_retries = 5
    
    while True:
        try:
            if not rabbitmq_channel:
                logger.warning("⚠ RabbitMQ nije dostupan, čekam...")
                await asyncio.sleep(5)
                continue
            
            # Pravi exchange i queue (samo prvi put ili nakon greške)
            if retry_count == 0:
                logger.info("📦 Inventory: Setting up exchange and queue...")
            
            exchange = await rabbitmq_channel.declare_exchange(
                "orders.events",
                aio_pika.ExchangeType.FANOUT,
                durable=True
            )
            
            queue = await rabbitmq_channel.declare_queue(
                "inventory.orders",
                durable=True
            )
            
            await queue.bind(exchange)
            
            # Sapostavi QoS - prefetch samo 1 poruku za obrada
            await rabbitmq_channel.set_qos(prefetch_count=1)
            
            logger.info("✓ Inventory service: Listening for order.created events...")
            retry_count = 0  # Reset retry counter na uspešnu konekciju
            
            # Budi-se svaki put kada ima nove poruke
            async with queue.iterator(no_ack=False) as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        try:
                            event_data = json.loads(message.body.decode())
                            if event_data.get("event") == "order.created":
                                book_id = event_data.get("book_id")
                                quantity = event_data.get("quantity")
                                order_id = event_data.get("order_id")
                                
                                # Smanj zalihe u DB-u
                                with Session(engine) as session:
                                    inv = session.exec(
                                        select(Inventory).where(Inventory.book_id == book_id)
                                    ).first()
                                    
                                    if inv and inv.quantity >= quantity:
                                        inv.quantity -= quantity
                                        session.add(inv)
                                        session.commit()
                                        logger.info(f"✓ Inventory updated: book_id={book_id}, new_qty={inv.quantity} (order_id={order_id})")
                                    else:
                                        logger.warning(f"✗ Insufficient inventory for book_id={book_id}")
                        except Exception as e:
                            logger.exception("✗ Error processing event: %s", e)
            
        except Exception as e:
            logger.exception("✗ Inventory consumer error: %s", e)
            retry_count += 1
            wait_time = min(5 * (2 ** retry_count), 30)
            logger.warning(f"⏸ Retrying in {wait_time}s ({retry_count}/{max_retries})...")
            await asyncio.sleep(wait_time)
            
            if retry_count >= max_retries:
                logger.error("✗ Max retries reached, stopping consumer")
                break
                
        except Exception as e:
            logger.exception("✗ Inventory consumer error: %s", e)
            logger.warning("⏸ Restarting consumer in 5 seconds...")
            await asyncio.sleep(5)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


@app.on_event("startup")
async def startup():
    # Initialize DB (same logic as before)
    max_retries = 5
    for attempt in range(max_retries):
        try:
            create_db_and_tables()
            logger.info("✓ Inventory DB initialized")
            break
        except Exception as e:
            logger.warning(f"DB connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise

    # seed test podatke
    try:
        with Session(engine) as session:
            existing = session.exec(select(Inventory)).all()
            if len(existing) == 0:
                test_items = [
                    Inventory(book_id=1, quantity=50),
                    Inventory(book_id=2, quantity=30),
                    Inventory(book_id=3, quantity=45),
                    Inventory(book_id=4, quantity=20),
                ]
                for item in test_items:
                    session.add(item)
                session.commit()
                logger.info(f"✓ Ubačeno {len(test_items)} test stavki zaliha")
            else:
                logger.info(f"✓ {len(existing)} stavki zaliha već postoji")
    except Exception as e:
        logger.warning(f"Seed warning: {e}")

    # Auto-initialize RabbitMQ and start consumer at startup
    try:
        logger.info("🔧 Auto-initializing RabbitMQ in inventory service...")
        ok = await init_rabbitmq()
        if ok:
            global rabbitmq_initialized, consumer_running
            rabbitmq_initialized = True
            consumer_running = True
            logger.info("✓ RabbitMQ initialized, starting consumer (startup)...")
            task = asyncio.create_task(consume_order_events())
            logger.info(f"✓ Consumer task created (task={task})")
            await asyncio.sleep(0.1)
        else:
            logger.warning("⚠ RabbitMQ init failed at startup; consumer not started")
    except Exception as e:
        logger.exception("✗ RabbitMQ startup init failed: %s", e)

@app.get("/health")
def health():
    return {"status": "ok", "service": "inventory"}


@app.get("/inventory/{book_id}")
def get_inventory(book_id: int, session: Session = Depends(get_session)):
    inv = session.exec(select(Inventory).where(Inventory.book_id == book_id)).first()
    if not inv:
        return {"book_id": book_id, "quantity": 0}
    return inv


@app.get("/inventory", response_model=List[Inventory])
async def list_inventory(session: Session = Depends(get_session)):
    """Lista sve zalihe i inicijalizuje RabbitMQ ako nije inicijalizovan"""
    global rabbitmq_initialized, consumer_running
    
    # Lazy inicijalizacija RabbitMQ i consumer-a
    if not rabbitmq_initialized:
        try:
            logger.info("🔧 Initializing RabbitMQ...")
            await init_rabbitmq()
            rabbitmq_initialized = True
            logger.info("✓ RabbitMQ initialized, starting consumer...")
            consumer_running = True
            # Pokreni consumer kao background task
            task = asyncio.create_task(consume_order_events())
            logger.info(f"✓ Consumer task created (task={task})")
            # Čekaj malo da se consumer priključi
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.exception("✗ RabbitMQ init failed: %s", e)
    
    items = session.exec(select(Inventory)).all()
    return items
@app.post("/inventory")
def create_inventory(book_id: int, quantity: int, session: Session = Depends(get_session)):
    inv = Inventory(book_id=book_id, quantity=quantity)
    session.add(inv)
    session.commit()
    session.refresh(inv)
    return inv


@app.put("/inventory/{book_id}")
def update_inventory(book_id: int, quantity: int, session: Session = Depends(get_session)):
    inv = session.exec(select(Inventory).where(Inventory.book_id == book_id)).first()
    if not inv:
        inv = Inventory(book_id=book_id, quantity=quantity)
        session.add(inv)
    else:
        inv.quantity = quantity
        session.add(inv)
    session.commit()
    session.refresh(inv)
    return inv
