from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import uuid
from datetime import datetime

from core.database import init_db
from core.response import http_exception_handler, validation_exception_handler, general_exception_handler
from core.middleware import TraceIDMiddleware
from api import auth, defense, scan, report, ai_chat, tts, firewall, system

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
    print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print_banner()
    init_db()
    print("✓ 数据库初始化完成")
    print("✓ API 路由注册完成")
    print("✓ 中间件加载完成")
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
    print("✓ 数据库连接已关闭")
    print("✓ 系统已安全退出")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

app = FastAPI(
    title="Aimiguan API",
    description="AI-driven Security Operations Platform",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TraceIDMiddleware)

# Register exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Register API routers
app.include_router(auth.router)
app.include_router(system.router)
app.include_router(system.compat_router)  # /api/system/* compatibility
app.include_router(defense.router)
app.include_router(scan.router)
app.include_router(report.router)
app.include_router(ai_chat.router)
app.include_router(tts.router)
app.include_router(firewall.router)

@app.get("/api/health")
async def health_check():
    return {
        "code": 0,
        "message": "OK",
        "data": {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    }

@app.get("/")
async def root():
    return {"message": "Aimiguan API Server"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
