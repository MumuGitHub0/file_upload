"""
文件上传器
实现分片上传、断点续传逻辑
"""

import hashlib
from pathlib import Path

from tqdm import tqdm

from .api import APIClient


class FileUploader:
    """文件上传器"""

    def __init__(self, api_client: APIClient):
        self.client = api_client

    def upload(self, file_path: str) -> dict:
        """
        上传文件

        Args:
            file_path: 文件路径

        Returns:
            {
                "file_id": "uuid",
                "url": "/download/{file_id}",
                "filename": "example.mp4",
                "file_size": 524288000
            }
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 1. 计算文件哈希
        print(f"正在计算文件哈希: {file_path.name}")
        file_hash = self._calculate_hash(file_path)
        file_size = file_path.stat().st_size

        # 2. 初始化上传
        print("正在初始化上传...")
        init_data = self.client.init_upload(file_path.name, file_size, file_hash)
        upload_id = init_data["upload_id"]
        chunk_size = init_data["chunk_size"]
        chunk_count = init_data["chunk_count"]
        uploaded_chunks = set(init_data.get("uploaded_chunks", []))

        print(f"上传ID: {upload_id}")
        print(f"分片大小: {chunk_size / 1024 / 1024:.2f} MB")
        print(f"总分片数: {chunk_count}")
        if uploaded_chunks:
            print(f"已上传分片: {len(uploaded_chunks)}/{chunk_count}")

        # 3. 分片上传
        with tqdm(total=chunk_count, desc="上传进度", unit="chunk") as pbar:
            with open(file_path, "rb") as f:
                for chunk_index in range(chunk_count):
                    # 跳过已上传的分片
                    if chunk_index in uploaded_chunks:
                        pbar.update(1)
                        continue

                    # 读取分片数据
                    chunk_data = f.read(chunk_size)

                    # 上传分片
                    self.client.upload_chunk(upload_id, chunk_index, chunk_data)
                    pbar.update(1)

        # 4. 完成上传
        print("\n正在完成上传...")
        result = self.client.complete_upload(upload_id)

        print(f"\n上传完成!")
        print(f"文件ID: {result['file_id']}")
        print(f"下载URL: {result['url']}")
        print(f"文件大小: {result['file_size'] / 1024 / 1024:.2f} MB")

        return result

    def _calculate_hash(self, file_path: Path) -> str:
        """
        计算文件MD5哈希

        Args:
            file_path: 文件路径

        Returns:
            MD5哈希字符串
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()