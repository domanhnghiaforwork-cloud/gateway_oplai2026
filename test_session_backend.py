"""Isolated auth API fixture for browser session tests; never opens live DBs.

Usage: python test_session_backend.py system|chatbot PORT
Install the auth dependencies of both backends, aiosqlite and uvicorn first.
"""
import asyncio
import os
from pathlib import Path
import sys
import tempfile

from fastapi import FastAPI
import uvicorn

WORKSPACE = Path(__file__).resolve().parent.parent
SECRET = "browser-test-only-system-sso-secret-" * 3
ACCOUNTS = [("session_a", "session.a@example.com"), ("session_b", "session.b@example.com")]


def create_system_app(temp):
    os.environ.update(DATABASE_PATH=str(Path(temp) / "system.db"), CHATBOT_SSO_SECRET=SECRET)
    sys.path.insert(0, str(WORKSPACE / "system_olpai2026/backend"))
    from app.database import Base, engine, SessionLocal
    from app.models import User
    from app.routers.auth import router
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for username, email in ACCOUNTS:
            db.add(User(username=username, email=email, password="Session-password-2026", full_name=username, role="user"))
        db.commit()
    app = FastAPI()
    app.include_router(router)

    @app.get("/api/{path:path}")
    def empty_lists(path: str):
        return []
    return app


def create_chatbot_app(temp):
    from dotenv import dotenv_values
    backend = WORKSPACE / "chatbot_oplai2026/chat_bot_allforn/backend"
    os.environ.update({k: v for k, v in dotenv_values(backend / ".env.example").items() if v is not None})
    os.environ.update(DATABASE_URL="sqlite+aiosqlite:///" + str(Path(temp) / "chatbot.db"), CHATBOT_SSO_SECRET=SECRET)
    sys.path.insert(0, str(backend))
    from app.api.auth import router
    from app.api.users import router as user_router
    from app.db.database import engine, SessionLocal
    from app.models import User
    from app.security.password import hash_password
    import app.security.system_sso as sso

    class TicketReplayGuard:
        def __init__(self):
            self.used = set()

        async def set(self, key, value, nx, ex):
            if key in self.used:
                return False
            self.used.add(key)
            return True
    replay_guard = TicketReplayGuard()
    sso.get_redis = lambda: replay_guard

    async def prepare():
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync: User.metadata.create_all(sync, tables=[User.__table__]))
        async with SessionLocal() as db:
            for _, email in ACCOUNTS:
                db.add(User(email=email, password_hash=hash_password("Session-password-2026"), role="user"))
            await db.commit()
    asyncio.run(prepare())
    app = FastAPI()
    app.include_router(router)
    app.include_router(user_router)

    @app.get("/config")
    def config():
        return {"name_chatbot": "Session verification"}

    @app.get("/conversations")
    def conversations():
        return []
    return app


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="oplai-session-api-") as temp:
        os.chdir(temp)
        create = create_system_app if sys.argv[1] == "system" else create_chatbot_app
        uvicorn.run(create(temp), host="127.0.0.1", port=int(sys.argv[2]), log_level="warning")
