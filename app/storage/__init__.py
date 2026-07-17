"""
存储后端模块
"""
from typing import Union
from app.storage.base import StorageBackend
from app.storage.local import LocalStorage
from app.config import settings


def get_storage_backend() -> Union[LocalStorage, 'OSSStorage']:
    """
    根据配置获取存储后端实例

    Returns:
        StorageBackend: 存储后端实例
    """
    backend_type = settings.STORAGE_BACKEND.lower()

    if backend_type == "local":
        return LocalStorage()
    elif backend_type == "oss":
        from app.storage.oss import OSSStorage
        return OSSStorage()
    else:
        raise ValueError(f"不支持的存储后端类型: {backend_type}")


__all__ = ["StorageBackend", "LocalStorage", "get_storage_backend"]