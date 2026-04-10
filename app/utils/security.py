import hashlib
import hmac
import json
import secrets
from base64 import urlsafe_b64decode, urlsafe_b64encode


def _b64encode(value: bytes) -> str:
    return urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return urlsafe_b64decode(value + padding)


def generate_api_key() -> str:
    return "gk_" + secrets.token_urlsafe(32)


def api_key_prefix(raw_key: str) -> str:
    return raw_key[:12]


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def hash_password(password: str, salt: str | None = None) -> str:
    password_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        password_salt.encode("utf-8"),
        120000,
    ).hex()
    return f"{password_salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, _ = password_hash.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), password_hash)


def sign_auth_token(payload: dict, secret_key: str) -> str:
    body = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = hmac.new(secret_key.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def verify_auth_token(token: str, secret_key: str) -> dict | None:
    try:
        body, signature = token.split(".", 1)
    except ValueError:
        return None

    expected = hmac.new(secret_key.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None

    try:
        return json.loads(_b64decode(body).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
