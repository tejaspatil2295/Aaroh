import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import get_settings
from .db import SessionLocal
from .routers import ai, auth, dashboard, finance, fitness, journal, learning, planner, users, work_side

log = logging.getLogger("aaroh")
settings = get_settings()

app = FastAPI(
    title="AAROH API",
    version="1.0.0",
    description="Personal Life OS. All endpoints except /auth/* require `Authorization: Bearer <access token>`.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.url.path.startswith("/api/v1"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


API = "/api/v1"
app.include_router(auth.router, prefix=API)
app.include_router(users.router, prefix=API)
app.include_router(dashboard.router, prefix=API)
app.include_router(ai.router, prefix=API)
for module in (planner, finance, journal, learning, fitness, work_side):
    for r in module.routers:
        app.include_router(r, prefix=API)


@app.get("/api/health", tags=["meta"])
def health():
    with SessionLocal() as db:
        db.execute(text("select 1"))
    return {"status": "ok"}
