"""
本地文件存储实现
"""
import os
import aiofiles
import aiofiles.os
from pathlib import Path
from typing import Tuple, Optional
from app.storage.base import StorageBackend
from app.config import settings


class LocalStorage(StorageBackend):
    """本地文件存储"""
    
    def __init__(self):
        """初始化本地存储"""
        self.storage_path = settings.LOCAL_STORAGE_PATH
        self.chunk_path = settings.LOCAL_CHUNK_PATH
        
        # 确保目录存在
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.chunk_path.mkdir(parents=True, exist_ok=True)
    
    async def save_chunk(self, upload_id: str, chunk_index: int, data: bytes) -> str:
        """保存分片到本地"""
        # 创建上传任务的分片目录
        chunk_dir = self.chunk_path / upload_id
        chunk_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存分片文件
        chunk_file = chunk_dir / f"{chunk_index}.chunk"
        async with aiofiles.open(chunk_file, "wb") as f:
            await f.write(data)
        
        return str(chunk_file)
    
    async def merge_chunks(self, upload_id: str, chunk_count: int, file_id: str, filename: str) -> str:
        """合并分片文件"""
        chunk_dir = self.chunk_path / upload_id
        final_path = self.get_file_path(file_id, filename)
        
        # 创建目标文件的父目录
        Path(final_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 合并所有分片
        async with aiofiles.open(final_path, "wb") as outfile:
            for i in range(chunk_count):
                chunk_file = chunk_dir / f"{i}.chunk"
                if chunk_file.exists():
                    async with aiofiles.open(chunk_file, "rb") as infile:
                        data = await infile.read()
                        await outfile.write(data)
        
        return final_path
    
    async def get_file(self, file_id: str, range_header: Optional[str] = None) -> Tuple[bytes, int, int, int]:
        """读取文件数据（支持 Range 请求）"""
        # 查找文件（需要根据 file_id 查找实际文件路径）
        # 这里简化处理，实际应该从数据库获取文件路径
        # 假设文件名格式为 {file_id}_*
        matching_files = list(self.storage_path.glob(f"{file_id}_*"))
        if not matching_files:
            raise FileNotFoundError(f"File {file_id} not found")
        
        file_path = matching_files[0]
        file_size = (await aiofiles.os.stat(file_path)).st_size
        
        # 解析 Range 请求头
        start = 0
        end = file_size - 1
        
        if range_header:
            # 格式: "bytes=start-end"
            range_str = range_header.replace("bytes=", "")
            parts = range_str.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else file_size - 1
        
        # 读取指定范围的数据
        async with aiofiles.open(file_path, "rb") as f:
            await f.seek(start)
            data = await f.read(end - start + 1)
        
        return data, start, end, file_size
    
    async def delete_file(self, file_id: str) -> bool:
        """删除文件"""
        try:
            # 查找并删除文件
            matching_files = list(self.storage_path.glob(f"{file_id}_*"))
            for file_path in matching_files:
                await aiofiles.os.remove(file_path)
            return True
        except Exception:
            return False
    
    async def cleanup_chunks(self, upload_id: str):
        """清理临时分片目录"""
        chunk_dir = self.chunk_path / upload_id
        if chunk_dir.exists():
            # 删除目录下的所有文件
            for chunk_file in chunk_dir.glob("*.chunk"):
                await aiofiles.os.remove(chunk_file)
            # 删除空目录
            chunk_dir.rmdir()
    
    def get_file_path(self, file_id: str, filename: str) -> str:
        """生成文件存储路径"""
        # 使用 file_id 前缀避免文件名冲突
        safe_filename = f"{file_id}_{filename}"
        return str(self.storage_path / safe_filename)