import os

import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse

DATABASE_URL = os.environ["DATABASE_URL"]
DB_TIMEOUT_SECONDS = 2

app = FastAPI()


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
