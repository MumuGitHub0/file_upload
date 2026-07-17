"""
上传下载 API 路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session

from app.models.file import get_db
from app.schemas.upload import (
    UploadInitRequest,
    UploadInitResponse,
    ChunkUploadResponse,
    UploadProgressResponse,
    UploadCompleteResponse,
    FileListResponse,
)
from app.services.upload_service import UploadService
from app.services.download_service import DownloadService

router = APIRouter(prefix="/api/v1", tags=["upload-download"])


# ========== 上传相关接口 ==========

@router.post("/upload/init", response_model=UploadInitResponse, summary="初始化上传")
async def init_upload(
    request: UploadInitRequest,
    db: Session = Depends(get_db)
):
    """
    初始化上传任务
    
    - **filename**: 文件名
    - **file_size**: 文件大小（字节）
    - **file_hash**: 文件哈希（MD5）
    
    返回 upload_id 和分片信息，支持断点续传
    """
    service = UploadService(db)
    return service.init_upload(request)


@router.post("/upload/chunk/{upload_id}", response_model=ChunkUploadResponse, summary="上传分片")
async def upload_chunk(
    upload_id: str,
    chunk_index: int = Form(...),
    chunk_data: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    上传文件分片
    
    - **upload_id**: 上传任务 ID
    - **chunk_index**: 分片索引（从 0 开始）
    - **chunk_data**: 分片数据（二进制）
    """
    service = UploadService(db)
    data = await chunk_data.read()
    return await service.upload_chunk(upload_id, chunk_index, data)


@router.post("/upload/complete/{upload_id}", response_model=UploadCompleteResponse, summary="完成上传")
async def complete_upload(
    upload_id: str,
    db: Session = Depends(get_db)
):
    """
    完成上传，合并所有分片
    
    - **upload_id**: 上传任务 ID
    
    返回文件 ID 和下载链接
    """
    service = UploadService(db)
    return await service.complete_upload(upload_id)


@router.get("/upload/progress/{upload_id}", response_model=UploadProgressResponse, summary="查询上传进度")
async def get_upload_progress(
    upload_id: str,
    db: Session = Depends(get_db)
):
    """
    查询上传进度
    
    - **upload_id**: 上传任务 ID
    
    返回已上传分片数、总分片数和进度百分比
    """
    service = UploadService(db)
    return service.get_progress(upload_id)


# ========== 下载相关接口 ==========

@router.get("/download/{file_id}", summary="下载文件")
async def download_file(
    file_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    下载文件，支持 Range 请求头（分段下载）
    
    - **file_id**: 文件 ID
    """
    service = DownloadService(db)
    
    # 获取 Range 请求头
    range_header = request.headers.get("range")
    
    try:
        # 获取文件数据
        data, start, end, file_size = await service.get_file(file_id, range_header)
        
        # 设置响应头
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(len(data)),
            "Content-Disposition": f"attachment; filename={file_id}"
        }
        
        # 根据是否有 Range 头返回不同的状态码
        status_code = 206 if range_header else 200
        
        return Response(
            content=data,
            status_code=status_code,
            headers=headers,
            media_type="application/octet-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/files", response_model=FileListResponse, summary="获取文件列表")
async def list_files(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    获取已上传文件列表
    
    - **skip**: 跳过数量
    - **limit**: 限制数量
    """
    service = DownloadService(db)
    return service.list_files(skip, limit)


@router.delete("/files/{file_id}", summary="删除文件")
async def delete_file(
    file_id: str,
    db: Session = Depends(get_db)
):
    """
    删除文件
    
    - **file_id**: 文件 ID
    """
    service = DownloadService(db)
    success = await service.delete_file(file_id)
    return {"success": success, "message": "文件已删除"}