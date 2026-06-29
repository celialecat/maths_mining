import hashlib
import hmac
import json
import time
from functools import wraps
from uuid import uuid4

import bcrypt
from flask import jsonify, request

import config

# In-memory user store: {username: {password_hash, user_id, wallet_address}}
_users: dict[str, dict] = {}

# JWT secret generated at startup
_JWT_SECRET = uuid4().hex
_JWT_EXPIRY_SECONDS = 86400  # 24 hours


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _create_token(user_id: str, username: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": int(time.time()) + _JWT_EXPIRY_SECONDS,
    }
    return _jwt_encode(header, payload)


def _jwt_encode(header: dict, payload: dict) -> str:
    import base64

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    h = b64url(json.dumps(header, separators=(",", ":")).encode())
    p = b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig_input = f"{h}.{p}".encode()
    sig = hmac.new(_JWT_SECRET.encode(), sig_input, hashlib.sha256).digest()
    return f"{h}.{p}.{b64url(sig)}"


def _jwt_decode(token: str) -> dict | None:
    import base64

    def b64url_decode(s: str) -> bytes:
        s += "=" * (4 - len(s) % 4)
        return base64.urlsafe_b64decode(s)

    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        sig_input = f"{parts[0]}.{parts[1]}".encode()
        expected_sig = hmac.new(
            _JWT_SECRET.encode(), sig_input, hashlib.sha256
        ).digest()
        actual_sig = b64url_decode(parts[2])

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(b64url_decode(parts[1]))

        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


def get_current_user() -> dict | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    payload = _jwt_decode(token)
    if payload is None:
        return None
    username = payload.get("username")
    if username not in _users:
        return None
    user = _users[username]
    return {
        "user_id": user["user_id"],
        "username": username,
        "wallet_address": user.get("wallet_address"),
    }


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return jsonify({"error": "Authentication required"}), 401
        request.current_user = user
        return f(*args, **kwargs)
    return decorated


def register_user(username: str, password: str) -> tuple[dict | None, str | None]:
    if not username or not password:
        return None, "Username and password are required"
    if len(username) < 3:
        return None, "Username must be at least 3 characters"
    if len(password) < 4:
        return None, "Password must be at least 4 characters"
    if username in _users:
        return None, "Username already taken"

    user_id = uuid4().hex
    _users[username] = {
        "user_id": user_id,
        "password_hash": _hash_password(password),
        "wallet_address": None,
    }
    token = _create_token(user_id, username)
    return {"token": token, "username": username, "user_id": user_id}, None


def login_user(username: str, password: str) -> tuple[dict | None, str | None]:
    if not username or not password:
        return None, "Username and password are required"
    if username not in _users:
        return None, "Invalid username or password"
    user = _users[username]
    if not _check_password(password, user["password_hash"]):
        return None, "Invalid username or password"

    token = _create_token(user["user_id"], username)
    return {
        "token": token,
        "username": username,
        "user_id": user["user_id"],
        "wallet_address": user.get("wallet_address"),
    }, None


def assign_wallet(username: str, address: str) -> None:
    if username in _users:
        _users[username]["wallet_address"] = address


def get_user_wallet(username: str) -> str | None:
    if username in _users:
        return _users[username].get("wallet_address")
    return None


def get_all_users_summary() -> list[dict]:
    return [
        {"username": u, "user_id": d["user_id"], "has_wallet": d.get("wallet_address") is not None}
        for u, d in _users.items()
    ]
