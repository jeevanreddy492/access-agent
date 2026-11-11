from google.adk.agents import Agent
from google.adk.tools import ToolContext

import app.config  # noqa: F401  (sets the Vertex env vars before ADK runs)
from app.config import MODEL_NAME
from app.guardrails.write_limit import one_write_per_turn
from app.prompts.system import SYSTEM_PROMPT
from app.tools.access_request import submit_access_request


def create_access_request(user_id: str, role_id: str, tool_context: ToolContext) -> dict:
    """Create a request to give a user a role.

    Args:
        user_id: The user who needs the role, e.g. alice.
        role_id: The role to request, e.g. billing-admin.
    """
    # The token comes from session state, never from the model.
    token = tool_context.state.get("user_token")
    if not token:
        return {"status": 401, "error": "no user token in session"}
    return submit_access_request(token, user_id, role_id)


root_agent = Agent(
    name="access_agent",
    model=MODEL_NAME,
    instruction=SYSTEM_PROMPT,
    tools=[create_access_request],
    before_tool_callback=one_write_per_turn,
)
