"""
上传相关的 Pydantic 模型
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ========== 上传初始化 ==========
class UploadInitRequest(BaseModel):
    """上传初始化请求"""
    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    file_hash: str = Field(..., description="文件哈希（MD5）")


class UploadInitResponse(BaseModel):
    """上传初始化响应"""
    upload_id: str = Field(..., description="上传任务 ID")
    chunk_size: int = Field(..., description="分片大小（字节）")
    chunk_count: int = Field(..., description="分片总数")
    uploaded_chunks: List[int] = Field(default_factory=list, description="已上传的分片索引（断点续传）")


# ========== 分片上传 ==========
class ChunkUploadResponse(BaseModel):
    """分片上传响应"""
    chunk_index: int = Field(..., description="分片索引")
    status: str = Field(..., description="上传状态")
    message: Optional[str] = Field(None, description="消息")


# ========== 上传进度 ==========
class UploadProgressResponse(BaseModel):
    """上传进度响应"""
    upload_id: str = Field(..., description="上传任务 ID")
    uploaded_chunks: int = Field(..., description="已上传分片数")
    total_chunks: int = Field(..., description="总分片数")
    progress: float = Field(..., description="进度百分比（0-100）")
    status: str = Field(..., description="上传状态")


# ========== 完成上传 ==========
class UploadCompleteResponse(BaseModel):
    """完成上传响应"""
    file_id: str = Field(..., description="文件 ID")
    url: str = Field(..., description="下载链接")
    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小")


# ========== 文件信息 ==========
class FileInfo(BaseModel):
    """文件信息"""
    file_id: str = Field(..., description="文件 ID")
    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    created_at: datetime = Field(..., description="创建时间")
    status: str = Field(..., description="文件状态")


class FileListResponse(BaseModel):
    """文件列表响应"""
    files: List[FileInfo] = Field(default_factory=list, description="文件列表")
    total: int = Field(..., description="文件总数")