import hashlib
import re

from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent.workflow import WORKFLOW_NAME, access_flow
from app.config import APP_NAME, MAX_STEPS

REQUEST_INPUT = "adk_request_input"   # ADK's name for "the workflow is waiting for the user"
YES = {"yes", "y", "yep", "confirm", "approve", "ok", "okay", "sure"}
NO = {"no", "n", "nope", "cancel", "reject", "stop"}

session_service = InMemorySessionService()
runner = Runner(node=access_flow, app_name=APP_NAME, session_service=session_service)
run_config = RunConfig(max_llm_calls=MAX_STEPS)


def _user_key(token: str) -> str:
    # Sessions are scoped per token, so one user can't reuse another user's session_id.
    return hashlib.sha256(token.encode()).hexdigest()[:32]


def _pending_question(session) -> tuple[str, str] | None:
    """Return (interrupt_id, question) if the workflow is waiting for a yes/no."""
    answered = set()
    for event in reversed(session.events):
        for part in (event.content.parts if event.content else []) or []:
            if part.function_response and part.function_response.name == REQUEST_INPUT:
                answered.add(part.function_response.id)
            if part.function_call and part.function_call.name == REQUEST_INPUT:
                if part.function_call.id not in answered:
                    return part.function_call.id, part.function_call.args.get("message", "")
                return None
    return None


def _yes_or_no(text: str) -> bool | None:
    word = re.sub(r"[^a-z]", "", text.strip().lower())
    if word in YES:
        return True
    if word in NO:
        return False
    return None


async def run_agent(question: str, user_token: str, session_id: str | None) -> tuple[str, str]:
    user_id = _user_key(user_token)

    session = None
    if session_id:
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
    if session is None:
        session = await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, state={"user_token": user_token}
        )

    # If we asked "yes/no?" last turn, this message is the answer, not a new request.
    pending = _pending_question(session)
    if pending:
        interrupt_id, asked = pending
        approved = _yes_or_no(question)
        if approved is None:
            return f"Please answer yes or no. {asked}", session.id
        message = types.Content(role="user", parts=[types.Part(
            function_response=types.FunctionResponse(
                id=interrupt_id, name=REQUEST_INPUT, response={"approved": approved},
            ))])
    else:
        message = types.Content(role="user", parts=[types.Part(text=question)])

    replies = []
    async for event in runner.run_async(
        user_id=user_id, session_id=session.id, new_message=message, run_config=run_config,
    ):
        # Only show text from our workflow's nodes, not the extractor's raw JSON.
        if event.author != WORKFLOW_NAME or not event.content:
            continue
        for part in event.content.parts or []:
            if part.text:
                replies.append(part.text)
            elif part.function_call and part.function_call.name == REQUEST_INPUT:
                replies.append(part.function_call.args.get("message", ""))

    return "\n".join(replies) or "Sorry, I couldn't produce an answer.", session.id
