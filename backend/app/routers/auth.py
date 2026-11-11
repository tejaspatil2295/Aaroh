import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..defaults import DEFAULT_AI_PERMISSIONS, DEFAULT_PREFERENCES
from ..models import RefreshToken, User, UserSettings, Workspace, WorkspaceMember
from ..schemas import LoginIn, RefreshIn, RegisterIn, TokenOut
from ..security import create_access_token, hash_password, hash_token, new_refresh_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE = "aaroh_refresh"

# Simple in-process rate limiter for credential endpoints (per IP). Use Redis when scaling out.
_attempts: dict[str, deque] = defaultdict(deque)


def _rate_limit(request: Request, limit: int = 10, window: int = 60) -> None:
    if get_settings().environment == "test":
        return
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    q = _attempts[key]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, try again in a minute")
    q.append(now)


def create_user(db: Session, email: str, password: str, full_name: str = "") -> User:
    user = User(email=email.lower(), password_hash=hash_password(password), full_name=full_name)
    db.add(user)
    db.flush()
    ws = Workspace(name="Personal", kind="personal", created_by=user.id)
    db.add(ws)
    db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner"))
    db.add(UserSettings(user_id=user.id, preferences=dict(DEFAULT_PREFERENCES), ai_permissions=dict(DEFAULT_AI_PERMISSIONS)))
    return user


def _issue(db: Session, user: User, response: Response, request: Request, family: uuid.UUID | None = None) -> TokenOut:
    s = get_settings()
    raw = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            family_id=family or uuid.uuid4(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=s.refresh_token_days),
            user_agent=(request.headers.get("user-agent") or "")[:255],
        )
    )
    db.commit()
    # Web clients rely on this httpOnly cookie; native clients store the body token in secure storage.
    response.set_cookie(
        COOKIE, raw, httponly=True, secure=s.cookie_secure, samesite="strict",
        max_age=s.refresh_token_days * 86400, path="/api/v1/auth",
    )
    return TokenOut(access_token=create_access_token(user.id), refresh_token=raw, expires_in=s.access_token_minutes * 60)


@router.post("/register", response_model=TokenOut, status_code=201)
def register(payload: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    _rate_limit(request)
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(409, "An account with this email already exists")
    user = create_user(db, payload.email, payload.password, payload.full_name)
    return _issue(db, user, response, request)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    _rate_limit(request)
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return _issue(db, user, response, request)


@router.post("/refresh", response_model=TokenOut)
def refresh(
    request: Request,
    response: Response,
    payload: RefreshIn | None = None,
    cookie_token: str | None = Cookie(default=None, alias=COOKIE),
    db: Session = Depends(get_db),
):
    raw = (payload.refresh_token if payload else None) or cookie_token
    if not raw:
        raise HTTPException(401, "Missing refresh token")
    rt = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
    now = datetime.now(timezone.utc)
    if not rt:
        raise HTTPException(401, "Invalid refresh token")
    if rt.revoked_at is not None:
        # Reuse of a rotated token: assume theft and revoke the whole session family.
        db.execute(update(RefreshToken).where(RefreshToken.family_id == rt.family_id).values(revoked_at=now))
        db.commit()
        raise HTTPException(401, "Refresh token reuse detected; please sign in again")
    if rt.expires_at < now:
        raise HTTPException(401, "Refresh token expired")
    rt.revoked_at = now
    user = db.get(User, rt.user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "Account disabled")
    return _issue(db, user, response, request, family=rt.family_id)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    payload: RefreshIn | None = None,
    cookie_token: str | None = Cookie(default=None, alias=COOKIE),
    db: Session = Depends(get_db),
):
    raw = (payload.refresh_token if payload else None) or cookie_token
    if raw:
        rt = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
        if rt:
            db.execute(
                update(RefreshToken).where(RefreshToken.family_id == rt.family_id).values(revoked_at=datetime.now(timezone.utc))
            )
            db.commit()
    response.delete_cookie(COOKIE, path="/api/v1/auth")

