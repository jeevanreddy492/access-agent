"""Deterministic access-request workflow.

    START -> extract -> validate --ok--> confirm --yes--> submit
                            |                 \\--no---> cancelled
                            \\--invalid (replies and stops)

Only `extract` uses the LLM, and it has no tools: it just turns the message into
{user_id, role_id}. Every decision after that is plain code.
"""

import re
import uuid

from google.adk.agents import Agent
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.workflow import START, Workflow, node
from pydantic import BaseModel

import app.config  # noqa: F401  (sets the Vertex env vars before ADK runs)
from app.clients import access_api
from app.config import MODEL_NAME
from app.prompts.system import EXTRACT_PROMPT
from app.tools.access_request import submit_access_request

WORKFLOW_NAME = "access_flow"


class AccessRequest(BaseModel):
    user_id: str | None = None
    role_id: str | None = None


# Step 1 (LLM): message -> {user_id, role_id}. Sees only the current message.
extract = Agent(
    name="extract",
    model=MODEL_NAME,
    instruction=EXTRACT_PROMPT,
    output_schema=AccessRequest,
    include_contents="none",
)


# Step 2 (code): check the request against the directory.
@node
def validate(node_input: dict):
    user_id = (node_input.get("user_id") or "").strip().lower()
    # "Billing Admin" / "billing_admin" -> "billing-admin"
    role_id = re.sub(r"[\s_]+", "-", (node_input.get("role_id") or "").strip().lower())

    if not user_id or not role_id:
        return Event(route="invalid", message=(
            "Please tell me which user and which role, "
            "e.g. \"Request billing-admin for alice\"."))
    if not access_api.user_exists(user_id):
        return Event(route="invalid", message=f"I couldn't find a user called '{user_id}'.")
    if not access_api.role_exists(role_id):
        roles = ", ".join(sorted(access_api.ROLES))
        return Event(route="invalid", message=f"'{role_id}' isn't a known role. Available roles: {roles}.")
    if access_api.user_has_role(user_id, role_id):
        return Event(route="invalid", message=f"{user_id} already has the {role_id} role.")

    return Event(route="ok", output={"user_id": user_id, "role_id": role_id})


# Step 3 (code): pause and ask the user. Runs again when the answer arrives.
@node(rerun_on_resume=True)
def confirm(ctx, node_input: dict):
    interrupt_id = ctx.state.get("confirm_id")
    answer = ctx.resume_inputs.get(interrupt_id) if interrupt_id else None

    if answer is None:
        ctx.state["confirm_id"] = f"confirm-{uuid.uuid4().hex}"
        return RequestInput(
            interrupt_id=ctx.state["confirm_id"],
            message=(f"Submit a request to give {node_input['user_id']} "
                     f"the {node_input['role_id']} role? (yes/no)"),
            payload=node_input,
        )

    ctx.state["confirm_id"] = None
    return Event(route="yes" if answer.get("approved") else "no", output=node_input)


# Step 4 (code): the only place that writes. Runs at most once per confirmation.
@node
def submit(ctx, node_input: dict):
    token = ctx.state.get("user_token")
    result = submit_access_request(token, node_input["user_id"], node_input["role_id"])

    if result["status"] == 201:
        text = (f"Done. Request {result['request_id']} was created to give "
                f"{node_input['user_id']} the {node_input['role_id']} role.")
    elif result["status"] == 403:
        text = "You're not allowed to request access."
    elif result["status"] == 401:
        text = "Your token isn't valid. Please sign in again."
    elif result["status"] == 409:
        text = f"{node_input['user_id']} already has the {node_input['role_id']} role."
    else:
        text = "The access request failed. Please try again later."
    return Event(message=text)


@node
def cancelled():
    return Event(message="Okay, I didn't submit anything.")


access_flow = Workflow(
    name=WORKFLOW_NAME,
    edges=[
        (START, extract, validate, {"ok": confirm}),
        (confirm, {"yes": submit, "no": cancelled}),
    ],
)
