from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import hashlib
import os

from core.database import (
    get_db,
    User,
    Role,
    UserRole,
    Permission,
    RolePermission,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
security = HTTPBearer()
BLACKLISTED_TOKENS: set[str] = set()

SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed


def get_user_role(user: User, db: Session) -> str:
    """Get user's primary role name"""
    user_role = db.query(UserRole).filter(UserRole.user_id == user.id).first()
    if user_role:
        role = db.query(Role).filter(Role.id == user_role.role_id).first()
        if role:
            return str(role.name)
    return "viewer"


def get_user_permissions(user: User, db: Session) -> list[str]:
    rows = (
        db.query(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .filter(UserRole.user_id == user.id)
        .all()
    )
    names = {str(row[0]) for row in rows if row and row[0]}
    return sorted(names)


def require_permissions(*required_permissions: str):
    async def _permission_dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        permissions = set(get_user_permissions(current_user, db))
        missing = [name for name in required_permissions if name not in permissions]
        if missing:
            trace_id = getattr(request.state, "trace_id", None)
            raise HTTPException(status_code=403, detail={
                "error": "permission_denied",
                "message": f"缺少权限: {missing[0]}",
                "required_permission": missing[0],
                "user_roles": [get_user_role(current_user, db)],
                "trace_id": trace_id,
                "audit_logged": True,
            })
        return current_user

    return _permission_dependency


def require_role(allowed_roles: list[str]):
    """角色要求依赖"""
    async def _role_dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        user_role = get_user_role(current_user, db)
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"需要角色: {allowed_roles}, 当前角色: {user_role}"
            )
        return current_user
    return _role_dependency


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserInfo(BaseModel):
    username: str
    role: str


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    if not request.username or not request.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    user = db.query(User).filter(User.username == request.username.strip()).first()
    if user is None or getattr(user, "enabled", 0) != 1:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not verify_password(request.password, str(user.password_hash)):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    role = get_user_role(user, db)
    token_data = {
        "sub": user.username,
        "role": role,
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    return TokenResponse(
        access_token=access_token, user={"username": user.username, "role": role}
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    try:
        token = credentials.credentials
        if token in BLACKLISTED_TOKENS:
            raise HTTPException(status_code=401, detail="令牌已失效，请重新登录")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not isinstance(username, str) or not username:
            raise HTTPException(status_code=401, detail="无效的认证令牌")
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的认证令牌")

    user = db.query(User).filter(User.username == username).first()
    if user is None or getattr(user, "enabled", 0) != 1:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


@router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    role = get_user_role(current_user, db)
    token_data = {
        "sub": current_user.username,
        "role": role,
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return TokenResponse(
        access_token=access_token,
        user={"username": current_user.username, "role": role},
    )


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
):
    BLACKLISTED_TOKENS.add(credentials.credentials)
    return {"code": 0, "message": "退出登录成功"}


@router.get("/profile", response_model=UserInfo)
async def get_profile(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    role = get_user_role(current_user, db)
    return UserInfo(username=str(current_user.username), role=role)
