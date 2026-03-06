"""推送通道管理 API"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

from core.database import get_db, PushChannel, User
from core.response import APIResponse
from api.auth import require_permissions
from services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/push", tags=["push"])

SUPPORTED_TYPES = ["webhook", "wecom", "email", "dingtalk"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PushChannelCreate(BaseModel):
    channel_type: str
    channel_name: str
    target: str
    config_json: Optional[str] = None
    enabled: int = 1


class PushChannelUpdate(BaseModel):
    channel_name: Optional[str] = None
    target: Optional[str] = None
    config_json: Optional[str] = None
    enabled: Optional[int] = None


@router.get("/channels")
async def list_channels(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("view_push")),
):
    """获取推送通道列表"""
    channels = db.query(PushChannel).order_by(PushChannel.created_at.desc()).all()
    return APIResponse.success([
        {
            "id": c.id,
            "channel_type": c.channel_type,
            "channel_name": c.channel_name,
            "target": c.target,
            "config_json": c.config_json,
            "enabled": c.enabled,
            "created_at": c.created_at.isoformat().replace("+00:00", "Z") if c.created_at else None,
            "updated_at": c.updated_at.isoformat().replace("+00:00", "Z") if c.updated_at else None,
        }
        for c in channels
    ])


@router.post("/channels")
async def create_channel(
    data: PushChannelCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("manage_push")),
):
    """创建推送通道"""
    if data.channel_type not in SUPPORTED_TYPES:
        raise HTTPException(400, f"不支持的通道类型，可选: {', '.join(SUPPORTED_TYPES)}")

    existing = db.query(PushChannel).filter(PushChannel.channel_name == data.channel_name).first()
    if existing:
        raise HTTPException(400, "通道名称已存在")

    trace_id = getattr(request.state, "trace_id", None) or str(uuid.uuid4())

    channel = PushChannel(
        channel_type=data.channel_type,
        channel_name=data.channel_name,
        target=data.target,
        config_json=data.config_json,
        enabled=data.enabled,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)

    AuditService.log(
        db=db,
        actor=str(current_user.username),
        action="create_push_channel",
        target=data.channel_name,
        target_type="push_channel",
        trace_id=trace_id,
    )

    return APIResponse.success(
        {"id": channel.id, "channel_name": channel.channel_name},
        message="推送通道已创建",
    )


@router.put("/channels/{channel_id}")
async def update_channel(
    channel_id: int,
    data: PushChannelUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("manage_push")),
):
    """更新推送通道"""
    channel = db.query(PushChannel).filter(PushChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(404, "通道不存在")

    if data.channel_name is not None:
        channel.channel_name = data.channel_name
    if data.target is not None:
        channel.target = data.target
    if data.config_json is not None:
        channel.config_json = data.config_json
    if data.enabled is not None:
        channel.enabled = data.enabled
    channel.updated_at = _utc_now()

    db.commit()

    trace_id = getattr(request.state, "trace_id", None) or str(uuid.uuid4())
    AuditService.log(
        db=db,
        actor=str(current_user.username),
        action="update_push_channel",
        target=str(channel_id),
        target_type="push_channel",
        trace_id=trace_id,
    )

    return APIResponse.success(None, message="更新成功")


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("manage_push")),
):
    """删除推送通道"""
    channel = db.query(PushChannel).filter(PushChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(404, "通道不存在")

    name = channel.channel_name
    db.delete(channel)
    db.commit()

    trace_id = getattr(request.state, "trace_id", None) or str(uuid.uuid4())
    AuditService.log(
        db=db,
        actor=str(current_user.username),
        action="delete_push_channel",
        target=name,
        target_type="push_channel",
        trace_id=trace_id,
    )

    return APIResponse.success(None, message="删除成功")


@router.post("/channels/{channel_id}/test")
async def test_channel(
    channel_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("manage_push")),
):
    """测试推送通道（模拟发送）"""
    channel = db.query(PushChannel).filter(PushChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(404, "通道不存在")

    trace_id = getattr(request.state, "trace_id", None) or str(uuid.uuid4())

    # 模拟发送逻辑：实际部署时替换为真实 webhook/email 调用
    test_result = {
        "channel_id": channel.id,
        "channel_type": channel.channel_type,
        "target": channel.target,
        "test_message": f"[Aimiguan 测试] 来自通道 '{channel.channel_name}' 的推送验证",
        "status": "simulated_success",
    }

    AuditService.log(
        db=db,
        actor=str(current_user.username),
        action="test_push_channel",
        target=str(channel_id),
        target_type="push_channel",
        trace_id=trace_id,
    )

    return APIResponse.success(test_result, message="测试推送已模拟完成")
