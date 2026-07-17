"""
清理服务 - 清理过期上传任务和临时文件
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List

from sqlalchemy.orm import Session
from app.models.file import FileMetadata, SessionLocal
from app.storage import get_storage_backend
from app.config import settings

logger = logging.getLogger(__name__)


class CleanupService:
    """清理服务"""

    def __init__(self, db: Session):
        """初始化清理服务"""
        self.db = db
        self.storage = get_storage_backend()

    def cleanup_expired_uploads(self) -> int:
        """
        清理过期的未完成上传任务

        Returns:
            清理的任务数量
        """
        # 计算过期时间
        expire_time = datetime.utcnow() - timedelta(hours=settings.UPLOAD_EXPIRE_HOURS)

        # 查找过期的未完成上传任务
        expired_uploads = self.db.query(FileMetadata).filter(
            FileMetadata.status == "uploading",
            FileMetadata.updated_at < expire_time
        ).all()

        count = 0
        for upload in expired_uploads:
            try:
                # 清理存储中的临时分片
                asyncio.run(self.storage.cleanup_chunks(upload.upload_id))

                # 删除数据库记录
                self.db.delete(upload)
                count += 1
                logger.info(f"已清理过期上传任务: {upload.upload_id}")
            except Exception as e:
                logger.error(f"清理上传任务失败 {upload.upload_id}: {e}")

        self.db.commit()
        return count

    def cleanup_orphaned_chunks(self) -> int:
        """
        清理孤立的临时分片文件

        查找数据库中不存在但存储中存在的临时分片

        Returns:
            清理的分片数量
        """
        # 获取所有活跃的上传任务 ID
        active_upload_ids = set(
            upload_id for (upload_id,) in
            self.db.query(FileMetadata.upload_id).filter(
                FileMetadata.status == "uploading"
            ).all()
        )

        # 本地存储的清理逻辑
        if settings.STORAGE_BACKEND == "local":
            return self._cleanup_local_chunks(active_upload_ids)

        return 0

    def _cleanup_local_chunks(self, active_upload_ids: set) -> int:
        """清理本地存储的孤立分片"""
        import os
        import shutil

        chunk_path = settings.LOCAL_CHUNK_PATH
        if not chunk_path.exists():
            return 0

        count = 0
        for upload_dir in chunk_path.iterdir():
            if upload_dir.is_dir():
                # 检查是否为活跃上传任务
                if upload_dir.name not in active_upload_ids:
                    try:
                        shutil.rmtree(upload_dir)
                        count += 1
                        logger.info(f"已清理孤立分片目录: {upload_dir.name}")
                    except Exception as e:
                        logger.error(f"清理分片目录失败 {upload_dir.name}: {e}")

        return count

    def cleanup_expired_files(self) -> int:
        """
        清理过期文件

        Returns:
            清理的文件数量
        """
        # 查找过期文件
        expired_files = self.db.query(FileMetadata).filter(
            FileMetadata.status == "completed",
            FileMetadata.expires_at != None,
            FileMetadata.expires_at < datetime.utcnow()
        ).all()

        count = 0
        for file_meta in expired_files:
            try:
                # 从存储中删除文件
                asyncio.run(self.storage.delete_file(file_meta.id))

                # 从数据库删除记录
                self.db.delete(file_meta)
                count += 1
                logger.info(f"已清理过期文件: {file_meta.id} ({file_meta.filename})")
            except Exception as e:
                logger.error(f"清理过期文件失败 {file_meta.id}: {e}")

        self.db.commit()
        return count


async def run_cleanup_task():
    """
    执行清理任务的后台函数

    用于定时任务调度
    """
    db = SessionLocal()
    try:
        service = CleanupService(db)

        # 清理过期上传任务
        expired_count = service.cleanup_expired_uploads()
        if expired_count > 0:
            logger.info(f"已清理 {expired_count} 个过期上传任务")

        # 清理孤立分片
        orphaned_count = service.cleanup_orphaned_chunks()
        if orphaned_count > 0:
            logger.info(f"已清理 {orphaned_count} 个孤立分片目录")

        # 清理过期文件
        if settings.FILE_DEFAULT_EXPIRE_DAYS > 0:
            expired_files_count = service.cleanup_expired_files()
            if expired_files_count > 0:
                logger.info(f"已清理 {expired_files_count} 个过期文件")

    except Exception as e:
        logger.error(f"清理任务执行失败: {e}")
    finally:
        db.close()


async def start_cleanup_scheduler():
    """
    启动清理定时任务

    作为后台任务运行，定时执行清理
    """
    logger.info(f"清理任务调度器已启动，间隔: {settings.CLEANUP_INTERVAL_MINUTES} 分钟")

    while True:
        try:
            await run_cleanup_task()
        except Exception as e:
            logger.error(f"清理任务异常: {e}")

        # 等待下一次执行
        await asyncio.sleep(settings.CLEANUP_INTERVAL_MINUTES * 60)