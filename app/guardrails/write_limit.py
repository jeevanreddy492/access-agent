from google.adk.tools import BaseTool, ToolContext

# Tools that change something, and the arguments each one needs.
WRITE_TOOLS = {
    "create_access_request": ("user_id", "role_id"),
}

_STATE_KEY = "last_write_invocation"


def one_write_per_turn(tool: BaseTool, args: dict, tool_context: ToolContext) -> dict | None:
    """Allow at most one write tool call per user message.

    Returning a dict skips the tool; ADK sends the dict to the model as the result.
    Returning None lets the tool run.
    """
    required = WRITE_TOOLS.get(tool.name)
    if required is None:
        return None  # read-only tool, no limit

    # A call with missing arguments would fail anyway; don't let it use up the turn's write.
    missing = [a for a in required if not args.get(a)]
    if missing:
        return {"status": 400, "error": f"missing arguments: {', '.join(missing)}"}

    # Each user message is one ADK invocation, so its id identifies the turn.
    turn = tool_context.invocation_id
    if tool_context.state.get(_STATE_KEY) == turn:
        return {
            "status": 429,
            "error": "Only one change is allowed per message. Do not retry. "
                     "Tell the user what was already submitted and ask them to send "
                     "a new message for anything else.",
        }

    tool_context.state[_STATE_KEY] = turn
    return None
