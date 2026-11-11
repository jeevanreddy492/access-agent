import hashlib

from google.adk.agents.invocation_context import LlmCallsLimitExceededError
from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent.agent import root_agent
from app.config import APP_NAME, MAX_STEPS

session_service = InMemorySessionService()
runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
run_config = RunConfig(max_llm_calls=MAX_STEPS)


def _user_key(token: str) -> str:
    # Sessions are scoped per token, so one user can't reuse another user's session_id.
    return hashlib.sha256(token.encode()).hexdigest()[:32]


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

    message = types.Content(role="user", parts=[types.Part(text=question)])
    answer = ""
    try:
        async for event in runner.run_async(
            user_id=user_id, session_id=session.id,
            new_message=message, run_config=run_config,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                answer = "".join(p.text or "" for p in event.content.parts)
    except LlmCallsLimitExceededError:
        answer = "Sorry, I couldn't finish that request. Please try again more simply."

    return answer or "Sorry, I couldn't produce an answer.", session.id