"""
API 路由模块
"""
from app.api.upload import router as upload_router
from app.api.preview import router as preview_router

__all__ = ["upload_router", "preview_router"]