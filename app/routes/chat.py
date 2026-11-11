import logging

from fastapi import APIRouter, Header, HTTPException

from app.agent.runner import run_agent
from app.guardrails.injection import looks_like_injection
from app.guardrails.pii import mask_pii
from app.schemas.ChatRequest import ChatRequest
from app.schemas.ChatResponse import ChatResponse

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, authorization: str = Header(default="")):
    # 1. Authentication
    user_token = authorization.removeprefix("Bearer ").strip()
    if not authorization.startswith("Bearer ") or not user_token:
        raise HTTPException(status_code=401, detail="missing token")

    # 2. PII masking
    clean_question, pii_found = mask_pii(body.question)
    notice = None
    if pii_found:
        notice = "Please do not share personal data. We removed: " + ", ".join(pii_found)

    # 3. Prompt-injection check
    if looks_like_injection(clean_question):
        raise HTTPException(status_code=400, detail="request blocked by safety check.")

    # 4. The agent
    try:
        answer, session_id = await run_agent(clean_question, user_token, body.session_id)
    except Exception:
        log.exception("agent failed")
        raise HTTPException(status_code=502, detail="the assistant is unavailable, try again")

    return ChatResponse(answer=answer, notice=notice, session_id=session_id)