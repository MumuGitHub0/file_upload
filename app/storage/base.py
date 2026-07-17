"""
存储抽象基类
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Optional


class StorageBackend(ABC):
    """存储后端抽象基类"""
    
    @abstractmethod
    async def save_chunk(self, upload_id: str, chunk_index: int, data: bytes) -> str:
        """
        保存分片数据
        
        Args:
            upload_id: 上传任务 ID
            chunk_index: 分片索引
            data: 分片数据
        
        Returns:
            分片存储路径
        """
        pass
    
    @abstractmethod
    async def merge_chunks(self, upload_id: str, chunk_count: int, file_id: str, filename: str) -> str:
        """
        合并所有分片
        
        Args:
            upload_id: 上传任务 ID
            chunk_count: 分片总数
            file_id: 文件 ID
            filename: 文件名
        
        Returns:
            最终文件存储路径
        """
        pass
    
    @abstractmethod
    async def get_file(self, file_id: str, range_header: Optional[str] = None) -> Tuple[bytes, int, int, int]:
        """
        获取文件数据
        
        Args:
            file_id: 文件 ID
            range_header: Range 请求头（如 "bytes=0-1023"）
        
        Returns:
            (文件数据, 起始位置, 结束位置, 总大小)
        """
        pass
    
    @abstractmethod
    async def delete_file(self, file_id: str) -> bool:
        """
        删除文件
        
        Args:
            file_id: 文件 ID
        
        Returns:
            是否删除成功
        """
        pass
    
    @abstractmethod
    async def cleanup_chunks(self, upload_id: str):
        """
        清理临时分片
        
        Args:
            upload_id: 上传任务 ID
        """
        pass
    
    @abstractmethod
    def get_file_path(self, file_id: str, filename: str) -> str:
        """
        获取文件存储路径
        
        Args:
            file_id: 文件 ID
            filename: 文件名
        
        Returns:
            文件存储路径
        """
        pass