from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, timezone
import uuid

from core.database import (
    get_db, AIReport, ThreatEvent, ExecutionTask, ScanTask, ScanFinding, User,
)
from core.response import APIResponse
from api.auth import require_permissions
from services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/report", tags=["report"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GenerateReportRequest(BaseModel):
    report_type: str  # daily, weekly, event, scan
    scope: Optional[str] = None


def _build_defense_summary(db: Session, since: datetime) -> str:
    total = db.query(func.count(ThreatEvent.id)).filter(ThreatEvent.created_at >= since).scalar() or 0
    pending = db.query(func.count(ThreatEvent.id)).filter(
        ThreatEvent.created_at >= since, ThreatEvent.status == "PENDING"
    ).scalar() or 0
    high_risk = db.query(func.count(ThreatEvent.id)).filter(
        ThreatEvent.created_at >= since, ThreatEvent.ai_score >= 80
    ).scalar() or 0
    blocked = db.query(func.count(ExecutionTask.id)).filter(
        ExecutionTask.state == "SUCCESS", ExecutionTask.ended_at >= since
    ).scalar() or 0

    top_ips_rows = (
        db.query(ThreatEvent.ip, func.count(ThreatEvent.id).label("cnt"))
        .filter(ThreatEvent.created_at >= since)
        .group_by(ThreatEvent.ip)
        .order_by(func.count(ThreatEvent.id).desc())
        .limit(5)
        .all()
    )
    top_ips = ", ".join(f"{r.ip}({r.cnt}次)" for r in top_ips_rows) if top_ips_rows else "无"

    lines = [
        f"告警总数: {total}",
        f"待处理: {pending}",
        f"高危(AI≥80): {high_risk}",
        f"成功封禁: {blocked}",
        f"TOP攻击IP: {top_ips}",
    ]
    return " | ".join(lines)


def _build_scan_summary(db: Session, since: datetime) -> str:
    total_tasks = db.query(func.count(ScanTask.id)).filter(ScanTask.created_at >= since).scalar() or 0
    completed = db.query(func.count(ScanTask.id)).filter(
        ScanTask.state == "REPORTED", ScanTask.created_at >= since
    ).scalar() or 0
    failed = db.query(func.count(ScanTask.id)).filter(
        ScanTask.state == "FAILED", ScanTask.created_at >= since
    ).scalar() or 0
    total_findings = db.query(func.count(ScanFinding.id)).filter(ScanFinding.created_at >= since).scalar() or 0
    high_findings = db.query(func.count(ScanFinding.id)).filter(
        ScanFinding.severity == "HIGH", ScanFinding.created_at >= since
    ).scalar() or 0

    lines = [
        f"扫描任务: {total_tasks}(完成{completed}/失败{failed})",
        f"发现漏洞: {total_findings}(高危{high_findings})",
    ]
    return " | ".join(lines)


@router.post("/generate")
async def generate_report(
    req: GenerateReportRequest,
    request: Request,
    current_user: User = Depends(require_permissions("generate_report")),
    db: Session = Depends(get_db),
):
    """基于真实数据生成报告摘要"""
    trace_id = getattr(request.state, "trace_id", None) or str(uuid.uuid4())
    now = _utc_now()

    if req.report_type == "daily":
        since = now - timedelta(days=1)
        label = "日报"
    elif req.report_type == "weekly":
        since = now - timedelta(weeks=1)
        label = "周报"
    elif req.report_type == "scan":
        since = now - timedelta(days=1)
        label = "扫描报告"
    else:
        since = now - timedelta(days=1)
        label = req.report_type

    defense_summary = _build_defense_summary(db, since)
    scan_summary = _build_scan_summary(db, since)
    summary = f"[{label}] 防御: {defense_summary} | 探测: {scan_summary}"

    report = AIReport(
        report_type=req.report_type,
        scope=req.scope or "全局",
        summary=summary,
        detail_path=f"/reports/{now.strftime('%Y%m%d_%H%M%S')}_{req.report_type}.md",
        trace_id=trace_id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    AuditService.log(
        db=db,
        actor=str(current_user.username),
        action="generate_report",
        target=str(report.id),
        target_type="report",
        trace_id=trace_id,
    )

    return APIResponse.success(
        {"report_id": report.id, "summary": summary},
        message=f"{label}已生成",
        trace_id=trace_id,
    )


@router.get("/reports")
async def get_reports(
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    """获取报告列表"""
    if page < 1:
        page = 1
    query = db.query(AIReport)
    total = query.count()
    reports = query.order_by(AIReport.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return APIResponse.success(
        {
            "total": total,
            "page": page,
            "items": [
                {
                    "id": item.id,
                    "report_type": item.report_type,
                    "scope": item.scope,
                    "summary": item.summary,
                    "detail_path": item.detail_path,
                    "format": item.format,
                    "trace_id": item.trace_id,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                }
                for item in reports
            ],
        }
    )


@router.get("/reports/{report_id}")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    """获取报告详情"""
    report = db.query(AIReport).filter(AIReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return APIResponse.success(
        {
            "id": report.id,
            "report_type": report.report_type,
            "scope": report.scope,
            "summary": report.summary,
            "detail_path": report.detail_path,
            "format": report.format,
            "trace_id": report.trace_id,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }
    )
