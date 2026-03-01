"""推送通道管理 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from backend.core.database import get_db, PushChannel
from backend.services.push_service import PushService

router = APIRouter(prefix="/api/v1/push", tags=["推送通道"])


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
async def list_channels(db: Session = Depends(get_db)):
    """获取推送通道列表"""
    channels = db.query(PushChannel).all()
    return {"data": [
        {
            "id": c.id,
            "channel_type": c.channel_type,
            "channel_name": c.channel_name,
            "target": c.target,
            "enabled": c.enabled,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in channels
    ]}


@router.post("/channels")
async def create_channel(data: PushChannelCreate, db: Session = Depends(get_db)):
    """创建推送通道"""
    if data.channel_type not in ["webhook", "wecom"]:
        raise HTTPException(400, "不支持的通道类型")
    
    existing = db.query(PushChannel).filter(PushChannel.channel_name == data.channel_name).first()
    if existing:
        raise HTTPException(400, "通道名称已存在")
    
    channel = PushChannel(
        channel_type=data.channel_type,
        channel_name=data.channel_name,
        target=data.target,
        config_json=data.config_json,
        enabled=data.enabled
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return {"id": channel.id, "message": "创建成功"}


@router.put("/channels/{channel_id}")
async def update_channel(channel_id: int, data: PushChannelUpdate, db: Session = Depends(get_db)):
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
    
    db.commit()
    return {"message": "更新成功"}


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    """删除推送通道"""
    channel = db.query(PushChannel).filter(PushChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(404, "通道不存在")
    
    db.delete(channel)
    db.commit()
    return {"message": "删除成功"}


@router.post("/channels/{channel_id}/test")
async def test_channel(channel_id: int, db: Session = Depends(get_db)):
    """测试推送通道"""
    channel = db.query(PushChannel).filter(PushChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(404, "通道不存在")
    
    test_message = f"[测试消息] 来自 {channel.channel_name} 的推送测试"
    success = await PushService.send_alert(db, channel_id, test_message)
    
    if success:
        return {"message": "测试成功", "status": "ok"}
    else:
        raise HTTPException(500, "推送失败，请检查通道配置")
