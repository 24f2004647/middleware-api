from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from collections import defaultdict, deque
import time
import uuid

EMAIL = "24f2004647@ds.study.iitm.ac.in"

ALLOWED_ORIGIN = "https://.*"
RATE_LIMIT = 13
WINDOW_SECONDS = 10

app = FastAPI()

# Allow assigned origin + exam origin(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        ALLOWED_ORIGIN,
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    # Don't rate-limit preflight requests
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
                status_code=429
            )

        bucket.append(now)

    return await call_next(request)


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id
    }


@app.options("/ping")
async def ping_options():
    return Response(status_code=200)


@app.get("/")
async def root():
    return {"status": "ok"}
