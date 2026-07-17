"""
存储后端模块
"""
from app.storage.base import StorageBackend
from app.storage.local import LocalStorage

__all__ = ["StorageBackend", "LocalStorage"]