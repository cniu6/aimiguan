from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import ipaddress
import re

from core.database import get_db, ScanTask, ScanFinding, Asset
from core.response import APIResponse
from services.scanner import scanner
from services.audit_service import AuditService
from api.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/scan", tags=["scan"])

# ===== 扫描 Profile 白名单（禁止前端自由拼接危险参数）=====
SCAN_PROFILES = {
    "quick": {
        "name": "快速扫描",
        "description": "仅扫描常用端口（Top 100），速度最快",
        "nmap_args": ["-sS", "-T4", "-F"],
        "estimated_seconds": 30,
        "risk_level": "low",
    },
    "default": {
        "name": "标准扫描",
        "description": "扫描 1-1000 端口，含服务版本探测",
        "nmap_args": ["-sS", "-sV", "-T4", "-p", "1-1000"],
        "estimated_seconds": 120,
        "risk_level": "low",
    },
    "comprehensive": {
        "name": "全面扫描",
        "description": "全端口扫描，含 OS 探测和脚本引擎（耗时较长）",
        "nmap_args": ["-sS", "-sV", "-O", "-A", "-T4", "-p-"],
        "estimated_seconds": 600,
        "risk_level": "medium",
        "required_role": "admin",
    },
    "vuln": {
        "name": "漏洞扫描",
        "description": "使用 NSE vuln 脚本集进行漏洞检测",
        "nmap_args": ["-sV", "--script=vuln", "-T4"],
        "estimated_seconds": 300,
        "risk_level": "medium",
        "required_role": "operator",
    },
}

ASSET_TARGET_TYPES = {"IP", "CIDR", "DOMAIN"}
ASSET_DEFAULT_TAG_BY_TYPE = {
    "IP": "ip",
    "CIDR": "cidr",
    "DOMAIN": "domain",
}
DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?!-)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*$"
)


def _actor_name(current_user: object) -> str:
    if isinstance(current_user, dict):
        actor = current_user.get("username")
    else:
        actor = getattr(current_user, "username", None)
    return str(actor or "unknown")


def _normalize_target_type(target_type: str) -> str:
    normalized = target_type.strip().upper()
    if normalized not in ASSET_TARGET_TYPES:
        raise HTTPException(status_code=400, detail=f"无效 target_type: {target_type}. 仅支持 IP/CIDR/DOMAIN")
    return normalized


def _normalize_target(target: str, target_type: str) -> str:
    value = target.strip()
    if not value:
        raise HTTPException(status_code=400, detail="目标不能为空")

    if target_type == "IP":
        try:
            return str(ipaddress.ip_address(value))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="IP 格式不合法") from exc

    if target_type == "CIDR":
        if "/" not in value:
            raise HTTPException(status_code=400, detail="CIDR 必须包含掩码，例如 10.0.0.0/24")
        try:
            return str(ipaddress.ip_network(value, strict=False))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="CIDR 格式不合法") from exc

    normalized = value.lower().rstrip(".")
    if not DOMAIN_PATTERN.fullmatch(normalized):
        raise HTTPException(status_code=400, detail="域名格式不合法")
    return normalized


def _normalize_tags(tags: Optional[str], target_type: str) -> str:
    if tags is None or not tags.strip():
        return ASSET_DEFAULT_TAG_BY_TYPE[target_type]

    raw_tags = tags.replace("，", ",").split(",")
    normalized_tags: List[str] = []
    for raw in raw_tags:
        tag = raw.strip().lower()
        if not tag:
            continue
        if tag not in normalized_tags:
            normalized_tags.append(tag)

    if not normalized_tags:
        return ASSET_DEFAULT_TAG_BY_TYPE[target_type]
    return ",".join(normalized_tags)


class CreateScanRequest(BaseModel):
    target: str = Field(..., description="扫描目标 (IP/CIDR/域名)")
    target_type: Optional[str] = Field(
        "host", description="目标类型: host/network/domain"
    )
    tool_name: Optional[str] = Field("nmap", description="扫描工具: nmap")
    profile: Optional[str] = Field(
        "default", description="扫描配置: quick/default/comprehensive/vuln"
    )
    script_set: Optional[str] = Field(None, description="NSE脚本集（仅 admin 可指定）")
    asset_id: Optional[int] = Field(None, description="关联资产ID")
    timeout_seconds: Optional[int] = Field(None, ge=30, le=3600, description="超时秒数（30-3600）")


class CreateAssetRequest(BaseModel):
    target: str = Field(..., description="目标 (IP/CIDR/域名)")
    target_type: str = Field("IP", description="类型: IP/CIDR/DOMAIN")
    tags: Optional[str] = Field(None, description="标签，逗号分隔")
    priority: Optional[int] = Field(5, ge=1, le=10, description="优先级 1-10")
    enabled: Optional[bool] = Field(True, description="是否启用")
    description: Optional[str] = Field(None, description="描述")


