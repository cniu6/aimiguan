"""
后台调度服务
定时执行 HFish 数据同步和 Nmap 扫描任务。

设计原则：
- 防御坚守（HFish 同步 + AI 评分 + 封禁执行）始终自动运行，无需任何手动开关。
- 主动探测（Nmap 扫描）由调度器按配置间隔自动执行，每次执行均创建 ScanTask 记录可追溯。
- 所有自动任务执行结果均写入 AuditLog（actor="scheduler"），确保全程可审计。
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from services.hfish_collector import hfish_collector
from services.nmap_scanner import nmap_scanner
from core.database import AuditLog, SessionLocal

logger = logging.getLogger(__name__)

SCHEDULER_ACTOR = "scheduler"


def _write_audit(db, action: str, target: str, result: str,
                 trace_id: str, error_message: Optional[str] = None,
                 target_type: str = "auto_task") -> None:
    """将调度器执行结果写入审计日志"""
    try:
        entry = AuditLog(
            actor=SCHEDULER_ACTOR,
            action=action,
            target=target,
            target_type=target_type,
            result=result,
            error_message=error_message,
            trace_id=trace_id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        logger.warning(f"审计日志写入失败: {e}")
        try:
            db.rollback()
        except Exception:
            pass


class SchedulerService:
    """后台任务调度器

    运行架构说明：
    - 防御坚守模式始终运行（HFish 同步 → ThreatEvent → AI 评分 → 审批执行）。
    - 主动探测通过此调度器按配置间隔自动触发 Nmap 扫描，每次扫描创建 ScanTask 记录。
    - 不存在"系统级主动/被动模式开关"，避免误操作导致资源持续消耗。
    """

    def __init__(self):
        self.running = False
        self.hfish_task: Optional[asyncio.Task] = None
        self.nmap_task: Optional[asyncio.Task] = None

    async def _hfish_sync_loop(self):
        """HFish 同步循环（防御坚守自动任务）"""
        logger.info("HFish 同步任务已启动（防御坚守自动运行）")

        while self.running:
            try:
                if hfish_collector.enabled:
                    trace_id = f"hfish_sync_{uuid.uuid4().hex[:8]}"
                    result = await hfish_collector.sync_once(trace_id)

                    db = SessionLocal()
                    try:
                        if result["success"]:
                            logger.info(f"HFish 同步成功: {result['message']}")
                            _write_audit(
                                db,
                                action="hfish_auto_sync",
                                target="hfish_collector",
                                result="SUCCESS",
                                trace_id=trace_id,
                                error_message=result.get("message"),
                            )
                        else:
                            logger.warning(f"HFish 同步失败: {result['message']}")
                            _write_audit(
                                db,
                                action="hfish_auto_sync",
                                target="hfish_collector",
                                result="FAILED",
                                trace_id=trace_id,
                                error_message=result.get("message"),
                            )
                    finally:
                        db.close()

                # 等待下一次同步
                await asyncio.sleep(hfish_collector.sync_interval)

            except asyncio.CancelledError:
                logger.info("HFish 同步任务被取消")
                break
            except Exception as e:
                logger.error(f"HFish 同步任务异常: {e}", exc_info=True)
                await asyncio.sleep(60)  # 出错后等待1分钟再重试

    async def _nmap_scan_loop(self):
        """Nmap 定时扫描循环（主动探测自动任务）

        每次扫描均通过 nmap_scanner.scan_target 创建 ScanTask 记录，
        并将调度执行结果写入 AuditLog，确保自动任务全程可追溯。
        """
        logger.info("Nmap 定时扫描任务已启动（主动探测自动任务）")

        while self.running:
            try:
                if nmap_scanner.enabled and nmap_scanner.ip_ranges:
                    db = SessionLocal()
                    try:
                        for ip_range in nmap_scanner.ip_ranges:
                            trace_id = f"nmap_auto_{uuid.uuid4().hex[:8]}"
                            logger.info(f"[自动调度] 开始扫描 {ip_range}，trace_id={trace_id}")

                            result = await nmap_scanner.scan_target(
                                target=ip_range,
                                profile="default",
                                db=db,
                                trace_id=trace_id,
                            )

                            if result["success"]:
                                logger.info(f"Nmap 自动扫描成功: {result['message']}")
                                _write_audit(
                                    db,
                                    action="nmap_auto_scan",
                                    target=ip_range,
                                    result="SUCCESS",
                                    trace_id=trace_id,
                                    error_message=result.get("message"),
                                    target_type="nmap_scan",
                                )
                            else:
                                logger.warning(f"Nmap 自动扫描失败: {result['message']}")
                                _write_audit(
                                    db,
                                    action="nmap_auto_scan",
                                    target=ip_range,
                                    result="FAILED",
                                    trace_id=trace_id,
                                    error_message=result.get("message"),
                                    target_type="nmap_scan",
                                )
                    finally:
                        db.close()

                # 等待下一次扫描
                await asyncio.sleep(nmap_scanner.scan_interval)

            except asyncio.CancelledError:
                logger.info("Nmap 扫描任务被取消")
                break
            except Exception as e:
                logger.error(f"Nmap 扫描任务异常: {e}", exc_info=True)
                await asyncio.sleep(300)  # 出错后等待5分钟再重试
    
    async def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行")
            return
        
        self.running = True
        logger.info("启动后台调度器")
        
        # 启动 HFish 同步任务
        self.hfish_task = asyncio.create_task(self._hfish_sync_loop())
        
        # 启动 Nmap 扫描任务
        self.nmap_task = asyncio.create_task(self._nmap_scan_loop())
        
        logger.info("后台调度器启动完成")
    
    async def stop(self):
        """停止调度器"""
        if not self.running:
            logger.warning("调度器未运行")
            return
        
        logger.info("停止后台调度器")
        self.running = False
        
        # 取消任务
        if self.hfish_task:
            self.hfish_task.cancel()
            try:
                await self.hfish_task
            except asyncio.CancelledError:
                pass
        
        if self.nmap_task:
            self.nmap_task.cancel()
            try:
                await self.nmap_task
            except asyncio.CancelledError:
                pass
        
        logger.info("后台调度器已停止")
    
    def is_running(self) -> bool:
        """检查调度器是否运行"""
        return self.running


# 全局单例
scheduler_service = SchedulerService()
