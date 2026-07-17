"""
FastAPI 应用入口
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import upload_router, preview_router
from app.models.file import init_db
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    init_db()
    print(f"[OK] 数据库已初始化")
    print(f"[OK] 存储后端: {settings.STORAGE_BACKEND}")
    print(f"[OK] 分片大小: {settings.CHUNK_SIZE // (1024*1024)} MB")
    print(f"[OK] 最大文件: {settings.MAX_FILE_SIZE // (1024*1024)} MB")

    # 启动清理任务调度器
    cleanup_task = None
    if settings.UPLOAD_EXPIRE_HOURS > 0:
        from app.services.cleanup_service import start_cleanup_scheduler
        cleanup_task = asyncio.create_task(start_cleanup_scheduler())
        print(f"[OK] 清理任务已启动，过期时间: {settings.UPLOAD_EXPIRE_HOURS} 小时")

    yield

    # 关闭时执行
    if cleanup_task:
        cleanup_task.cancel()
        print("[OK] 清理任务已停止")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    description="支持分片上传、断点续传、进度追踪的大文件上传下载服务",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(upload_router)
app.include_router(preview_router)


@app.get("/", tags=["root"])
async def root():
    """根路径"""
    return {
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)