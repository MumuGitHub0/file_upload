"""
FastAPI 应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import upload_router
from app.models.file import init_db
from app.config import settings


# 创建 FastAPI 应用
app = FastAPI(
    title="大文件上传下载服务",
    description="支持分片上传、断点续传、进度追踪的大文件上传下载服务",
    version="0.1.0",
)

# CORS 配置（可选）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(upload_router)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    init_db()
    print(f"[OK] 数据库已初始化")
    print(f"[OK] 存储后端: {settings.STORAGE_BACKEND}")
    print(f"[OK] 分片大小: {settings.CHUNK_SIZE // (1024*1024)} MB")
    print(f"[OK] 最大文件: {settings.MAX_FILE_SIZE // (1024*1024)} MB")


@app.get("/", tags=["root"])
async def root():
    """根路径"""
    return {
        "message": "大文件上传下载服务",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)