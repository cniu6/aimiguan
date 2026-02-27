from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

from core.database import get_db, AIReport
from core.response import APIResponse

router = APIRouter(prefix="/api/v1/report", tags=["report"])


class GenerateReportRequest(BaseModel):
    report_type: str  # daily, weekly, event, scan
    scope: Optional[str] = None


@router.post("/generate")
async def generate_report(
    req: GenerateReportRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """生成 AI 报告"""
    # TODO: Call AI engine to generate report
    summary = f"Generated {req.report_type} report"
    trace_id = getattr(request.state, "trace_id", None) or str(uuid.uuid4())

    report = AIReport(
        report_type=req.report_type,
        scope=req.scope,
        summary=summary,
        detail_path=f"/reports/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md",
        trace_id=trace_id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return APIResponse.success(
        {"report_id": report.id}, message="Report generated", trace_id=trace_id
    )


@router.get("/reports")
async def get_reports(db: Session = Depends(get_db)):
    """获取报告列表"""
    reports = db.query(AIReport).order_by(AIReport.created_at.desc()).limit(50).all()
    return APIResponse.success(
        [
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
        ]
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
