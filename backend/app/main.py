import os
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.db import abandon_unfinished_runs, init_schema
from app.event_log.routes import router as event_log_router
from app.experiment.engine import Engine
from app.messaging.service import MessageService
from app.realtime.hub import Hub
from app.realtime.routes import router as realtime_router
from app.session.config import load_config
from app.session.routes import router as session_router
from app.session.service import SeatService

DATABASE_URL = os.environ["DATABASE_URL"]
CONFIG_PATH = os.environ.get("CONFIG_PATH", "/srv/config.yml")
DB_TIMEOUT_SECONDS = 2


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config(CONFIG_PATH)
    pool = AsyncConnectionPool(
        DATABASE_URL,
        min_size=1,
        max_size=8,
        open=False,
        kwargs={"autocommit": True, "row_factory": dict_row},
    )
    await pool.open(wait=True, timeout=10)
    await init_schema(pool)
    await abandon_unfinished_runs(pool)
    app.state.pool = pool
    hub = Hub()
    seats = SeatService(pool, config)
    app.state.seats = seats
    app.state.engine = Engine(pool, config, seats, hub)
    app.state.messages = MessageService(pool, seats, hub)
    yield
    await app.state.engine.shutdown()
    await pool.close()


app = FastAPI(lifespan=lifespan)
app.include_router(session_router)
app.include_router(event_log_router)
app.include_router(realtime_router)


def check_database() -> None:
    with psycopg.connect(DATABASE_URL, connect_timeout=DB_TIMEOUT_SECONDS) as conn:
        conn.execute(f"SET statement_timeout = {DB_TIMEOUT_SECONDS * 1000}")
        conn.execute("SELECT 1").fetchone()


@app.get("/api/health")
def health() -> JSONResponse:
    try:
        check_database()
    except Exception:
        return JSONResponse(
            {"status": "error", "database": "unavailable"}, status_code=503
        )
    return JSONResponse({"status": "ok", "database": "ok"})
