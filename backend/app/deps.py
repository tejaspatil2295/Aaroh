import uuid
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import User, WorkspaceMember
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user_id = decode_access_token(creds.credentials)
    user = db.get(User, user_id) if user_id else None
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return user


@dataclass
class Ctx:
    """Request context: who is acting and in which workspace."""

    user: User
    workspace_id: uuid.UUID
    role: str
    db: Session

    @property
    def user_id(self) -> uuid.UUID:
        return self.user.id


def get_ctx(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_workspace_id: str | None = Header(default=None),
) -> Ctx:
    q = select(WorkspaceMember).where(WorkspaceMember.user_id == user.id)
    if x_workspace_id:
        try:
            q = q.where(WorkspaceMember.workspace_id == uuid.UUID(x_workspace_id))
        except ValueError:
            raise HTTPException(400, "Invalid workspace id")
    else:
        q = q.order_by(WorkspaceMember.created_at)
    m = db.scalars(q).first()
    if not m:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this workspace")
    return Ctx(user=user, workspace_id=m.workspace_id, role=m.role, db=db)
