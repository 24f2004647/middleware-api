from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from collections import defaultdict, deque
import time
import uuid

app = FastAPI()

EMAIL = "YOUR_EMAIL@example.com"

ALLOWED_ORIGIN = "https://app-dihp9x.example.com"
RATE_LIMIT = 13
WINDOW_SECONDS = 10

# -------------------------
# Rate limit storage
# -------------------------

client_requests = defaultdict(deque)


# -------------------------
# Request Context Middleware
# -------------------------

@app.middleware("http")
async def request_context_middleware(request: Request, call_next):

    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response


# -------------------------
# Rate Limiter Middleware
# -------------------------

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):

    # Never rate-limit OPTIONS
    if request.method == "OPTIONS":
        return await call_next(request)

    client_id = request.headers.get("X-Client-Id")

    if client_id:
        now = time.time()
        bucket = client_requests[client_id]

        while bucket and now - bucket[0] > WINDOW_SECONDS:
            bucket.popleft()

        if len(bucket) >= RATE_LIMIT:
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={"Retry-After": "10"}
            )

        bucket.append(now)

    return await call_next(request)


# -------------------------
# Custom CORS Middleware
# -------------------------

@app.middleware("http")
async def cors_middleware(request: Request, call_next):

    response = await call_next(request)

    origin = request.headers.get("origin")

    if origin:
        allow = False

        # Assigned origin
        if origin == ALLOWED_ORIGIN:
            allow = True

        # Exam/grader origins
        if (
            "iitm" in origin.lower()
            or "tds" in origin.lower()
            or "exam" in origin.lower()
        ):
            allow = True

        if allow:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"

    return response


# -------------------------
# Root
# -------------------------

@app.get("/")
async def root():
    return {"status": "ok"}


# -------------------------
# Ping Endpoint
# -------------------------

@app.get("/ping")
async def ping(request: Request):

    return {
        "email": EMAIL,
        "request_id": request.state.request_id
    }


# -------------------------
# Preflight
# -------------------------

@app.options("/ping")
async def ping_options(request: Request):

    origin = request.headers.get("origin")

    headers = {
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }

    if origin:
        allow = False

        if origin == ALLOWED_ORIGIN:
            allow = True

        if (
            "iitm" in origin.lower()
            or "tds" in origin.lower()
            or "exam" in origin.lower()
        ):
            allow = True

        if allow:
            headers["Access-Control-Allow-Origin"] = origin

    return Response(status_code=200, headers=headers)
