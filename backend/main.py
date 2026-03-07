from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from core.database import init_db
from core.logging_config import setup_logging
from core.response import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)
from core.middleware import TraceIDMiddleware, RateLimitMiddleware
from api import auth, defense, scan, report, ai_chat, tts, firewall, system, push, overview, plugin, device, workflow
from services.scheduler_service import scheduler_service


def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     █████╗ ██╗███╗   ███╗██╗ ██████╗ ██╗   ██╗ █████╗ ███╗  ║
║    ██╔══██╗██║████╗ ████║██║██╔════╝ ██║   ██║██╔══██╗████╗ ║
║    ███████║██║██╔████╔██║██║██║  ███╗██║   ██║███████║██╔██╗║
║    ██╔══██║██║██║╚██╔╝██║██║██║   ██║██║   ██║██╔══██║██║╚██║
║    ██║  ██║██║██║ ╚═╝ ██║██║╚██████╔╝╚██████╔╝██║  ██║██║ ╚█║
║    ╚═╝  ╚═╝╚═╝╚═╝     ╚═╝╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚╝
║                                                              ║
║              AI 驱动的智能安全运营平台 v0.1.0                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)
    print("🚀 系统启动中...")
    print(f"⏰ 启动时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    print_banner()
    init_db()
    print("✓ 数据库初始化完成")
    print("✓ API 路由注册完成")
    print("✓ 中间件加载完成")
    
    # 启动后台调度服务
    await scheduler_service.start()
    print("✓ 后台调度服务已启动")
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🌐 服务地址: http://0.0.0.0:8000")
    print("📚 API 文档: http://0.0.0.0:8000/docs")
    print("🔧 健康检查: http://0.0.0.0:8000/api/health")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ 系统启动成功！按 CTRL+C 停止服务")
    print()
    yield
    # Shutdown
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🛑 正在关闭服务...")
    
    # 停止后台调度服务
    await scheduler_service.stop()
    print("✓ 后台调度服务已停止")
    
    print("✓ 数据库连接已关闭")
    print("✓ 系统已安全退出")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


app = FastAPI(
    title="Aimiguan API",
    description="AI-driven Security Operations Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TraceIDMiddleware)
app.add_middleware(RateLimitMiddleware, global_rpm=120, login_rpm=5)

# Register exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Register API routers
app.include_router(auth.router)
app.include_router(system.router)
app.include_router(system.compat_router)  # /api/system/* compatibility
app.include_router(defense.router)
app.include_router(defense.compat_router)
app.include_router(scan.router)
app.include_router(report.router)
app.include_router(ai_chat.router)
app.include_router(tts.router)
app.include_router(firewall.router)
app.include_router(push.router)
app.include_router(overview.router)
app.include_router(plugin.router)
app.include_router(device.router)
app.include_router(workflow.router)


@app.get("/api/health")
async def health_check():
    return {
        "code": 0,
        "message": "OK",
        "data": {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    }


@app.get("/")
async def root():
    return {"message": "Aimiguan API Server"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
