"""
上传服务 - 核心业务逻辑
"""
import uuid
import math
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status

from app.models.file import FileMetadata, init_db
from app.schemas.upload import (
    UploadInitRequest,
    UploadInitResponse,
    ChunkUploadResponse,
    UploadProgressResponse,
    UploadCompleteResponse,
)
from app.storage import get_storage_backend
from app.config import settings
from app.utils.validators import validate_file_extension


class UploadService:
    """上传服务"""
    
    def __init__(self, db: Session):
        """初始化上传服务"""
        self.db = db
        self.storage = get_storage_backend()
    
    def init_upload(self, request: UploadInitRequest) -> UploadInitResponse:
        """
        初始化上传任务

        Args:
            request: 上传初始化请求

        Returns:
            UploadInitResponse: 包含 upload_id 和分片信息
        """
        # 验证文件大小
        if request.file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件大小超过限制（最大 {settings.MAX_FILE_SIZE // (1024*1024)} MB）"
            )

        # 验证文件类型
        allowed_extensions = settings.get_allowed_extensions()
        is_valid, error_msg = validate_file_extension(request.filename, allowed_extensions)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # 检查是否已存在相同文件（去重）
        existing_file = self.db.query(FileMetadata).filter(
            FileMetadata.file_hash == request.file_hash,
            FileMetadata.status == "completed"
        ).first()
        
        if existing_file:
            # 文件已存在，返回已存在的 upload_id
            return UploadInitResponse(
                upload_id=existing_file.upload_id,
                chunk_size=existing_file.chunk_size,
                chunk_count=existing_file.chunk_count,
                uploaded_chunks=list(range(existing_file.chunk_count))  # 所有分片都已上传
            )
        
        # 检查是否有未完成的上传任务（断点续传）
        incomplete_upload = self.db.query(FileMetadata).filter(
            FileMetadata.file_hash == request.file_hash,
            FileMetadata.status == "uploading"
        ).first()
        
        if incomplete_upload:
            # 返回未完成的上传任务
            return UploadInitResponse(
                upload_id=incomplete_upload.upload_id,
                chunk_size=incomplete_upload.chunk_size,
                chunk_count=incomplete_upload.chunk_count,
                uploaded_chunks=incomplete_upload.get_uploaded_chunks()
            )
        
        # 创建新的上传任务
        upload_id = str(uuid.uuid4())
        chunk_count = math.ceil(request.file_size / settings.CHUNK_SIZE)

        # 计算过期时间
        expires_at = None
        if settings.FILE_DEFAULT_EXPIRE_DAYS > 0:
            from datetime import timedelta
            expires_at = datetime.utcnow() + timedelta(days=settings.FILE_DEFAULT_EXPIRE_DAYS)

        file_metadata = FileMetadata(
            id=str(uuid.uuid4()),
            filename=request.filename,
            file_size=request.file_size,
            file_hash=request.file_hash,
            upload_id=upload_id,
            chunk_size=settings.CHUNK_SIZE,
            chunk_count=chunk_count,
            status="uploading",
            storage_backend=settings.STORAGE_BACKEND,
            storage_path=self.storage.get_file_path(upload_id, request.filename),
            expires_at=expires_at
        )
        
        self.db.add(file_metadata)
        self.db.commit()
        
        return UploadInitResponse(
            upload_id=upload_id,
            chunk_size=settings.CHUNK_SIZE,
            chunk_count=chunk_count,
            uploaded_chunks=[]
        )
    
    async def upload_chunk(
        self,
        upload_id: str,
        chunk_index: int,
        chunk_data: bytes
    ) -> ChunkUploadResponse:
        """
        上传分片
        
        Args:
            upload_id: 上传任务 ID
            chunk_index: 分片索引
            chunk_data: 分片数据
        
        Returns:
            ChunkUploadResponse: 分片上传结果
        """
        # 查找上传任务
        file_metadata = self.db.query(FileMetadata).filter(
            FileMetadata.upload_id == upload_id
        ).first()
        
        if not file_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="上传任务不存在"
            )
        
        if file_metadata.status != "uploading":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="上传任务已完成或失败"
            )
        
        # 验证分片索引
        if chunk_index < 0 or chunk_index >= file_metadata.chunk_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"分片索引无效（0-{file_metadata.chunk_count-1}）"
            )
        
        # 保存分片
        await self.storage.save_chunk(upload_id, chunk_index, chunk_data)
        
        # 更新数据库
        file_metadata.add_uploaded_chunk(chunk_index)
        self.db.commit()
        
        return ChunkUploadResponse(
            chunk_index=chunk_index,
            status="success",
            message=f"分片 {chunk_index} 上传成功"
        )
    
    async def complete_upload(self, upload_id: str) -> UploadCompleteResponse:
        """
        完成上传，合并分片
        
        Args:
            upload_id: 上传任务 ID
        
        Returns:
            UploadCompleteResponse: 包含文件 ID 和下载链接
        """
        # 查找上传任务
        file_metadata = self.db.query(FileMetadata).filter(
            FileMetadata.upload_id == upload_id
        ).first()
        
        if not file_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="上传任务不存在"
            )
        
        if file_metadata.status != "uploading":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="上传任务已完成或失败"
            )
        
        # 检查是否所有分片都已上传
        uploaded_chunks = file_metadata.get_uploaded_chunks()
        if len(uploaded_chunks) != file_metadata.chunk_count:
            missing_chunks = [
                i for i in range(file_metadata.chunk_count)
                if i not in uploaded_chunks
            ]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"还有分片未上传：{missing_chunks}"
            )
        
        # 合并分片
        final_path = await self.storage.merge_chunks(
            upload_id,
            file_metadata.chunk_count,
            file_metadata.id,
            file_metadata.filename
        )

        # 病毒扫描（如果启用）
        if settings.VIRUS_SCAN_ENABLED:
            from app.services.scan_service import get_scan_service
            scan_service = get_scan_service()
            if scan_service:
                scan_result = scan_service.scan_file(final_path)
                file_metadata.scan_status = "clean" if scan_result.is_clean else "infected"
                file_metadata.scan_result = scan_result.message
                if not scan_result.is_clean:
                    # 扫描到病毒，标记文件为失败状态
                    file_metadata.status = "failed"
                    self.db.commit()
                    await self.storage.cleanup_chunks(upload_id)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"文件包含恶意内容: {scan_result.message}"
                    )

        # 更新数据库
        file_metadata.status = "completed"
        file_metadata.storage_path = final_path
        self.db.commit()

        # 清理临时分片
        await self.storage.cleanup_chunks(upload_id)

        # 发送回调通知
        if settings.UPLOAD_CALLBACK_URL:
            from app.services.callback_service import get_callback_service
            callback_svc = get_callback_service()
            if callback_svc:
                download_url = f"/download/{file_metadata.id}"
                await callback_svc.send_upload_complete_callback(
                    upload_id=upload_id,
                    file_id=file_metadata.id,
                    filename=file_metadata.filename,
                    file_size=file_metadata.file_size,
                    download_url=download_url
                )
                file_metadata.callback_status = "success"
                self.db.commit()

        return UploadCompleteResponse(
            file_id=file_metadata.id,
            url=f"/download/{file_metadata.id}",
            filename=file_metadata.filename,
            file_size=file_metadata.file_size
        )
    
    def get_progress(self, upload_id: str) -> UploadProgressResponse:
        """
        查询上传进度
        
        Args:
            upload_id: 上传任务 ID
        
        Returns:
            UploadProgressResponse: 上传进度信息
        """
        file_metadata = self.db.query(FileMetadata).filter(
            FileMetadata.upload_id == upload_id
        ).first()
        
        if not file_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="上传任务不存在"
            )
        
        return UploadProgressResponse(
            upload_id=upload_id,
            uploaded_chunks=len(file_metadata.get_uploaded_chunks()),
            total_chunks=file_metadata.chunk_count,
            progress=file_metadata.progress,
            status=file_metadata.status
        )