class UpdateAssetRequest(BaseModel):
    target_type: Optional[str] = Field(None, description="类型: IP/CIDR/DOMAIN")
    tags: Optional[str] = Field(None, description="标签，逗号分隔")
    priority: Optional[int] = Field(None, ge=1, le=10, description="优先级 1-10")
    enabled: Optional[bool] = Field(None, description="是否启用")
    description: Optional[str] = Field(None, description="描述")


class ScanTaskResponse(BaseModel):
    id: int
    target: str
    tool_name: Optional[str]
    state: str
    created_at: datetime


# ===== 扫描 Profile 查询 API =====


@router.get("/profiles")
async def get_scan_profiles(
    current_user: object = Depends(get_current_user),
):
    """获取允许的扫描配置模板列表（白名单，前端只能从此列表选择）"""
    user_role = "viewer"
    if isinstance(current_user, dict):
        user_role = current_user.get("role", "viewer")
    else:
        user_role = getattr(current_user, "role", "viewer")

    result = []
    for key, profile in SCAN_PROFILES.items():
        required_role = profile.get("required_role")
        available = True
        if required_role == "admin" and user_role not in ("admin",):
            available = False
        elif required_role == "operator" and user_role not in ("operator", "admin"):
            available = False
        result.append(
            {
                "key": key,
                "name": profile["name"],
                "description": profile["description"],
                "estimated_seconds": profile["estimated_seconds"],
                "risk_level": profile["risk_level"],
                "available": available,
            }
        )
    return APIResponse.success(result)


# ===== 资产管理 API =====


@router.post("/assets", response_model=dict)
async def create_asset(
    req: CreateAssetRequest,
    db: Session = Depends(get_db),
    current_user: object = Depends(require_role(["operator", "admin"])),
):
    """创建扫描资产"""
    normalized_target_type = _normalize_target_type(req.target_type)
    normalized_target = _normalize_target(req.target, normalized_target_type)
    normalized_tags = _normalize_tags(req.tags, normalized_target_type)

    # 检查是否已存在
    existing = db.query(Asset).filter(Asset.target == normalized_target).first()
    if existing:
        raise HTTPException(status_code=400, detail="资产已存在")

    asset = Asset(
        target=normalized_target,
        target_type=normalized_target_type,
        tags=normalized_tags,
        priority=req.priority,
        enabled=1 if req.enabled else 0,
        description=req.description,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    # 记录审计
    AuditService.log(
        db=db,
        actor=_actor_name(current_user),
        action="asset_create",
        target=f"asset:{asset.id}",
        target_type="asset",
        result="success",
        reason=f"创建资产: {normalized_target}",
    )

    return APIResponse.success(
        {
            "asset_id": asset.id,
            "target": asset.target,
            "target_type": asset.target_type,
            "tags": asset.tags,
            "priority": asset.priority,
            "enabled": bool(asset.enabled),
        },
        message="Asset created",
    )


@router.get("/assets")
async def get_assets(
    target_type: Optional[str] = None,
    enabled: Optional[bool] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: object = Depends(get_current_user),
):
    """获取资产列表（支持关键字搜索、类型筛选、启停筛选、分页）"""
    query = db.query(Asset)

    if target_type:
        normalized_target_type = _normalize_target_type(target_type)
        query = query.filter(Asset.target_type == normalized_target_type)
    if enabled is not None:
        query = query.filter(Asset.enabled == (1 if enabled else 0))
    if keyword:
        query = query.filter(Asset.target.contains(keyword.strip()))

    total = query.count()
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size
    assets = query.order_by(Asset.created_at.desc()).offset(offset).limit(page_size).all()

    return APIResponse.success(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": a.id,
                    "target": a.target,
                    "target_type": a.target_type,
                    "tags": a.tags,
                    "priority": a.priority,
                    "enabled": bool(a.enabled),
                    "description": a.description,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in assets
            ],
        }
    )


@router.get("/assets/{asset_id}")
async def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: object = Depends(get_current_user),
):
    """获取资产详情"""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return APIResponse.success(
        {
            "id": asset.id,
            "target": asset.target,
            "target_type": asset.target_type,
            "tags": asset.tags,
            "priority": asset.priority,
            "enabled": bool(asset.enabled),
            "description": asset.description,
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
            "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,
        }
    )


