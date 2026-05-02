from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

MAX_BODY_BYTES = 256 * 1024  # 256 KB


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body exceeds {MAX_BODY_BYTES} bytes"},
            )
        return await call_next(request)

from api.limiter import limiter
from api.routes.ingest import router as ingest_router
from api.routes.dashboard import router as dashboard_router
from api.routes.health import router as health_router
from api.routes.alerts import router as alerts_router
from api.routes.debug import router as debug_router
from api.routes.compliance import router as compliance_router
from api.routes.traces import router as traces_router
from api.routes.billing import router as billing_router
from api.routes.waitlist import router as waitlist_router
from api.routes.demo import router as demo_router
from api.routes.admin import router as admin_router, seed_demo_on_startup
from pipeline.worker import start_worker, stop_worker
from storage.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_demo_on_startup()
    await start_worker()
    yield
    await stop_worker()


app = FastAPI(title="LLM Observability MVP", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(BodySizeLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'"
    )
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if response.headers.get("content-type", "").startswith("application/json"):
        response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(ingest_router)
app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(alerts_router)
app.include_router(debug_router)
app.include_router(compliance_router)
app.include_router(traces_router)
app.include_router(billing_router)
app.include_router(waitlist_router)
app.include_router(demo_router)
app.include_router(admin_router)


# Public entry point: landing page. Dashboard moves to /dashboard.
@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("dashboard/landing.html")


@app.get("/dashboard", include_in_schema=False)
async def dashboard_page():
    return FileResponse("dashboard/index.html")


# Clean-URL SEO comparison pages (no .html suffix — better for sharing + rankings)
@app.get("/vs/langsmith", include_in_schema=False)
async def vs_langsmith():
    return FileResponse("dashboard/vs/langsmith.html")


@app.get("/vs/langfuse", include_in_schema=False)
async def vs_langfuse():
    return FileResponse("dashboard/vs/langfuse.html")


@app.get("/vs/helicone", include_in_schema=False)
async def vs_helicone():
    return FileResponse("dashboard/vs/helicone.html")


@app.get("/alternatives/datadog-llm", include_in_schema=False)
async def alt_datadog_llm():
    return FileResponse("dashboard/alternatives/datadog-llm.html")


@app.get("/impressum", include_in_schema=False)
async def impressum():
    return FileResponse("dashboard/impressum.html")


@app.get("/datenschutz", include_in_schema=False)
async def datenschutz():
    return FileResponse("dashboard/datenschutz.html")


@app.get("/nutzungsbedingungen", include_in_schema=False)
async def nutzungsbedingungen():
    return FileResponse("dashboard/nutzungsbedingungen.html")


@app.get("/success", include_in_schema=False)
async def success():
    return FileResponse("dashboard/success.html")


@app.get("/book-demo", include_in_schema=False)
async def book_demo():
    return FileResponse("dashboard/book-demo.html")


@app.get("/case-study", include_in_schema=False)
async def case_study():
    return FileResponse("dashboard/case_study.html")


@app.get("/security", include_in_schema=False)
async def security_page():
    return FileResponse("dashboard/security.html")


@app.get("/subprocessors", include_in_schema=False)
async def subprocessors_page():
    return FileResponse("dashboard/subprocessors.html")


@app.get("/enterprise", include_in_schema=False)
async def enterprise_page():
    return FileResponse("dashboard/enterprise.html")


@app.get("/security-questionnaire", include_in_schema=False)
async def security_questionnaire_page():
    return FileResponse("dashboard/security-questionnaire.html")


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap():
    return FileResponse("dashboard/sitemap.xml", media_type="application/xml")


@app.get("/robots.txt", include_in_schema=False)
async def robots():
    return FileResponse("dashboard/robots.txt", media_type="text/plain")


# Serve all other static files (debug.html, traces.html, compliance.html, assets)
app.mount("/", StaticFiles(directory="dashboard"), name="dashboard")
