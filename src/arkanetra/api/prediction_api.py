from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[2]
PREDICTIONS_DIR = ROOT / "reports" / "predictions"
MANIFEST_PATH = ROOT / "reports" / "artifact_manifest.json"
ALERT_PATH = ROOT / "reports" / "alert_history.csv"
AUDIT_PATH = ROOT / "reports" / "audit_log.jsonl"

API_KEY = os.environ.get("ARKANETRA_API_KEY", "")
RATE_LIMIT_REQUESTS = int(os.environ.get("ARKANETRA_RATE_LIMIT_RPM", "60"))
RATE_LIMIT_WINDOW = 60

_rate_limit_store: dict[str, list[float]] = defaultdict(list)

VALID_ALERT_STATES = {"NORMAL", "WATCH", "WARNING", "CRITICAL", "RESOLVED", "UNCERTAIN"}
VALID_SCENARIOS = {"baseline", "high_activity", "quiet_sun", "ensemble"}


class RateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        self._requests[client_id] = [t for t in self._requests[client_id] if t > cutoff]
        if len(self._requests[client_id]) >= self.max_requests:
            return False
        self._requests[client_id].append(now)
        return True

    def remaining(self, client_id: str) -> int:
        now = time.time()
        cutoff = now - self.window_seconds
        recent = [t for t in self._requests[client_id] if t > cutoff]
        return max(0, self.max_requests - len(recent))

    def retry_after(self, client_id: str) -> int:
        now = time.time()
        cutoff = now - self.window_seconds
        recent = [t for t in self._requests[client_id] if t > cutoff]
        if len(recent) < self.max_requests:
            return 0
        oldest = min(recent)
        return int(oldest + self.window_seconds - now) + 1


rate_limiter = RateLimiter(max_requests=RATE_LIMIT_REQUESTS, window_seconds=RATE_LIMIT_WINDOW)

app = FastAPI(
    title="ArkaNetra Prediction API",
    version="0.2.0",
    description="Operational Decision-Support API for ArkaNetra flare predictions",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _get_client_id(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _require_api_key(request: Request) -> None:
    if not API_KEY:
        return
    auth_header = request.headers.get("Authorization", "")
    api_key_header = request.headers.get("X-API-Key", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    elif api_key_header:
        token = api_key_header
    else:
        token = ""
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.middleware("http")
async def auth_and_rate_limit_middleware(request: Request, call_next):
    if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
        return await call_next(request)

    try:
        _require_api_key(request)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

    client_id = _get_client_id(request)
    if not rate_limiter.is_allowed(client_id):
        retry = rate_limiter.retry_after(client_id)
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded", "retry_after_seconds": retry},
            headers={"Retry-After": str(retry)},
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(rate_limiter.max_requests)
    response.headers["X-RateLimit-Remaining"] = str(rate_limiter.remaining(client_id))
    return response


def load_predictions() -> pd.DataFrame:
    jsonl_path = PREDICTIONS_DIR / "predictions.jsonl"
    if jsonl_path.exists():
        records = []
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return pd.DataFrame(records)
    parquet_path = ROOT / "reports" / "predictions" / "arkanetra_mvp_predictions.parquet"
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    return pd.DataFrame()


def load_alerts() -> pd.DataFrame:
    if ALERT_PATH.exists():
        return pd.read_csv(ALERT_PATH)
    return pd.DataFrame()


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}


def load_audit_log() -> list[dict]:
    if not AUDIT_PATH.exists():
        return []
    entries = []
    with AUDIT_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


@app.get("/health")
def health_check() -> dict[str, Any]:
    predictions = load_predictions()
    alerts = load_alerts()
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "predictions_count": len(predictions),
        "alerts_count": len(alerts),
        "version": "0.2.0",
    }


@app.get("/predictions")
def get_predictions(
    scenario: str | None = Query(None, description="Filter by scenario"),
    mission_state: str | None = Query(None, description="Filter by mission state"),
    limit: int = Query(100, ge=1, le=10000, description="Max records to return"),
) -> dict[str, Any]:
    if scenario and scenario not in VALID_SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario '{scenario}'. Valid: {sorted(VALID_SCENARIOS)}",
        )

    df = load_predictions()
    if df.empty:
        return {"predictions": [], "total": 0, "filtered": 0}

    filtered = df
    if scenario:
        filtered = filtered[filtered["scenario"] == scenario]
    if mission_state:
        filtered = filtered[filtered["mission_state"] == mission_state]

    filtered = filtered.head(limit)
    return {
        "predictions": filtered.to_dict(orient="records"),
        "total": len(df),
        "filtered": len(filtered),
    }


@app.get("/alerts")
def get_alerts(
    state: str | None = Query(None, description="Filter by alert state"),
    limit: int = Query(100, ge=1, le=10000, description="Max records to return"),
) -> dict[str, Any]:
    if state and state.upper() not in VALID_ALERT_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state '{state}'. Valid: {sorted(VALID_ALERT_STATES)}",
        )

    df = load_alerts()
    if df.empty:
        return {"alerts": [], "total": 0}

    filtered = df
    if state:
        filtered = filtered[filtered["state"] == state.upper()]

    filtered = filtered.head(limit)
    return {
        "alerts": filtered.to_dict(orient="records"),
        "total": len(df),
        "state_summary": df["state"].value_counts().to_dict() if not df.empty else {},
    }


@app.get("/manifest")
def get_manifest() -> dict[str, Any]:
    return load_manifest()


@app.get("/audit")
def get_audit_log(limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
    entries = load_audit_log()
    return {
        "entries": entries[-limit:],
        "total": len(entries),
    }


@app.get("/scenarios")
def get_scenarios() -> dict[str, Any]:
    predictions = load_predictions()
    if predictions.empty:
        return {"scenarios": []}
    scenarios = predictions["scenario"].value_counts().to_dict()
    return {"scenarios": scenarios}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
