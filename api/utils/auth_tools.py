import jwt
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import unquote, parse_qs, parse_qsl

from database.database import get_db
from database.models import Member
from config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    telegram_token,
)

bearer_scheme = HTTPBearer()


def verify_telegram_auth(data: dict) -> bool:
    hash_from_telegram = data.pop("hash", None)
    if not hash_from_telegram:
        return False

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))

    secret_key = hashlib.sha256(telegram_token.encode()).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    print(computed_hash, hash_from_telegram)
    return computed_hash == hash_from_telegram


def validate_web_app_data(init_data):
    parsed_data = parse_qs(init_data)
    hash_str = parsed_data.get("hash", [""])[0]
    init_data = sorted(
        [
            chunk.split("=")
            for chunk in unquote(init_data).split("&")
            if chunk[: len("hash=")] != "hash="
        ],
        key=lambda x: x[0],
    )
    init_data = "\n".join([f"{rec[0]}={rec[1]}" for rec in init_data])

    secret_key = hmac.new(
        "WebAppData".encode(), telegram_token.encode(), hashlib.sha256
    ).digest()
    data_check = hmac.new(secret_key, init_data.encode(), hashlib.sha256)

    print(data_check.hexdigest(), hash_str)
    if data_check.hexdigest() != hash_str:
        raise Exception("Данные переданы не из Telegram")

    return init_data


def parse_validate_raw(raw_str: str) -> dict:
    data = {}
    for line in raw_str.splitlines():
        if not line or "=" not in line:
            continue
        key, val = line.split("=", 1)
        if key == "user":
            data[key] = json.loads(val)
        else:
            data[key] = val
    return data


def create_tokens(member_id: int, telegram_id: int) -> Dict[str, str]:
    now = datetime.utcnow()
    member_id = str(member_id)
    access_payload = {
        "id": member_id,
        "telegram_id": telegram_id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    refresh_payload = {
        "id": member_id,
        "telegram_id": telegram_id,
        "iat": now,
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }
    access = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    refresh = jwt.encode(refresh_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return {"access": access, "refresh": refresh}


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


async def get_current_member(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Member:
    data = decode_token(creds.credentials)
    if not data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = await db.get(Member, data["id"])
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user
