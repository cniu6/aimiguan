"""
后台调度服务
定时执行 HFish 数据同步和 Nmap 扫描任务
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from services.hfish_collector import hfish_collector
from services.nmap_scanner import nmap_scanner
from core.database import SessionLocal

logger = logging.getLogger(__name__)


class SchedulerService:
    """后台任务调度器"""
    
    def __init__(self):
        self.running = False
        self.hfish_task: Optional[asyncio.Task] = None
        self.nmap_task: Optional[asyncio.Task] = None
    
    async def _hfish_sync_loop(self):
        """HFish 同步循环"""
        logger.info("HFish 同步任务已启动")
        
        while self.running:
            try:
                if hfish_collector.enabled:
                    trace_id = f"hfish_sync_{uuid.uuid4().hex[:8]}"
                    result = await hfish_collector.sync_once(trace_id)
                    
                    if result["success"]:
                        logger.info(f"HFish 同步成功: {result['message']}")
                    else:
                        logger.warning(f"HFish 同步失败: {result['message']}")
                
                # 等待下一次同步
                await asyncio.sleep(hfish_collector.sync_interval)
            
            except asyncio.CancelledError:
                logger.info("HFish 同步任务被取消")
                break
            except Exception as e:
                logger.error(f"HFish 同步任务异常: {e}", exc_info=True)
                await asyncio.sleep(60)  # 出错后等待1分钟再重试
    
    async def _nmap_scan_loop(self):
        """Nmap 扫描循环"""
        logger.info("Nmap 扫描任务已启动")
        
        while self.running:
            try:
                if nmap_scanner.enabled and nmap_scanner.ip_ranges:
                    db = SessionLocal()
                    try:
                        for ip_range in nmap_scanner.ip_ranges:
                            trace_id = f"nmap_scan_{uuid.uuid4().hex[:8]}"
                            logger.info(f"开始扫描 {ip_range}")
                            
                            result = await nmap_scanner.scan_target(
                                target=ip_range,
                                profile="default",
                                db=db,
                                trace_id=trace_id
                            )
                            
                            if result["success"]:
                                logger.info(f"Nmap 扫描成功: {result['message']}")
                            else:
                                logger.warning(f"Nmap 扫描失败: {result['message']}")
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
