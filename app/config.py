"""
配置管理模块
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Settings:
    """应用配置"""
    
    # 基础路径
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    
    # 存储配置
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")
    
    # 本地存储配置
    LOCAL_STORAGE_PATH: Path = Path(os.getenv("LOCAL_STORAGE_PATH", "./data/files"))
    LOCAL_CHUNK_PATH: Path = Path(os.getenv("LOCAL_CHUNK_PATH", "./data/chunks"))
    
    # OSS 配置
    OSS_ENDPOINT: Optional[str] = os.getenv("OSS_ENDPOINT")
    OSS_ACCESS_KEY_ID: Optional[str] = os.getenv("OSS_ACCESS_KEY_ID")
    OSS_ACCESS_KEY_SECRET: Optional[str] = os.getenv("OSS_ACCESS_KEY_SECRET")
    OSS_BUCKET_NAME: Optional[str] = os.getenv("OSS_BUCKET_NAME")
    
    # 上传配置
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", 5 * 1024 * 1024))  # 5MB
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", 1024 * 1024 * 1024))  # 1GB
    
    # 数据库配置
    DATABASE_URL: str = f"sqlite:///{DATA_DIR}/metadata.db"
    
    def __init__(self):
        """初始化配置，创建必要的目录"""
        self.LOCAL_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        self.LOCAL_CHUNK_PATH.mkdir(parents=True, exist_ok=True)
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    def validate_oss_config(self) -> bool:
        """验证 OSS 配置是否完整"""
        return all([
            self.OSS_ENDPOINT,
            self.OSS_ACCESS_KEY_ID,
            self.OSS_ACCESS_KEY_SECRET,
            self.OSS_BUCKET_NAME,
        ])


# 全局配置实例
settings = Settings()