@router.put("/assets/{asset_id}")
async def update_asset(
    asset_id: int,
    req: UpdateAssetRequest,
    db: Session = Depends(get_db),
    current_user: object = Depends(require_role(["operator", "admin"])),
):
    """更新资产"""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if (
        req.target_type is None
        and req.tags is None
        and req.priority is None
        and req.enabled is None
        and req.description is None
    ):
        raise HTTPException(status_code=400, detail="至少提供一个可更新字段")

    if req.target_type is not None:
        normalized_target_type = _normalize_target_type(req.target_type)
        _normalize_target(str(asset.target), normalized_target_type)
        asset.target_type = normalized_target_type

    if req.tags is not None:
        asset.tags = _normalize_tags(req.tags, str(asset.target_type))
    if req.priority is not None:
        asset.priority = req.priority
    if req.enabled is not None:
        asset.enabled = 1 if req.enabled else 0
    if req.description is not None:
        asset.description = req.description

    db.commit()
    db.refresh(asset)

    AuditService.log(
        db=db,
        actor=_actor_name(current_user),
        action="asset_update",
        target=f"asset:{asset_id}",
        target_type="asset",
        result="success",
    )

    return APIResponse.success(message="Asset updated")


@router.delete("/assets/{asset_id}")
async def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: object = Depends(require_role(["admin"])),
):
    """删除资产"""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    db.delete(asset)
    db.commit()

    AuditService.log(
        db=db,
        actor=_actor_name(current_user),
        action="asset_delete",
        target=f"asset:{asset_id}",
        target_type="asset",
        result="success",
    )

    return APIResponse.success(message="Asset deleted")


@router.patch("/assets/{asset_id}/toggle")
async def toggle_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: object = Depends(require_role(["operator", "admin"])),
):
    """快捷启停资产"""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.enabled = 0 if asset.enabled else 1
    db.commit()

    AuditService.log(
        db=db,
        actor=_actor_name(current_user),
        action="asset_toggle",
        target=f"asset:{asset_id}",
        target_type="asset",
        result="success",
        reason=f"资产状态切换为: {'启用' if asset.enabled else '禁用'}",
    )

    return APIResponse.success({"enabled": bool(asset.enabled)}, message="Asset toggled")


# ===== 扫描任务 API =====


@router.post("/tasks")
async def create_scan_task(
    req: CreateScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: object = Depends(require_role(["operator", "admin"])),
):
    """创建扫描任务并立即调度执行"""

    # 验证 profile 白名单
    profile = req.profile or "default"
    if profile not in SCAN_PROFILES:
        raise HTTPException(
            status_code=400,
            detail=f"无效 profile: {profile}. 仅支持: {list(SCAN_PROFILES.keys())}",
        )

    # 权限校验：comprehensive/vuln profile 需要特定角色
    user_role = "viewer"
    if isinstance(current_user, dict):
        user_role = current_user.get("role", "viewer")
    else:
        user_role = getattr(current_user, "role", "viewer")

    required_role = SCAN_PROFILES[profile].get("required_role")
    if required_role == "admin" and user_role != "admin":
        raise HTTPException(status_code=403, detail=f"该扫描配置需要 admin 权限")
    if required_role == "operator" and user_role not in ("operator", "admin"):
        raise HTTPException(status_code=403, detail=f"该扫描配置需要 operator 权限")

    # 验证资产ID（如果提供）
    if req.asset_id:
        asset = db.query(Asset).filter(Asset.id == req.asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

    # 创建任务记录
    target_type = req.target_type or "host"
    tool_name = req.tool_name or "nmap"
    timeout_seconds = req.timeout_seconds or SCAN_PROFILES[profile]["estimated_seconds"] * 5

    task = ScanTask(
        asset_id=req.asset_id or 0,
        target=req.target,
        target_type=target_type,
        tool_name=tool_name,
        profile=profile,
        script_set=req.script_set,
        state="CREATED",
        timeout_seconds=timeout_seconds,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 异步调度扫描任务
    try:
        await scanner.schedule_scan(
            task_id=task.id,
            target=req.target,
            tool_name=tool_name,
            profile=profile,
            script_set=req.script_set,
            operator=_actor_name(current_user),
            timeout_seconds=timeout_seconds,
        )
    except RuntimeError as e:
        # 并发限制，任务仍创建但标记为等待
        task.state = "CREATED"  # 保持 CREATED 状态等待调度
        db.commit()
        return APIResponse.error(
            code=429,
            message=f"Scan task created but queued: {str(e)}",
            data={"task_id": task.id, "status": "queued"},
        )

    return APIResponse.success(
        {"task_id": task.id, "status": "scheduled"},
        message="Scan task created and scheduled",
    )


@router.get("/tasks")
async def get_scan_tasks(
    state: Optional[str] = None,
    profile: Optional[str] = None,
    target: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: object = Depends(get_current_user),
):
    """获取扫描任务列表（支持状态/配置/目标筛选、分页）"""
    query = db.query(ScanTask)
    if state:
        query = query.filter(ScanTask.state == state)
    if profile:
        query = query.filter(ScanTask.profile == profile)
    if target:
        query = query.filter(ScanTask.target.contains(target.strip()))

    total = query.count()
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size
    tasks = query.order_by(ScanTask.created_at.desc()).offset(offset).limit(page_size).all()

    return APIResponse.success(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": t.id,
                    "target": t.target,
                    "target_type": t.target_type,
                    "tool_name": t.tool_name,
                    "profile": t.profile,
                    "state": t.state,
                    "priority": t.priority,
                    "timeout_seconds": t.timeout_seconds,
                    "error_message": t.error_message,
                    "started_at": t.started_at.isoformat() if t.started_at else None,
                    "ended_at": t.ended_at.isoformat() if t.ended_at else None,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tasks
            ],
        }
    )


