"""
Main FastAPI Application Entrypoint.
Sets up CORS, Correlation ID tracking, API routers, and PWA static file serving.
"""
import time
import uuid
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.src.core.config import settings
from backend.src.core.logger import logger, set_correlation_id
from backend.src.presentation.api_v1 import router as api_v1_router

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Hands-free Vietnamese Motorbike Traffic Navigation and Safety Assistant",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Correlation ID and Request Timing Middleware
@app.middleware("http")
async def correlation_and_logging_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4())[:8])
    set_correlation_id(correlation_id)

    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)

    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Response-Time-MS"] = str(duration_ms)

    # Don't clutter logs with static asset queries
    if not request.url.path.startswith("/static") and not request.url.path.endswith((".js", ".css", ".png", ".ico")):
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)"
        )

    return response


# Include API v1 Router
app.include_router(api_v1_router)

# Mount Frontend Static Files
frontend_dir = Path(__file__).resolve().parent.parent.parent.parent / "frontend"

if frontend_dir.exists():
    static_dir = frontend_dir / "static"
    locales_dir = frontend_dir / "locales"

    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    if locales_dir.exists():
        app.mount("/locales", StaticFiles(directory=str(locales_dir)), name="locales")

    @app.get("/", summary="Serve PWA main page")
    async def serve_index():
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Traffic Assistant API is running"}

    @app.get("/training.html", summary="Serve dedicated Model Training page")
    async def serve_training():
        train_file = static_dir / "training.html"
        if train_file.exists():
            return FileResponse(str(train_file))
        return FileResponse(str(frontend_dir / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.src.presentation.main:app", host=settings.host, port=settings.app_port, reload=settings.debug)
