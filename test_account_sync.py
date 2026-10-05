"""Run with Python + both backends' auth dependencies and aiosqlite.

Uses temporary SQLite databases and ASGI clients in separate processes because
both repositories name their Python package `app`. No live data or keys are used.
"""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

WORKSPACE = Path(__file__).resolve().parent.parent
SYSTEM = WORKSPACE / "system_olpai2026" / "backend"
CHATBOT = WORKSPACE / "chatbot_oplai2026" / "chat_bot_allforn" / "backend"
SECRET = "test-only-account-provisioning-secret-" * 3


def run_chatbot_receiver():
    from dotenv import dotenv_values
    os.environ.update({k: v for k, v in dotenv_values(CHATBOT / ".env.example").items() if v is not None})
    os.environ.update(
        DATABASE_URL="sqlite+aiosqlite:///" + sys.argv[2],
        CHATBOT_SSO_SECRET=SECRET, CHATBOT_ACCOUNT_SYNC_ENABLED=sys.argv[3],
    )
    sys.path.insert(0, str(CHATBOT))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.auth import router
    from app.api.users import router as user_router
    from app.db.database import engine
    from app.models import User

    async def prepare():
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync: User.metadata.create_all(sync, tables=[User.__table__]))
    asyncio.run(prepare())
    app = FastAPI()
    app.include_router(router)
    app.include_router(user_router)
    with TestClient(app) as client:
        print("ready", flush=True)
        for line in sys.stdin:
            request = json.loads(line)
            response = client.request(**request)
            print(json.dumps({"status": response.status_code, "json": response.json()}), flush=True)
    asyncio.run(engine.dispose())


class AccountSyncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="oplai-account-sync-")
        cls.old_cwd = os.getcwd()
        os.chdir(cls.temp.name)
        os.environ.update(
            DATABASE_PATH=str(Path(cls.temp.name) / "system.db"),
            CHATBOT_ACCOUNT_SYNC_ENABLED="true", CHATBOT_SSO_SECRET=SECRET,
            CHATBOT_INTERNAL_URL="http://chatbot-fixture",
        )
        sys.path.insert(0, str(SYSTEM))
        from fastapi import FastAPI
        from app.routers import admin, auth
        cls.app = FastAPI()
        cls.app.include_router(admin.router)
        cls.app.include_router(auth.router)

    @classmethod
    def tearDownClass(cls):
        from app.database import engine
        engine.dispose()
        os.chdir(cls.old_cwd)
        cls.temp.cleanup()

    def setUp(self):
        from fastapi.testclient import TestClient
        from app.database import Base, engine, SessionLocal
        from app.models import User
        from app.auth_utils import create_access_token
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            admin = User(username="admin", email="admin@example.com", full_name="Admin", role="admin", password="fixture-password")
            db.add(admin)
            db.commit()
            self.headers = {"Authorization": "Bearer " + create_access_token({"sub": str(admin.id)})}
        self.client = TestClient(self.app)
        self.receiver = None
        self.chatbot_db = str(Path(self.temp.name) / (self._testMethodName + ".db"))
        self.start_receiver()

    def start_receiver(self, enabled="true"):
        self.receiver = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--receiver", self.chatbot_db, enabled],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", cwd=self.temp.name,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        if self.receiver.stdout.readline().strip() != "ready":
            raise RuntimeError(self.receiver.stderr.read())

    def stop_receiver(self):
        if self.receiver:
            self.receiver.stdin.close()
            self.receiver.wait(timeout=10)
            self.receiver.stdout.close()
            self.receiver.stderr.close()
            self.receiver = None

    def tearDown(self):
        self.stop_receiver()
        self.client.close()

    def chatbot(self, method, url, **kwargs):
        self.receiver.stdin.write(json.dumps({"method": method, "url": url, **kwargs}) + "\n")
        self.receiver.stdin.flush()
        line = self.receiver.stdout.readline()
        if not line:
            raise RuntimeError(self.receiver.stderr.read())
        return json.loads(line)

    def dispatch(self, fail=False):
        import httpx
        from app.chatbot_provisioning import dispatch_pending_accounts
        real_client = httpx.Client

        def handle(request):
            if fail:
                raise httpx.ConnectError("Fixture chatbot offline", request=request)
            response = self.chatbot("POST", request.url.path, json=json.loads(request.content))
            return httpx.Response(response["status"], json=response["json"])

        with patch("app.chatbot_provisioning.httpx.Client", side_effect=lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw)):
            dispatch_pending_accounts()

    def create(self, username="student", **kwargs):
        response = self.client.post("/api/admin/users", headers=self.headers, json={"username": username, **kwargs})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def login_chatbot(self, email, password, expected=200):
        response = self.chatbot("POST", "/auth/login", json={"email": email, "password": password})
        self.assertEqual(response["status"], expected, response)
        return response["json"]

    def pending(self):
        from app.database import SessionLocal
        from app.models import ChatbotProvisionJob
        with SessionLocal() as db:
            return db.query(ChatbotProvisionJob).count()

    def ticket(self, **overrides):
        import jwt
        from pwdlib import PasswordHash
        now = datetime.now(timezone.utc)
        claims = {"iss": "olpai-system", "aud": "olpai-chatbot", "type": "chatbot-provision",
                  "sub": "99", "email": "ticket@example.com", "role": "user", "jti": "a" * 32,
                  "iat": now, "exp": now + timedelta(seconds=60),
                  "password_hash": PasswordHash.recommended().hash("ticket-password")}
        return jwt.encode({**claims, **overrides}, SECRET, algorithm="HS256")

    def test_single_create_and_email_password_login_in_both_apps(self):
        user = self.create(email="Student@EXAMPLE.com", password="Shared-password", role="admin")
        self.assertEqual(self.pending(), 1)
        self.dispatch()
        self.assertEqual(self.pending(), 0)
        system = self.client.post("/api/auth/login", json={"username": user["email"], "password": user["password"]})
        self.assertEqual(system.status_code, 200)
        chatbot = self.login_chatbot(user["email"], user["password"])
        self.assertEqual(chatbot["user"]["role"], "admin")
        me = self.chatbot("GET", "/users/me", headers={"Authorization": "Bearer " + chatbot["access_token"]})
        self.assertEqual(me["status"], 200)
        self.assertEqual(me["json"]["email"], user["email"].lower())

    def test_batch_generated_passwords(self):
        response = self.client.post("/api/admin/users/batch", headers=self.headers, json={"count": 3})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.pending(), 3)
        self.dispatch()
        self.assertEqual(self.pending(), 0)
        for user in response.json()["users"]:
            self.login_chatbot(user["email"], user["password"])

    def test_system_password_lengths_and_chatbot_registration_policy(self):
        for username, password in [("short", "Ab@234"), ("long", "Long-password-" * 10)]:
            with self.subTest(username=username):
                user = self.create(username=username, password=password)
                self.dispatch()
                self.login_chatbot(user["email"], user["password"])
        batch = self.client.post("/api/admin/users/batch", headers=self.headers, json={"count": 2, "password_length": 6})
        self.assertEqual(batch.status_code, 200)
        self.dispatch()
        for user in batch.json()["users"]:
            self.assertEqual(len(user["password"]), 6)
            self.login_chatbot(user["email"], user["password"])
        registration = self.chatbot("POST", "/auth/register", json={"email": "short-registration@example.com", "password": "Ab@234"})
        self.assertEqual(registration["status"], 422)

    def test_background_worker_dispatches_without_another_user_action(self):
        import httpx
        from app.chatbot_provisioning import provisioning_lifespan
        user = self.create(password="Background-password")
        real_client = httpx.Client

        def handle(request):
            response = self.chatbot("POST", request.url.path, json=json.loads(request.content))
            return httpx.Response(response["status"], json=response["json"])

        async def run_worker():
            async with provisioning_lifespan(self.app):
                for _ in range(100):
                    if self.pending() == 0:
                        return
                    await asyncio.sleep(0.05)
                self.fail("Background provisioning did not complete")
        with patch("app.chatbot_provisioning.httpx.Client", side_effect=lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw)):
            asyncio.run(run_worker())
        self.login_chatbot(user["email"], user["password"])

    def test_lost_acknowledgement_retries_without_replacing_remote_account(self):
        import httpx
        from app.chatbot_provisioning import dispatch_pending_accounts
        from app.database import SessionLocal
        from app.models import ChatbotProvisionJob
        user = self.create(password="Lost-response-password")
        real_client = httpx.Client

        def handle(request):
            response = self.chatbot("POST", request.url.path, json=json.loads(request.content))
            self.assertEqual(response["status"], 200)
            raise httpx.ReadTimeout("Fixture lost response", request=request)

        with patch("app.chatbot_provisioning.httpx.Client", side_effect=lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw)):
            dispatch_pending_accounts()
        original = self.login_chatbot(user["email"], user["password"])["user"]["id"]
        with SessionLocal() as db:
            job = db.query(ChatbotProvisionJob).one()
            job.next_attempt_at = datetime.utcnow() - timedelta(seconds=1)
            db.commit()
        self.dispatch()
        self.assertEqual(self.pending(), 0)
        self.assertEqual(self.login_chatbot(user["email"], user["password"])["user"]["id"], original)

    def test_sync_enabled_without_secret_is_inert(self):
        with patch.dict(os.environ, {"CHATBOT_SSO_SECRET": ""}):
            self.create(password="No-integration-key")
            self.assertEqual(self.pending(), 0)
            self.assertEqual(self.client.post("/api/auth/login", json={"username": "student", "password": "No-integration-key"}).status_code, 200)

    def test_offline_retry_persists_after_database_and_receiver_restart(self):
        from app.database import SessionLocal, engine
        from app.models import ChatbotProvisionJob
        user = self.create(password="Offline-password")
        self.dispatch(fail=True)
        self.assertEqual(self.pending(), 1)
        engine.dispose()
        self.stop_receiver()
        self.start_receiver()
        with SessionLocal() as db:
            job = db.query(ChatbotProvisionJob).one()
            self.assertEqual(job.attempts, 1)
            self.assertEqual(job.last_error, "transport_error")
            self.assertTrue(job.password_hash.startswith("$argon2id$"))
            self.assertNotIn(user["password"], job.password_hash)
            job.next_attempt_at = datetime.utcnow() - timedelta(seconds=1)
            db.commit()
        self.dispatch()
        self.assertEqual(self.pending(), 0)
        self.login_chatbot(user["email"], user["password"])

    def test_existing_chatbot_password_and_role_preserved_and_retries_idempotent(self):
        self.assertEqual(self.chatbot("POST", "/auth/register", json={"email": "existing@example.com", "password": "Original-password"})["status"], 201)
        self.create(email="existing@example.com", password="System-password", role="admin")
        self.dispatch()
        self.assertEqual(self.pending(), 0)
        session = self.login_chatbot("existing@example.com", "Original-password")
        self.assertEqual(session["user"]["role"], "user")
        self.login_chatbot("existing@example.com", "System-password", expected=401)
        ticket = self.ticket()
        first = self.chatbot("POST", "/auth/system-provision", json={"ticket": ticket})
        second = self.chatbot("POST", "/auth/system-provision", json={"ticket": ticket})
        self.assertEqual(first, {"status": 200, "json": {"created": True}})
        self.assertEqual(second, {"status": 200, "json": {"created": False}})

    def test_rollback_duplicate_and_delete_do_not_leave_jobs(self):
        from app.database import SessionLocal
        from app.models import User
        from app.chatbot_provisioning import enqueue_chatbot_account
        with SessionLocal() as db:
            user = User(username="rolledback", email="rolledback@example.com", full_name="Rollback", password="pw")
            db.add(user)
            db.flush()
            enqueue_chatbot_account(db, user, "pw")
            db.rollback()
        self.assertEqual(self.pending(), 0)
        user = self.create()
        duplicate = self.client.post("/api/admin/users", headers=self.headers, json={"username": user["username"]})
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(self.pending(), 1)
        self.assertEqual(self.client.delete(f"/api/admin/users/{user['id']}", headers=self.headers).status_code, 200)
        self.assertEqual(self.pending(), 0)

    def test_standalone_apps_do_not_require_integration(self):
        from app.chatbot_provisioning import provisioning_lifespan
        with patch.dict(os.environ, {"CHATBOT_ACCOUNT_SYNC_ENABLED": "false", "CHATBOT_SSO_SECRET": "", "CHATBOT_INTERNAL_URL": ""}):
            self.create(password="Standalone-password")
            self.assertEqual(self.pending(), 0)
            with patch("app.chatbot_provisioning.httpx.Client") as remote:
                self.dispatch()
                async def check_lifespan():
                    async with provisioning_lifespan(self.app):
                        await asyncio.sleep(0.01)
                asyncio.run(check_lifespan())
                remote.assert_not_called()
            self.assertEqual(self.client.post("/api/auth/login", json={"username": "student", "password": "Standalone-password"}).status_code, 200)
        self.stop_receiver()
        self.start_receiver(enabled="false")
        self.assertEqual(self.chatbot("POST", "/auth/system-provision", json={"ticket": self.ticket()})["status"], 503)
        self.assertEqual(self.chatbot("POST", "/auth/register", json={"email": "independent@example.com", "password": "Independent-password"})["status"], 201)
        self.login_chatbot("independent@example.com", "Independent-password")

    def test_provisioning_authentication_and_purpose_separation(self):
        import jwt
        ticket = self.ticket()
        claims = jwt.decode(ticket, SECRET, algorithms=["HS256"], audience="olpai-chatbot")
        invalid = [{"aud": "other"}, {"iss": "other"}, {"type": "chatbot-sso"}, {"role": "owner"},
                   {"exp": int(datetime.now(timezone.utc).timestamp()) - 1},
                   {"email": "invalid"}, {"password_hash": "plaintext"}, {"jti": "short"},
                   {"exp": claims["iat"] + 3600}]
        for changes in invalid:
            with self.subTest(changes=changes):
                bad = jwt.encode({**claims, **changes}, SECRET, algorithm="HS256")
                self.assertEqual(self.chatbot("POST", "/auth/system-provision", json={"ticket": bad})["status"], 401)
        wrong_key = jwt.encode(claims, "wrong-key-" * 10, algorithm="HS256")
        self.assertEqual(self.chatbot("POST", "/auth/system-provision", json={"ticket": wrong_key})["status"], 401)
        self.assertEqual(self.chatbot("POST", "/auth/system-sso", json={"ticket": ticket})["status"], 401)
        self.assertEqual(self.chatbot("GET", "/users/me", headers={"Authorization": "Bearer " + ticket})["status"], 401)
        self.assertEqual(self.client.post("/api/admin/users", json={"username": "unauthorized"}).status_code, 401)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--receiver":
        run_chatbot_receiver()
    else:
        unittest.main(verbosity=2)