@router.get("/tasks/{task_id}")
async def get_scan_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: object = Depends(get_current_user),
):
    """获取扫描任务详情"""
    task = db.query(ScanTask).filter(ScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    findings = db.query(ScanFinding).filter(ScanFinding.scan_task_id == task_id).all()

    return APIResponse.success(
        {
            "task": {
                "id": task.id,
                "target": task.target,
                "target_type": task.target_type,
                "tool_name": task.tool_name,
                "profile": task.profile,
                "state": task.state,
                "priority": task.priority,
                "error_message": task.error_message,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "ended_at": task.ended_at.isoformat() if task.ended_at else None,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            },
            "findings": [
                {
                    "id": f.id,
                    "asset": f.asset,
                    "port": f.port,
                    "service": f.service,
                    "severity": f.severity,
                    "status": f.status,
                    "evidence": f.evidence,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in findings
            ],
        }
    )


@router.post("/tasks/{task_id}/cancel")
async def cancel_scan_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: object = Depends(require_role(["operator", "admin"])),
):
    """取消扫描任务"""
    task = db.query(ScanTask).filter(ScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.state not in ["CREATED", "DISPATCHED", "RUNNING"]:
        raise HTTPException(
            status_code=400, detail=f"Cannot cancel task in state: {task.state}"
        )

    success = await scanner.cancel_scan(task_id)

    if success:
        return APIResponse.success(message="Scan task cancelled")
    else:
        return APIResponse.error(code=500, message="Failed to cancel scan task")


@router.get("/tasks/{task_id}/status")
async def get_scan_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: object = Depends(get_current_user),
):
    """获取扫描任务实时状态"""
    task = db.query(ScanTask).filter(ScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 检查内存中的运行状态
    memory_status = scanner.get_task_status(task_id)

    return APIResponse.success(
        {
            "task_id": task_id,
            "state": task.state,
            "memory_status": memory_status,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "ended_at": task.ended_at.isoformat() if task.ended_at else None,
        }
    )


# ===== 扫描发现 API =====


@router.get("/findings")
async def get_findings(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    scan_task_id: Optional[int] = None,
    asset: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: object = Depends(get_current_user),
):
    """获取扫描发现列表（支持多维度筛选和分页）"""
    query = db.query(ScanFinding)

    if severity:
        query = query.filter(ScanFinding.severity == severity.upper())
    if status:
        query = query.filter(ScanFinding.status == status.upper())
    if scan_task_id:
        query = query.filter(ScanFinding.scan_task_id == scan_task_id)
    if asset:
        query = query.filter(ScanFinding.asset.contains(asset.strip()))

    total = query.count()
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size
    findings = query.order_by(ScanFinding.created_at.desc()).offset(offset).limit(page_size).all()

    return APIResponse.success(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": f.id,
                    "scan_task_id": f.scan_task_id,
                    "asset": f.asset,
                    "port": f.port,
                    "service": f.service,
                    "severity": f.severity,
                    "status": f.status,
                    "cve": f.cve,
                    "evidence": f.evidence[:300] if f.evidence else None,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in findings
            ],
        }
    )


@router.put("/findings/{finding_id}/status")
async def update_finding_status(
    finding_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: object = Depends(require_role(["operator", "admin"])),
):
    """更新发现项状态 (NEW/CONFIRMED/FALSE_POSITIVE/FIXED/IGNORED)"""
    finding = db.query(ScanFinding).filter(ScanFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    valid_statuses = ["NEW", "CONFIRMED", "FALSE_POSITIVE", "FIXED", "IGNORED"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}"
        )

    finding.status = status
    db.commit()

    AuditService.log(
        db=db,
        actor=_actor_name(current_user),
        action="finding_status_update",
        target=f"finding:{finding_id}",
        target_type="scan_finding",
        result="success",
        reason=f"状态更新为: {status}",
    )

    return APIResponse.success(message="Finding status updated")
