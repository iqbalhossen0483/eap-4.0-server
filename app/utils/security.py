import asyncio
import bcrypt
from datetime import datetime, timedelta, timezone
import jwt
from app.config import settings


# Sync bcrypt helpers — called only via run_in_executor, never directly in async code
def _hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


async def hash_password(plain: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _hash, plain)


async def verify_password(plain: str, hashed: str) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _verify, plain, hashed)


def create_access_token(payload: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({**payload, "exp": expire}, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
