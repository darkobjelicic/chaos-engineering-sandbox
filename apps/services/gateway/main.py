import os
import httpx
import logging
import pybreaker
from telemetry import setup_telemetry

setup_telemetry()
from pythonjsonlogger import jsonlogger
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger = logging.getLogger("gateway")
logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler()
fmt = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
handler.setFormatter(fmt)
logger.addHandler(handler)

BOOK_SERVICE_URL = os.getenv("BOOK_SERVICE_URL", "http://book-service:8000")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://order-service:8000")
INVENTORY_SERVICE_URL = os.getenv(
    "INVENTORY_SERVICE_URL", "http://inventory-service:8000"
)

# Circuit breakers — open after 5 failures, reset after 30s
_listener = pybreaker.CircuitBreakerListener()
book_breaker = pybreaker.CircuitBreaker(
    fail_max=5, reset_timeout=30, name="book-service"
)
auth_breaker = pybreaker.CircuitBreaker(
    fail_max=5, reset_timeout=30, name="auth-service"
)
order_breaker = pybreaker.CircuitBreaker(
    fail_max=5, reset_timeout=30, name="order-service"
)
inventory_breaker = pybreaker.CircuitBreaker(
    fail_max=5, reset_timeout=30, name="inventory-service"
)

TIMEOUT = httpx.Timeout(5.0)

app = FastAPI(title="API Gateway")

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _unavailable(service: str) -> Response:
    logger.warning("circuit_open service=%s", service)
    return Response(
        content=f'{{"error": "{service} unavailable"}}'.encode(),
        status_code=503,
        media_type="application/json",
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}


# ── Book Service ──────────────────────────────────────────────────────────────


@app.get("/books")
async def proxy_list_books():
    try:

        @book_breaker
        async def _call():
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                return await client.get(f"{BOOK_SERVICE_URL}/books")

        r = await _call()
        return Response(
            content=r.content,
            status_code=r.status_code,
            media_type=r.headers.get("content-type"),
        )
    except pybreaker.CircuitBreakerError:
        return _unavailable("book-service")


@app.get("/books/{book_id}")
async def proxy_get_book(book_id: int):
    try:

        @book_breaker
        async def _call():
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                return await client.get(f"{BOOK_SERVICE_URL}/books/{book_id}")

        r = await _call()
        return Response(
            content=r.content,
            status_code=r.status_code,
            media_type=r.headers.get("content-type"),
        )
    except pybreaker.CircuitBreakerError:
        return _unavailable("book-service")


@app.post("/books")
async def proxy_create_book(request: Request):
    body = await request.json()
    try:

        @book_breaker
        async def _call():
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                return await client.post(f"{BOOK_SERVICE_URL}/books", json=body)

        r = await _call()
        return Response(
            content=r.content,
            status_code=r.status_code,
            media_type=r.headers.get("content-type"),
        )
    except pybreaker.CircuitBreakerError:
        return _unavailable("book-service")


# ── Auth Service ──────────────────────────────────────────────────────────────


@app.post("/auth/register")
async def proxy_register(request: Request):
    body = await request.json()
    try:

        @auth_breaker
        async def _call():
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                return await client.post(f"{AUTH_SERVICE_URL}/register", json=body)

        r = await _call()
        return Response(
            content=r.content,
            status_code=r.status_code,
            media_type=r.headers.get("content-type"),
        )
    except pybreaker.CircuitBreakerError:
        return _unavailable("auth-service")


@app.post("/auth/login")
async def proxy_login(request: Request):
    body = await request.form()
    try:

        @auth_breaker
        async def _call():
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                return await client.post(f"{AUTH_SERVICE_URL}/login", data=body)

        r = await _call()
        return Response(
            content=r.content,
            status_code=r.status_code,
            media_type=r.headers.get("content-type"),
        )
    except pybreaker.CircuitBreakerError:
        return _unavailable("auth-service")


@app.get("/auth/me")
async def proxy_me(request: Request):
    token = request.headers.get("Authorization")
    if not token:
        return {"error": "Missing token"}, 401
    try:

        @auth_breaker
        async def _call():
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                return await client.get(
                    f"{AUTH_SERVICE_URL}/me", headers={"Authorization": token}
                )

        r = await _call()
        return Response(
            content=r.content,
            status_code=r.status_code,
            media_type=r.headers.get("content-type"),
        )
    except pybreaker.CircuitBreakerError:
        return _unavailable("auth-service")


# ── Order Service ─────────────────────────────────────────────────────────────


@app.get("/orders")
async def proxy_list_orders(request: Request):
    token = request.headers.get("Authorization")
    headers = {"Authorization": token} if token else None
    try:

        @order_breaker
        async def _call():
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                return await client.get(f"{ORDER_SERVICE_URL}/orders", headers=headers)

        r = await _call()
        return Response(
            content=r.content,
            status_code=r.status_code,
            media_type=r.headers.get("content-type"),
        )
    except pybreaker.CircuitBreakerError:
        return _unavailable("order-service")


@app.post("/orders")
async def proxy_create_order(request: Request):
    body = await request.json()
    token = request.headers.get("Authorization")
    headers = {"Authorization": token} if token else None
    try:

        @order_breaker
        async def _call():
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                return await client.post(
                    f"{ORDER_SERVICE_URL}/orders", json=body, headers=headers
                )

        r = await _call()
        return Response(
            content=r.content,
            status_code=r.status_code,
            media_type=r.headers.get("content-type"),
        )
    except pybreaker.CircuitBreakerError:
        return _unavailable("order-service")


# ── Inventory Service ─────────────────────────────────────────────────────────


@app.get("/inventory")
async def proxy_list_inventory():
    try:

        @inventory_breaker
        async def _call():
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                return await client.get(f"{INVENTORY_SERVICE_URL}/inventory")

        r = await _call()
        return Response(
            content=r.content,
            status_code=r.status_code,
            media_type=r.headers.get("content-type"),
        )
    except pybreaker.CircuitBreakerError:
        return _unavailable("inventory-service")


@app.get("/inventory/{book_id}")
async def proxy_get_inventory(book_id: int):
    try:

        @inventory_breaker
        async def _call():
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                return await client.get(f"{INVENTORY_SERVICE_URL}/inventory/{book_id}")

        r = await _call()
        return Response(
            content=r.content,
            status_code=r.status_code,
            media_type=r.headers.get("content-type"),
        )
    except pybreaker.CircuitBreakerError:
        return _unavailable("inventory-service")
