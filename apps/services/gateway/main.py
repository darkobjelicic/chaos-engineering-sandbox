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

BOOK_SERVICE_URL      = os.getenv("BOOK_SERVICE_URL",      "http://book-service:8000")
AUTH_SERVICE_URL      = os.getenv("AUTH_SERVICE_URL",      "http://auth-service:8000")
ORDER_SERVICE_URL     = os.getenv("ORDER_SERVICE_URL",     "http://order-service:8000")
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://inventory-service:8000")

TIMEOUT = 5.0  # seconds — prevents hanging connections under chaos

book_breaker      = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=30)
auth_breaker      = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=30)
order_breaker     = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=30)
inventory_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=30)

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


def _service_unavailable(service: str) -> Response:
    logger.warning("Circuit breaker OPEN for %s", service)
    return Response(
        content=f'{{"error": "{service} temporarily unavailable"}}',
        status_code=503,
        media_type="application/json",
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}


# ── Book Service ──────────────────────────────────────────────────────────────

@app.get("/books")
async def proxy_list_books():
    logger.info("Proxying GET /books to %s", BOOK_SERVICE_URL)
    try:
        @book_breaker
        def call():
            return httpx.get(f"{BOOK_SERVICE_URL}/books", timeout=TIMEOUT)
        r = call()
    except pybreaker.CircuitBreakerError:
        return _service_unavailable("book-service")
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type"))


@app.get("/books/{book_id}")
async def proxy_get_book(book_id: int):
    logger.info("Proxying GET /books/%s to %s", book_id, BOOK_SERVICE_URL)
    try:
        @book_breaker
        def call():
            return httpx.get(f"{BOOK_SERVICE_URL}/books/{book_id}", timeout=TIMEOUT)
        r = call()
    except pybreaker.CircuitBreakerError:
        return _service_unavailable("book-service")
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type"))


@app.post("/books")
async def proxy_create_book(request: Request):
    body = await request.json()
    logger.info("Proxying POST /books to %s", BOOK_SERVICE_URL)
    try:
        @book_breaker
        def call():
            return httpx.post(f"{BOOK_SERVICE_URL}/books", json=body, timeout=TIMEOUT)
        r = call()
    except pybreaker.CircuitBreakerError:
        return _service_unavailable("book-service")
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type"))


# ── Auth Service ──────────────────────────────────────────────────────────────

@app.post("/auth/register")
async def proxy_register(request: Request):
    body = await request.json()
    logger.info("Proxying POST /auth/register to %s", AUTH_SERVICE_URL)
    try:
        @auth_breaker
        def call():
            return httpx.post(f"{AUTH_SERVICE_URL}/register", json=body, timeout=TIMEOUT)
        r = call()
    except pybreaker.CircuitBreakerError:
        return _service_unavailable("auth-service")
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type"))


@app.post("/auth/login")
async def proxy_login(request: Request):
    body = await request.form()
    logger.info("Proxying POST /auth/login to %s", AUTH_SERVICE_URL)
    try:
        @auth_breaker
        def call():
            return httpx.post(f"{AUTH_SERVICE_URL}/login", data=body, timeout=TIMEOUT)
        r = call()
    except pybreaker.CircuitBreakerError:
        return _service_unavailable("auth-service")
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type"))


@app.get("/auth/me")
async def proxy_me(request: Request):
    token = request.headers.get("Authorization")
    if not token:
        return {"error": "Missing token"}, 401
    logger.info("Proxying GET /auth/me to %s", AUTH_SERVICE_URL)
    try:
        @auth_breaker
        def call():
            return httpx.get(f"{AUTH_SERVICE_URL}/me",
                             headers={"Authorization": token}, timeout=TIMEOUT)
        r = call()
    except pybreaker.CircuitBreakerError:
        return _service_unavailable("auth-service")
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type"))


# ── Order Service ─────────────────────────────────────────────────────────────

@app.get("/orders")
async def proxy_list_orders(request: Request):
    logger.info("Proxying GET /orders to %s", ORDER_SERVICE_URL)
    token = request.headers.get("Authorization")
    headers = {"Authorization": token} if token else {}
    try:
        @order_breaker
        def call():
            return httpx.get(f"{ORDER_SERVICE_URL}/orders",
                             headers=headers, timeout=TIMEOUT)
        r = call()
    except pybreaker.CircuitBreakerError:
        return _service_unavailable("order-service")
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type"))


@app.post("/orders")
async def proxy_create_order(request: Request):
    body = await request.json()
    logger.info("Proxying POST /orders to %s", ORDER_SERVICE_URL)
    token = request.headers.get("Authorization")
    headers = {"Authorization": token} if token else {}
    try:
        @order_breaker
        def call():
            return httpx.post(f"{ORDER_SERVICE_URL}/orders",
                              json=body, headers=headers, timeout=TIMEOUT)
        r = call()
    except pybreaker.CircuitBreakerError:
        return _service_unavailable("order-service")
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type"))


# ── Inventory Service ─────────────────────────────────────────────────────────

@app.get("/inventory")
async def proxy_list_inventory():
    logger.info("Proxying GET /inventory to %s", INVENTORY_SERVICE_URL)
    try:
        @inventory_breaker
        def call():
            return httpx.get(f"{INVENTORY_SERVICE_URL}/inventory", timeout=TIMEOUT)
        r = call()
    except pybreaker.CircuitBreakerError:
        return _service_unavailable("inventory-service")
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type"))


@app.get("/inventory/{book_id}")
async def proxy_get_inventory(book_id: int):
    logger.info("Proxying GET /inventory/%s to %s", book_id, INVENTORY_SERVICE_URL)
    try:
        @inventory_breaker
        def call():
            return httpx.get(f"{INVENTORY_SERVICE_URL}/inventory/{book_id}",
                             timeout=TIMEOUT)
        r = call()
    except pybreaker.CircuitBreakerError:
        return _service_unavailable("inventory-service")
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type"))
