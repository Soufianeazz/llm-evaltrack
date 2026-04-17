from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes.ingest import router as ingest_router
from api.routes.dashboard import router as dashboard_router
from api.routes.alerts import router as alerts_router
from api.routes.debug import router as debug_router
from api.routes.compliance import router as compliance_router
from api.routes.traces import router as traces_router
from api.routes.billing import router as billing_router
from api.routes.waitlist import router as waitlist_router
from pipeline.worker import start_worker, stop_worker
from storage.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await start_worker()
    yield
    await stop_worker()


app = FastAPI(title="BugSpy", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(dashboard_router)
app.include_router(alerts_router)
app.include_router(debug_router)
app.include_router(compliance_router)
app.include_router(traces_router)
app.include_router(billing_router)
app.include_router(waitlist_router)

# Serve the static dashboard
app.mount("/", StaticFiles(directory="dashboard", html=True), name="dashboard")
