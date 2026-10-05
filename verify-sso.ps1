# Integration checks use temporary tokens in memory, without changing passwords.
. (Join-Path $PSScriptRoot 'common.ps1')
Assert-Docker
$prepare = @'
import json, os, secrets
from datetime import datetime, timedelta, timezone
import jwt
from app.database import SessionLocal
from app.models import User
from app.auth_utils import create_access_token, get_password_hash, verify_password
from pwdlib import PasswordHash
password = "Integration-password-2026"
assert verify_password(password, PasswordHash.recommended().hash(password))
assert not verify_password("wrong", PasswordHash.recommended().hash(password))
assert verify_password(password, get_password_hash(password))
assert verify_password(password, password)
assert not verify_password(password, "$argon2id$invalid")
with SessionLocal() as db:
    users = db.query(User).filter(User.password.like("$argon2%")).all()
    assert users, "Synchronize chatbot accounts first"
    now = datetime.now(timezone.utc)
    base = {"iss":"olpai-system", "aud":"olpai-chatbot", "type":"chatbot-sso",
            "sub":str(users[0].id), "email":users[0].email, "role":users[0].role,
            "jti":secrets.token_urlsafe(32), "iat":now, "exp":now+timedelta(seconds=60)}
    invalid = {}
    for name, changes in {
        "expired":{"iat":now-timedelta(seconds=120), "exp":now-timedelta(seconds=60)},
        "wrong_audience":{"aud":"other-app"}, "wrong_issuer":{"iss":"other-system"},
        "wrong_type":{"type":"access"}, "wrong_role":{"role":"owner"},
    }.items():
        invalid[name] = jwt.encode({**base, **changes}, os.environ["CHATBOT_SSO_SECRET"], algorithm="HS256")
    invalid["wrong_signature"] = jwt.encode(base, secrets.token_urlsafe(64), algorithm="HS256")
    print(json.dumps({"users":[{"email":u.email,"role":u.role,"token":create_access_token({"sub":str(u.id)})} for u in users], "invalid":invalid}))
'@
$oldOutputEncoding = $OutputEncoding
try {
    $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $credentials = $prepare | & docker exec -i olp_ai_kma_backend python -
    if ($LASTEXITCODE -ne 0) { throw 'Unable to prepare integration checks.' }
    $credentials | python (Join-Path $PSScriptRoot 'verify_sso.py')
    if ($LASTEXITCODE -ne 0) { throw 'SSO integration checks failed.' }
} finally {
    $credentials = $null
    $OutputEncoding = $oldOutputEncoding
}
