import json
import uuid

import redis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal

from src.auth.jwt import get_current_user_id
from src.config import settings
from src.tasks.celery_app import celery_app

router = APIRouter(tags=["tasks"])

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

_TASK_TTL = 60 * 60 * 24  # 24 hours


# --- Schemas ---

class AnalyzeRequest(BaseModel):
    symbol: str
    analyses: list[Literal["sentiment", "technical", "forecast"]]
    forecast_timeframe: Literal["6m", "12m", "3y"] | None = None


class TaskResponse(BaseModel):
    task_id: str
    symbol: str
    status: str
    results: dict


# --- Helpers ---

def _task_key(task_id: str) -> str:
    return f"task:{task_id}"


def _get_task_meta(task_id: str) -> dict:
    raw = redis_client.get(_task_key(task_id))
    if not raw:
        raise HTTPException(status_code=404, detail="Task not found")
    return json.loads(raw)


def _save_task_meta(task_id: str, meta: dict) -> None:
    redis_client.setex(_task_key(task_id), _TASK_TTL, json.dumps(meta))


# --- Routes ---

@router.post("/analyze")
def analyze(
    body: AnalyzeRequest,
    user_id: str = Depends(get_current_user_id),
):
    task_id = str(uuid.uuid4())
    symbol = body.symbol.upper()

    # Dispatch data fetch first — all analysis workers depend on this completing
    data_result = celery_app.send_task("fetch_stock_data", args=[symbol], queue="data")

    meta = {
        "symbol": symbol,
        "analyses": body.analyses,
        "forecast_timeframe": body.forecast_timeframe,
        "user_id": user_id,
        "sub_tasks": {"data": data_result.id},
        "status": "fetching_data",
    }
    _save_task_meta(task_id, meta)

    return {"task_id": task_id}


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
):
    meta = _get_task_meta(task_id)
    sub_tasks = meta["sub_tasks"]
    results = {}

    # Check the data sub-task
    data_result = celery_app.AsyncResult(sub_tasks["data"])
    results["data"] = {"status": data_result.state.lower()}

    if data_result.successful():
        results["data"]["result"] = data_result.result

        # Check analysis sub-tasks — workers dispatched in phases 3-5
        all_done = True
        for analysis in meta["analyses"]:
            if analysis in sub_tasks:
                result = celery_app.AsyncResult(sub_tasks[analysis])
                results[analysis] = {"status": result.state.lower()}
                if result.successful():
                    results[analysis]["result"] = result.result
                elif result.failed():
                    results[analysis]["error"] = str(result.result)
                else:
                    all_done = False
            else:
                # Worker not yet implemented (Phase 3+)
                results[analysis] = {"status": "pending"}
                all_done = False

        overall_status = "complete" if all_done else "analyzing"

    elif data_result.failed():
        overall_status = "failed"
        results["data"]["error"] = str(data_result.result)
    else:
        overall_status = "fetching_data"

    meta["status"] = overall_status
    _save_task_meta(task_id, meta)

    return TaskResponse(
        task_id=task_id,
        symbol=meta["symbol"],
        status=overall_status,
        results=results,
    )