"""
API客户端封装
封装所有与服务端的HTTP交互
"""

import os
from pathlib import Path
from typing import Optional

import requests


class APIClient:
    """大文件上传下载API客户端"""

    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = base_url.rstrip("/")
        self.api_prefix = "/api/v1"

    def init_upload(self, filename: str, file_size: int, file_hash: str) -> dict:
        """
        初始化上传

        Args:
            filename: 文件名
            file_size: 文件大小（字节）
            file_hash: 文件MD5哈希

        Returns:
            {
                "upload_id": "uuid",
                "chunk_size": 5242880,
                "chunk_count": 100,
                "uploaded_chunks": []
            }
        """
        url = f"{self.base_url}{self.api_prefix}/upload/init"
        resp = requests.post(
            url,
            json={
                "filename": filename,
                "file_size": file_size,
                "file_hash": file_hash,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def upload_chunk(
        self, upload_id: str, chunk_index: int, chunk_data: bytes
    ) -> dict:
        """
        上传分片

        Args:
            upload_id: 上传ID
            chunk_index: 分片索引（从0开始）
            chunk_data: 分片数据

        Returns:
            {
                "chunk_index": 0,
                "status": "success",
                "message": "分片 0 上传成功"
            }
        """
        url = f"{self.base_url}{self.api_prefix}/upload/chunk/{upload_id}"
        files = {"chunk_data": chunk_data}
        data = {"chunk_index": str(chunk_index)}
        resp = requests.post(url, files=files, data=data)
        resp.raise_for_status()
        return resp.json()

    def complete_upload(self, upload_id: str) -> dict:
        """
        完成上传

        Args:
            upload_id: 上传ID

        Returns:
            {
                "file_id": "uuid",
                "url": "/download/{file_id}",
                "filename": "example.mp4",
                "file_size": 524288000
            }
        """
        url = f"{self.base_url}{self.api_prefix}/upload/complete/{upload_id}"
        resp = requests.post(url)
        resp.raise_for_status()
        return resp.json()

    def get_progress(self, upload_id: str) -> dict:
        """
        查询上传进度

        Args:
            upload_id: 上传ID

        Returns:
            {
                "upload_id": "uuid",
                "uploaded_chunks": 50,
                "total_chunks": 100,
                "progress": 50.0,
                "status": "uploading"
            }
        """
        url = f"{self.base_url}{self.api_prefix}/upload/progress/{upload_id}"
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()

    def download_file(self, file_id: str, output_path: str) -> str:
        """
        下载文件

        Args:
            file_id: 文件ID
            output_path: 输出路径

        Returns:
            保存的文件路径
        """
        url = f"{self.base_url}{self.api_prefix}/download/{file_id}"
        resp = requests.get(url, stream=True)
        resp.raise_for_status()

        # 获取文件大小用于进度显示
        total_size = int(resp.headers.get("content-length", 0))

        # 确保输出目录存在
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        return str(output_path)

    def list_files(self, skip: int = 0, limit: int = 100) -> dict:
        """
        获取文件列表

        Args:
            skip: 跳过数量
            limit: 限制数量

        Returns:
            {
                "files": [...],
                "total": 1
            }
        """
        url = f"{self.base_url}{self.api_prefix}/files"
        params = {"skip": skip, "limit": limit}
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def delete_file(self, file_id: str) -> dict:
        """
        删除文件

        Args:
            file_id: 文件ID

        Returns:
            {
                "success": true,
                "message": "文件已删除"
            }
        """
        url = f"{self.base_url}{self.api_prefix}/files/{file_id}"
        resp = requests.delete(url)
        resp.raise_for_status()
        return resp.json()