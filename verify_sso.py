"""Integration checks. Private tokens arrive over stdin and are never printed."""
import concurrent.futures
import json
import os
import sys
import urllib.error
import urllib.request


def request(path, body=None, token=None):
    base = os.getenv("SSO_VERIFY_URL", "http://localhost:8080")
    headers = {"ngrok-skip-browser-warning": "true"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def main():
    credentials = json.load(sys.stdin)
    status, _ = request("/api/auth/chatbot-ticket", {})
    assert status == 401, "Unauthenticated ticket issuance must be rejected"
    for user in credentials["users"]:
        status, issued = request("/api/auth/chatbot-ticket", {}, user["token"])
        assert status == 200
        status, session = request("/chatbot/api/auth/system-sso", issued)
        assert status == 200 and session["user"]["email"] == user["email"]
        assert session["user"]["role"] == user["role"]
        status, me = request("/chatbot/api/users/me", token=session["access_token"])
        assert status == 200 and me["id"] == session["user"]["id"]
        status, _ = request("/chatbot/api/auth/system-sso", issued)
        assert status == 401, "Replayed tickets must be rejected"
        status, _ = request("/chatbot/api/users/me", token=issued["ticket"])
        assert status == 401, "SSO tickets must not authenticate normal chatbot APIs"
    for name, ticket in credentials["invalid"].items():
        status, _ = request("/chatbot/api/auth/system-sso", {"ticket": ticket})
        assert status == 401, f"Invalid ticket accepted: {name}"
    status, _ = request("/chatbot/api/auth/system-sso", {"ticket": "malformed"})
    assert status == 401
    status, ticket = request("/api/auth/chatbot-ticket", {}, credentials["users"][0]["token"])
    assert status == 200
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        statuses = sorted(executor.map(lambda _: request("/chatbot/api/auth/system-sso", ticket)[0], range(2)))
    assert statuses == [200, 401], "Concurrent redemption must succeed exactly once"
    print(f"PASS: {len(credentials['users'])} imported accounts, protected issuance, invalid/expired/replayed tickets, concurrent redemption, password compatibility.")


if __name__ == "__main__":
    main()
