import os
import json
import time
from telemetry import setup_telemetry

setup_telemetry()
import asyncio
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Field, Session, create_engine, select
import aio_pika
import httpx
from fastapi import Header, Request
import logging
from pythonjsonlogger import jsonlogger

# JSON logging setup
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger = logging.getLogger("order")
logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler()
fmt = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
handler.setFormatter(fmt)
logger.addHandler(handler)

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@postgres-order:5432/order_db"
)
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")

engine = create_engine(DATABASE_URL, echo=False)

# Global za RabbitMQ konekciju
rabbitmq_connection = None
rabbitmq_channel = None


class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    book_id: int
    quantity: int
    status: str = "created"


class OrderCreate(SQLModel):
    book_id: int
    quantity: int


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


async def init_rabbitmq():
    """Inicijalizuje RabbitMQ konekciju sa retry logikom"""
    global rabbitmq_connection, rabbitmq_channel
    max_retries = 20

    for attempt in range(max_retries):
        try:
            rabbitmq_connection = await aio_pika.connect_robust(RABBITMQ_URL)
            rabbitmq_channel = await rabbitmq_connection.channel()
            logger.info("✓ Order service: RabbitMQ connected")
            return True
        except Exception as e:
            wait = min(2**attempt, 30)
            logger.warning(
                f"RabbitMQ connection attempt {attempt + 1}/{max_retries} failed: {e}; retrying in {wait}s"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "✗ Order service: RabbitMQ connection failed after retries"
                )
                return False


async def publish_order_event(order_id: int, user_id: int, book_id: int, quantity: int):
    """Publlikuje order.created event na RabbitMQ"""
    if not rabbitmq_channel:
        logger.warning("⚠ RabbitMQ nije dostupan, event se ne može objaviti")
        return

    try:
        exchange = await rabbitmq_channel.declare_exchange(
            "orders.events", aio_pika.ExchangeType.FANOUT, durable=True
        )

        event_data = {
            "event": "order.created",
            "order_id": order_id,
            "user_id": user_id,
            "book_id": book_id,
            "quantity": quantity,
        }

        message = aio_pika.Message(
            body=json.dumps(event_data).encode(), content_type="application/json"
        )

        await exchange.publish(message, routing_key="")
        logger.info(
            f"✓ Event published: order.created (order_id={order_id}, book_id={book_id}, qty={quantity})"
        )
    except Exception as e:
        logger.exception("✗ Failed to publish event: %s", e)


app = FastAPI(title="Order Service")

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

FastAPIInstrumentor.instrument_app(app)
SQLAlchemyInstrumentor().instrument(engine=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Flag za RabbitMQ inicijalizaciju
rabbitmq_initialized = False


@app.on_event("startup")
def on_startup():
    """Inicijalizuj DB na startup-u"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            create_db_and_tables()
            logger.info("✓ Order DB initialized")
            break
        except Exception as e:
            logger.warning(
                f"DB connection attempt {attempt + 1}/{max_retries} failed: {e}"
            )
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise


@app.get("/health")
def health():
    return {"status": "ok", "service": "order"}


async def _get_current_user_from_header(authorization: Optional[str] = Header(None)):
    """Call auth service /me to validate token and return current user dict or raise 401"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{AUTH_SERVICE_URL}/me", headers={"Authorization": authorization}
            )
        if r.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        return r.json()
    except httpx.RequestError as e:
        logger.exception("Error contacting auth service: %s", e)
        raise HTTPException(status_code=503, detail="Auth service unavailable")


@app.get("/orders", response_model=List[Order])
async def list_orders(
    current_user: dict = Depends(_get_current_user_from_header),
    session: Session = Depends(get_session),
):
    # Return only orders for the authenticated user
    orders = session.exec(
        select(Order).where(Order.user_id == current_user.get("id"))
    ).all()
    return orders


@app.get("/orders/{order_id}", response_model=Order)
async def get_order(
    order_id: int,
    current_user: dict = Depends(_get_current_user_from_header),
    session: Session = Depends(get_session),
):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Narudžbina nije pronađena")
    if order.user_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Nemate pristup ovoj narudžbini")
    return order


@app.on_event("startup")
async def rabbitmq_startup_init():
    """Try to initialize RabbitMQ at startup to avoid lazy init during request handling."""
    global rabbitmq_initialized
    try:
        logger.info("🔧 Order service: Auto-initializing RabbitMQ at startup...")
        ok = await init_rabbitmq()
        if ok:
            rabbitmq_initialized = True
            logger.info("✓ Order service: RabbitMQ initialized at startup")
        else:
            logger.warning(
                "⚠ Order service: RabbitMQ init failed at startup; will retry lazily on demand"
            )
    except Exception as e:
        logger.exception("Order service startup RabbitMQ init error: %s", e)


@app.post("/orders", response_model=Order)
async def create_order(
    order_data: OrderCreate, request: Request, session: Session = Depends(get_session)
):
    """Kreira novu narudžbinu i publlikuje event"""
    global rabbitmq_initialized

    # Inicijalizuj RabbitMQ pri prvom zahtevу
    if not rabbitmq_initialized:
        try:
            await init_rabbitmq()
            rabbitmq_initialized = True
        except Exception as e:
            logger.exception("⚠ RabbitMQ init failed: %s", e)

    # Validate token and ensure user_id matches authenticated user
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    current_user = await _get_current_user_from_header(auth_header)
    # Enforce server-side: always set the order's user_id to the authenticated user's id
    payload = order_data.dict()
    payload["user_id"] = current_user.get("id")

    order = Order(**payload)
    session.add(order)
    session.commit()
    session.refresh(order)

    # Publlikuj event
    try:
        await publish_order_event(
            order_id=order.id,
            user_id=order.user_id,
            book_id=order.book_id,
            quantity=order.quantity,
        )
    except Exception as e:
        logger.exception("⚠ Could not publish event: %s", e)

    return order
