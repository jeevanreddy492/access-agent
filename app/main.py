from fastapi import FastAPI

from app.routes import chat

app = FastAPI(title="Access Agent")

app.include_router(chat.router)