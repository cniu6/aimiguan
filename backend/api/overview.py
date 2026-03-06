"""
Overview 聚合接口
为防御仪表盘和探测仪表盘提供综合指标、趋势和待办统计
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from api.auth import require_permissions
from core.database import (
    Asset,
    ExecutionTask,
    ScanFinding,
    ScanTask,
    ThreatEvent,
    User,
    get_db,
)

router = APIRouter(prefix="/api/v1/overview", tags=["overview"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_z(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


# ──────────────────────────────────────────────────────────
# GET /api/v1/overview/metrics
# ──────────────────────────────────────────────────────────

@router.get("/metrics")
async def get_metrics(
    request: Request,
    current_user: User = Depends(require_permissions("view_events")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    系统核心指标聚合：
    - 今日新增告警数
    - 待审批事件数
    - 封禁成功数（今日）
    - 总资产数 / 启用资产数
    - 扫描任务数（运行中 / 今日）
    - 漏洞统计（总数 / 高危数）
    """
    now = _utc_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # ── 防御侧 ──
    today_alerts = db.query(func.count(ThreatEvent.id)).filter(
        ThreatEvent.created_at >= today_start
    ).scalar() or 0

    pending_events = db.query(func.count(ThreatEvent.id)).filter(
        ThreatEvent.status == "PENDING"
    ).scalar() or 0

    # 高危（ai_score >= 80）待处理
    high_risk_pending = db.query(func.count(ThreatEvent.id)).filter(
        ThreatEvent.status == "PENDING",
        ThreatEvent.ai_score >= 80,
    ).scalar() or 0

    # 今日封禁成功
    today_blocked = db.query(func.count(ExecutionTask.id)).filter(
        ExecutionTask.state == "SUCCESS",
        ExecutionTask.ended_at >= today_start,
    ).scalar() or 0

    # 执行失败（需人工介入）
    manual_required = db.query(func.count(ExecutionTask.id)).filter(
        ExecutionTask.state == "MANUAL_REQUIRED",
    ).scalar() or 0

    # ── 探测侧 ──
    total_assets = db.query(func.count(Asset.id)).scalar() or 0
    enabled_assets = db.query(func.count(Asset.id)).filter(
        Asset.enabled == 1
    ).scalar() or 0

    running_tasks = db.query(func.count(ScanTask.id)).filter(
        ScanTask.state == "RUNNING"
    ).scalar() or 0

    today_tasks = db.query(func.count(ScanTask.id)).filter(
        ScanTask.created_at >= today_start
    ).scalar() or 0

    total_findings = db.query(func.count(ScanFinding.id)).scalar() or 0
    high_findings = db.query(func.count(ScanFinding.id)).filter(
        ScanFinding.severity == "HIGH"
    ).scalar() or 0
    medium_findings = db.query(func.count(ScanFinding.id)).filter(
        ScanFinding.severity == "MEDIUM"
    ).scalar() or 0

    return {
        "code": 0,
        "data": {
            "defense": {
                "today_alerts": today_alerts,
                "pending_events": pending_events,
                "high_risk_pending": high_risk_pending,
                "today_blocked": today_blocked,
                "manual_required": manual_required,
                # 封禁成功率（今日有告警时计算）
                "block_success_rate": round(today_blocked / today_alerts * 100, 1) if today_alerts > 0 else 0,
            },
            "probe": {
                "total_assets": total_assets,
                "enabled_assets": enabled_assets,
                "running_tasks": running_tasks,
                "today_tasks": today_tasks,
                "total_findings": total_findings,
                "high_findings": high_findings,
                "medium_findings": medium_findings,
            },
            "generated_at": _iso_z(now),
        },
    }


# ──────────────────────────────────────────────────────────
# GET /api/v1/overview/trends
# ──────────────────────────────────────────────────────────

