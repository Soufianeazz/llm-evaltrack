import time
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import ApiKeyContext, ensure_role, require_api_key_context
from api.limiter import limiter
from api.schemas import IngestResponse, LLMCallPayload
from pipeline.worker import enqueue
from storage.database import get_session
from storage.models import Request as RequestModel

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse, status_code=202)
@limiter.limit("60/minute")
async def ingest(
    request: Request,
    payload: LLMCallPayload,
    db: AsyncSession = Depends(get_session),
    ctx: ApiKeyContext = Depends(require_api_key_context),
):
    ensure_role(ctx, "admin", "analyst")

    request_id = str(uuid.uuid4())
    ts = payload.timestamp or time.time()

    row = RequestModel(
        id=request_id,
        api_key=ctx.key,
        input=payload.input,
        output=payload.output,
        prompt=payload.prompt,
        model=payload.model,
        metadata_=payload.metadata,
        timestamp=ts,
    )
    db.add(row)
    await db.commit()

    await enqueue({"request_id": request_id})

    return IngestResponse(request_id=request_id, queued=True)
