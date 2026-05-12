import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Annotated, Deque

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

# Простой rate-limit логина: окно 5 минут, in-memory.
# Для prod с несколькими репликами лучше Redis-based limiter, но для дипломной
# работы и одного инстанса это адекватная защита от брутфорса.
_LOGIN_WINDOW = timedelta(minutes=5)
_login_attempts: dict[str, Deque[datetime]] = defaultdict(deque)


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str


class TokenData(BaseModel):
    user_id: int
    role: str


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверные учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise credentials_exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exc
    return user


def require_role(*roles: str):
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
            )
        return current_user
    return _check


def _resolve_client_ip(request: Request) -> str:
    """Реальный IP клиента: за nginx читаем X-Forwarded-For/X-Real-IP.

    Без этого `request.client.host` за прокси отдаёт IP nginx-контейнера —
    общий для всех клиентов, и лимит блокирует вообще всех после N попыток
    с одного из них. Берём первый IP из X-Forwarded-For (наиболее близкий
    к клиенту), либо X-Real-IP.
    """
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.headers.get("X-Real-IP")
    if xri:
        return xri.strip()
    return request.client.host if request.client else "unknown"


def _check_login_rate_limit(client_ip: str) -> None:
    """Бросает 429, если с одного IP было больше N попыток за окно."""
    now = datetime.now(timezone.utc)
    cutoff = now - _LOGIN_WINDOW
    attempts = _login_attempts[client_ip]
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    if len(attempts) >= settings.login_rate_limit_per_5min:
        retry_after = int((attempts[0] + _LOGIN_WINDOW - now).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток входа. Попробуйте позже.",
            headers={"Retry-After": str(max(retry_after, 1))},
        )
    attempts.append(now)


@router.post("/login", response_model=Token, summary="Вход в систему")
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
):
    client_ip = _resolve_client_ip(request)
    _check_login_rate_limit(client_ip)

    result = await db.execute(select(User).where(User.login == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    token = create_access_token(user.id, user.role)
    logger.info("User %s logged in from %s", user.login, client_ip)
    return Token(access_token=token, token_type="bearer", role=user.role, name=user.name)


@router.get("/me", summary="Текущий пользователь")
async def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "name": current_user.name, "role": current_user.role, "login": current_user.login}
