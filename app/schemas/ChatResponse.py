from pydantic import BaseModel


class ChatResponse(BaseModel):
    answer: str
    notice: str | None = None
    session_id: str