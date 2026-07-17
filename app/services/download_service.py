"""
下载服务
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime

from app.models.file import FileMetadata
from app.schemas.upload import FileInfo, FileListResponse
from app.storage import get_storage_backend
from app.config import settings


class DownloadService:
    """下载服务"""
    
    def __init__(self, db: Session):
        """初始化下载服务"""
        self.db = db
        self.storage = get_storage_backend()
    
    async def get_file(self, file_id: str, range_header: Optional[str] = None):
        """
        获取文件数据
        
        Args:
            file_id: 文件 ID
            range_header: Range 请求头
        
        Returns:
            (文件数据, 起始位置, 结束位置, 总大小)
        """
        # 查找文件
        file_metadata = self.db.query(FileMetadata).filter(
            FileMetadata.id == file_id,
            FileMetadata.status == "completed"
        ).first()
        
        if not file_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        
        # 从存储后端获取文件
        return await self.storage.get_file(file_id, range_header)
    
    def list_files(self, skip: int = 0, limit: int = 100) -> FileListResponse:
        """
        获取文件列表
        
        Args:
            skip: 跳过数量
            limit: 限制数量
        
        Returns:
            FileListResponse: 文件列表
        """
        total = self.db.query(FileMetadata).filter(
            FileMetadata.status == "completed"
        ).count()
        
        files = self.db.query(FileMetadata).filter(
            FileMetadata.status == "completed"
        ).order_by(FileMetadata.created_at.desc()).offset(skip).limit(limit).all()
        
        file_infos = [
            FileInfo(
                file_id=f.id,
                filename=f.filename,
                file_size=f.file_size,
                created_at=f.created_at,
                status=f.status
            )
            for f in files
        ]
        
        return FileListResponse(files=file_infos, total=total)
    
    async def delete_file(self, file_id: str) -> bool:
        """
        删除文件
        
        Args:
            file_id: 文件 ID
        
        Returns:
            bool: 是否删除成功
        """
        file_metadata = self.db.query(FileMetadata).filter(
            FileMetadata.id == file_id
        ).first()
        
        if not file_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        
        # 从存储后端删除文件
        await self.storage.delete_file(file_id)
        
        # 从数据库删除记录
        self.db.delete(file_metadata)
        self.db.commit()
        
        return True