@router.get("/trends")
async def get_trends(
    range: str = "7d",
    current_user: User = Depends(require_permissions("view_events")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    趋势数据：
    - 告警趋势（按天）
    - 扫描任务趋势（按天）
    支持 range: 24h / 7d / 30d
    """
    now = _utc_now()

    if range == "24h":
        days = 1
        bucket_hours = 1
    elif range == "30d":
        days = 30
        bucket_hours = 24
    else:  # 7d
        days = 7
        bucket_hours = 24

    since = now - timedelta(days=days)

    # 告警趋势：按天聚合
    alert_rows = (
        db.query(
            func.date(ThreatEvent.created_at).label("day"),
            func.count(ThreatEvent.id).label("cnt"),
        )
        .filter(ThreatEvent.created_at >= since)
        .group_by(func.date(ThreatEvent.created_at))
        .order_by(func.date(ThreatEvent.created_at))
        .all()
    )

    # 高危告警趋势
    high_alert_rows = (
        db.query(
            func.date(ThreatEvent.created_at).label("day"),
            func.count(ThreatEvent.id).label("cnt"),
        )
        .filter(
            ThreatEvent.created_at >= since,
            ThreatEvent.ai_score >= 80,
        )
        .group_by(func.date(ThreatEvent.created_at))
        .order_by(func.date(ThreatEvent.created_at))
        .all()
    )

    # 扫描任务趋势
    task_rows = (
        db.query(
            func.date(ScanTask.created_at).label("day"),
            func.count(ScanTask.id).label("cnt"),
        )
        .filter(ScanTask.created_at >= since)
        .group_by(func.date(ScanTask.created_at))
        .order_by(func.date(ScanTask.created_at))
        .all()
    )

    def _fill_days(rows: list, since: datetime, days: int) -> List[Dict]:
        """按天补齐缺失的日期（值为 0）"""
        row_map = {str(r.day): r.cnt for r in rows}
        result = []
        for i in range(days):
            day = (since + timedelta(days=i)).strftime("%Y-%m-%d")
            result.append({"date": day, "count": row_map.get(day, 0)})
        return result

    return {
        "code": 0,
        "data": {
            "range": range,
            "alert_trend": _fill_days(alert_rows, since, days),
            "high_alert_trend": _fill_days(high_alert_rows, since, days),
            "task_trend": _fill_days(task_rows, since, days),
        },
    }


# ──────────────────────────────────────────────────────────
# GET /api/v1/overview/todos
# ──────────────────────────────────────────────────────────

@router.get("/todos")
async def get_todos(
    current_user: User = Depends(require_permissions("view_events")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    待办摘要：
    - 高优先级待审批事件 Top 5（按 ai_score 降序）
    - 失败任务 Top 5（执行任务 MANUAL_REQUIRED）
    - 高危漏洞发现 Top 5
    """
    # 高优先级待审批事件
    pending_top = (
        db.query(ThreatEvent)
        .filter(ThreatEvent.status == "PENDING")
        .order_by(ThreatEvent.ai_score.desc(), ThreatEvent.created_at.desc())
        .limit(5)
        .all()
    )

    # MANUAL_REQUIRED 任务（需人工介入）
    failed_tasks = (
        db.query(ExecutionTask)
        .filter(ExecutionTask.state == "MANUAL_REQUIRED")
        .order_by(ExecutionTask.updated_at.desc())
        .limit(5)
        .all()
    )

    # 高危漏洞
    high_findings = (
        db.query(ScanFinding)
        .filter(ScanFinding.severity == "HIGH", ScanFinding.status == "NEW")
        .order_by(ScanFinding.created_at.desc())
        .limit(5)
        .all()
    )

    def _event_to_dict(e: ThreatEvent) -> Dict:
        return {
            "id": e.id,
            "ip": e.ip,
            "source": e.source,
            "ai_score": e.ai_score,
            "ai_reason": e.ai_reason,
            "status": e.status,
            "created_at": _iso_z(e.created_at),
        }

    def _task_to_dict(t: ExecutionTask) -> Dict:
        return {
            "id": t.id,
            "event_id": t.event_id,
            "action": t.action,
            "state": t.state,
            "retry_count": t.retry_count,
            "error_message": t.error_message,
            "updated_at": _iso_z(t.updated_at),
        }

    def _finding_to_dict(f: ScanFinding) -> Dict:
        return {
            "id": f.id,
            "asset": f.asset,
            "port": f.port,
            "service": f.service,
            "cve": f.cve,
            "severity": f.severity,
            "status": f.status,
            "created_at": _iso_z(f.created_at),
        }

    return {
        "code": 0,
        "data": {
            "pending_events": [_event_to_dict(e) for e in pending_top],
            "failed_tasks": [_task_to_dict(t) for t in failed_tasks],
            "high_findings": [_finding_to_dict(f) for f in high_findings],
            "counts": {
                "pending_events": db.query(func.count(ThreatEvent.id)).filter(ThreatEvent.status == "PENDING").scalar() or 0,
                "manual_required": db.query(func.count(ExecutionTask.id)).filter(ExecutionTask.state == "MANUAL_REQUIRED").scalar() or 0,
                "high_findings_new": db.query(func.count(ScanFinding.id)).filter(ScanFinding.severity == "HIGH", ScanFinding.status == "NEW").scalar() or 0,
            },
        },
    }


# ──────────────────────────────────────────────────────────
# GET /api/v1/overview/defense-stats
# 防御侧聚合统计（威胁等级分布 / 来源分布 / TOP IP）
# ──────────────────────────────────────────────────────────

@router.get("/defense-stats")
async def get_defense_stats(
    range: str = "7d",
    current_user: User = Depends(require_permissions("view_events")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    防御侧聚合统计（对应 ai_lzx vuetify_index.html 的图表数据）
    - 威胁等级分布
    - 来源/服务分布
    - TOP 10 攻击 IP
    - 7天/24h 告警趋势
    """
    now = _utc_now()
    days = 30 if range == "30d" else (1 if range == "24h" else 7)
    since = now - timedelta(days=days)

    # 威胁等级分布（按 ai_score 分段）
    threat_level_dist = []
    ranges_def = [
        ("CRITICAL", 90, 100),
        ("HIGH", 70, 89),
        ("MEDIUM", 40, 69),
        ("LOW", 0, 39),
    ]
    for label, lo, hi in ranges_def:
        cnt = db.query(func.count(ThreatEvent.id)).filter(
            ThreatEvent.created_at >= since,
            ThreatEvent.ai_score >= lo,
            ThreatEvent.ai_score <= hi,
        ).scalar() or 0
        threat_level_dist.append({"level": label, "count": cnt})

    # 来源/服务分布
    service_rows = (
        db.query(
            ThreatEvent.service_name,
            func.count(ThreatEvent.id).label("cnt"),
        )
        .filter(ThreatEvent.created_at >= since, ThreatEvent.service_name.isnot(None))
        .group_by(ThreatEvent.service_name)
        .order_by(func.count(ThreatEvent.id).desc())
        .limit(10)
        .all()
    )
    service_dist = [
        {"service": r.service_name or "unknown", "count": r.cnt}
        for r in service_rows
    ]

    # TOP 10 攻击 IP
    top_ip_rows = (
        db.query(
            ThreatEvent.ip,
            func.count(ThreatEvent.id).label("cnt"),
            func.max(ThreatEvent.ai_score).label("max_score"),
        )
        .filter(ThreatEvent.created_at >= since)
        .group_by(ThreatEvent.ip)
        .order_by(func.count(ThreatEvent.id).desc())
        .limit(10)
        .all()
    )
    top_ips = [
        {"ip": r.ip, "count": r.cnt, "max_score": r.max_score}
        for r in top_ip_rows
    ]

    # 总计
    total = db.query(func.count(ThreatEvent.id)).filter(
        ThreatEvent.created_at >= since
    ).scalar() or 0

    high_total = db.query(func.count(ThreatEvent.id)).filter(
        ThreatEvent.created_at >= since,
        ThreatEvent.ai_score >= 80,
    ).scalar() or 0

    return {
        "code": 0,
        "data": {
            "range": range,
            "total": total,
            "high_total": high_total,
            "threat_level_dist": threat_level_dist,
            "service_dist": service_dist,
            "top_ips": top_ips,
        },
    }
