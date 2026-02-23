from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from core.database import get_db, AIReport

router = APIRouter(prefix="/api/v1/report", tags=["report"])

class GenerateReportRequest(BaseModel):
    report_type: str  # daily, weekly, event, scan
    scope: Optional[str] = None

@router.post("/generate")
async def generate_report(req: GenerateReportRequest, db: Session = Depends(get_db)):
    """生成 AI 报告"""
    # TODO: Call AI engine to generate report
    summary = f"Generated {req.report_type} report"
    
    report = AIReport(
        report_type=req.report_type,
        scope=req.scope,
        summary=summary,
        detail_path=f"/reports/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return {"code": 0, "message": "Report generated", "data": {"report_id": report.id}}

@router.get("/reports")
async def get_reports(db: Session = Depends(get_db)):
    """获取报告列表"""
    reports = db.query(AIReport).order_by(AIReport.created_at.desc()).limit(50).all()
    return {"code": 0, "data": reports}

@router.get("/reports/{report_id}")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    """获取报告详情"""
    report = db.query(AIReport).filter(AIReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {"code": 0, "data": report}