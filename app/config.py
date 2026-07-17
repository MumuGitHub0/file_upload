"""
配置管理模块
"""
import os
from pathlib import Path
from typing import Optional, List, Tuple
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Settings:
    """应用配置"""
    
    # ========== 应用常量（硬编码）==========
    APP_NAME: str = "大文件上传下载服务"
    APP_VERSION: str = "0.1.0"
    API_PREFIX: str = "/api/v1"
    
    # ========== 验证常量（硬编码）==========
    MAX_CHUNK_SIZE: int = 50 * 1024 * 1024  # 50MB
    MIN_CHUNK_SIZE: int = 1024 * 1024  # 1MB
    
    # ========== 基础路径 ==========
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    
    # ========== 服务器配置（环境变量）==========
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # ========== 存储配置（环境变量）==========
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")
    
    # 本地存储配置
    LOCAL_STORAGE_PATH: Path = Path(os.getenv("LOCAL_STORAGE_PATH", "./data/files"))
    LOCAL_CHUNK_PATH: Path = Path(os.getenv("LOCAL_CHUNK_PATH", "./data/chunks"))
    
    # OSS 配置（环境变量）
    OSS_ENDPOINT: Optional[str] = os.getenv("OSS_ENDPOINT")
    OSS_ACCESS_KEY_ID: Optional[str] = os.getenv("OSS_ACCESS_KEY_ID")
    OSS_ACCESS_KEY_SECRET: Optional[str] = os.getenv("OSS_ACCESS_KEY_SECRET")
    OSS_BUCKET_NAME: Optional[str] = os.getenv("OSS_BUCKET_NAME")
    
    # ========== 上传配置（环境变量）==========
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", 5 * 1024 * 1024))  # 5MB
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", 1024 * 1024 * 1024))  # 1GB
    ALLOWED_EXTENSIONS: str = os.getenv("ALLOWED_EXTENSIONS", "")  # 空表示不限制
    
    # ========== 安全配置（环境变量）==========
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")  # 多个用逗号分隔
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # ========== 运维配置（环境变量）==========
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")  # DEBUG, INFO, WARNING, ERROR
    DATABASE_URL: str = os.getenv("DATABASE_URL") or f"sqlite:///{DATA_DIR.as_posix()}/metadata.db"

    # ========== 清理配置（环境变量）==========
    UPLOAD_EXPIRE_HOURS: int = int(os.getenv("UPLOAD_EXPIRE_HOURS", "24"))  # 未完成上传过期时间（小时）
    CLEANUP_INTERVAL_MINUTES: int = int(os.getenv("CLEANUP_INTERVAL_MINUTES", "60"))  # 清理间隔（分钟）

    # ========== 病毒扫描配置（环境变量）==========
    VIRUS_SCAN_ENABLED: bool = os.getenv("VIRUS_SCAN_ENABLED", "false").lower() == "true"
    VIRUS_SCAN_ENGINE: str = os.getenv("VIRUS_SCAN_ENGINE", "clamav")  # clamav 或 api
    CLAMAV_SOCKET: str = os.getenv("CLAMAV_SOCKET", "/var/run/clamav/clamd.ctl")  # ClamAV socket 路径
    VIRUS_SCAN_API_URL: Optional[str] = os.getenv("VIRUS_SCAN_API_URL")  # 外部扫描 API 地址

    # ========== 文件过期配置（环境变量）==========
    FILE_DEFAULT_EXPIRE_DAYS: int = int(os.getenv("FILE_DEFAULT_EXPIRE_DAYS", "0"))  # 默认过期天数（0 表示永不过期）

    # ========== 回调通知配置（环境变量）==========
    UPLOAD_CALLBACK_URL: Optional[str] = os.getenv("UPLOAD_CALLBACK_URL")  # 回调地址
    UPLOAD_CALLBACK_TIMEOUT: int = int(os.getenv("UPLOAD_CALLBACK_TIMEOUT", "30"))  # 超时时间（秒）
    UPLOAD_CALLBACK_RETRIES: int = int(os.getenv("UPLOAD_CALLBACK_RETRIES", "3"))  # 重试次数

    # ========== 预览配置（环境变量）==========
    PREVIEW_ENABLED: bool = os.getenv("PREVIEW_ENABLED", "true").lower() == "true"
    PREVIEW_SUPPORTED_TYPES: str = os.getenv("PREVIEW_SUPPORTED_TYPES", ".jpg,.jpeg,.png,.gif,.webp,.bmp,.mp4,.webm")
    THUMBNAIL_SIZE: str = os.getenv("THUMBNAIL_SIZE", "200x200")  # 缩略图尺寸
    
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
    
    def get_allowed_extensions(self) -> Optional[List[str]]:
        """获取允许的文件扩展名列表"""
        if not self.ALLOWED_EXTENSIONS:
            return None
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]
    
    def get_cors_origins_list(self) -> List[str]:
        """获取 CORS 允许的来源列表"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    def validate_chunk_size(self) -> bool:
        """验证分片大小是否在合理范围内"""
        return self.MIN_CHUNK_SIZE <= self.CHUNK_SIZE <= self.MAX_CHUNK_SIZE

    def get_preview_supported_types(self) -> List[str]:
        """获取支持预览的文件类型列表"""
        if not self.PREVIEW_SUPPORTED_TYPES:
            return []
        return [ext.strip().lower() for ext in self.PREVIEW_SUPPORTED_TYPES.split(",")]

    def get_thumbnail_size(self) -> Tuple[int, int]:
        """获取缩略图尺寸"""
        try:
            width, height = self.THUMBNAIL_SIZE.lower().split("x")
            return int(width), int(height)
        except Exception:
            return 200, 200


# 全局配置实例
settings = Settings()