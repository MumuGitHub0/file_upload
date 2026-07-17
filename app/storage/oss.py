"""
阿里云 OSS 对象存储实现
"""
import os
import tempfile
from typing import Tuple, Optional, Dict
from app.storage.base import StorageBackend
from app.config import settings


class OSSStorage(StorageBackend):
    """阿里云 OSS 对象存储"""

    def __init__(self):
        """初始化 OSS 客户端"""
        import oss2

        # 验证配置
        if not settings.validate_oss_config():
            raise ValueError("OSS 配置不完整，请检查 OSS_ENDPOINT, OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_BUCKET_NAME")

        # 创建 OSS 认证
        auth = oss2.Auth(
            settings.OSS_ACCESS_KEY_ID,
            settings.OSS_ACCESS_KEY_SECRET
        )

        # 创建 Bucket 实例
        endpoint = settings.OSS_ENDPOINT
        bucket_name = settings.OSS_BUCKET_NAME

        # 确保 endpoint 格式正确
        if not endpoint.startswith(('http://', 'https://')):
            endpoint = f"https://{endpoint}"

        self.bucket = oss2.Bucket(auth, endpoint, bucket_name)

        # 分片上传状态缓存 {upload_id: {upload_id, parts: []}}
        self._multipart_uploads: Dict[str, dict] = {}

    async def save_chunk(self, upload_id: str, chunk_index: int, data: bytes) -> str:
        """
        保存分片数据到 OSS

        使用 OSS 分片上传：
        1. 首次调用时初始化分片上传
        2. 上传每个分片
        3. 记录分片信息
        """
        # 获取或创建分片上传任务
        if upload_id not in self._multipart_uploads:
            # 初始化分片上传
            object_key = self._get_chunk_object_key(upload_id)
            result = self.bucket.init_multipart_upload(object_key)
            self._multipart_uploads[upload_id] = {
                'oss_upload_id': result.upload_id,
                'object_key': object_key,
                'parts': []
            }

        upload_info = self._multipart_uploads[upload_id]
        object_key = upload_info['object_key']
        oss_upload_id = upload_info['oss_upload_id']

        # 上传分片（分片号从 1 开始）
        part_number = chunk_index + 1
        result = self.bucket.upload_part(
            object_key,
            oss_upload_id,
            part_number,
            data
        )

        # 记录分片信息
        upload_info['parts'].append(oss2.models.PartInfo(
            part_number,
            result.etag,
            size=len(data)
        ))

        return f"oss://{settings.OSS_BUCKET_NAME}/{object_key}?part={part_number}"

    async def merge_chunks(self, upload_id: str, chunk_count: int, file_id: str, filename: str) -> str:
        """
        合并所有分片

        完成分片上传，将所有分片合并为最终文件
        """
        if upload_id not in self._multipart_uploads:
            raise ValueError(f"上传任务不存在: {upload_id}")

        upload_info = self._multipart_uploads[upload_id]
        object_key = upload_info['object_key']
        oss_upload_id = upload_info['oss_upload_id']
        parts = upload_info['parts']

        # 确保分片按序排列
        parts.sort(key=lambda p: p.part_number)

        # 完成分片上传
        self.bucket.complete_multipart_upload(
            object_key,
            oss_upload_id,
            parts
        )

        # 重命名为最终文件名
        final_object_key = self.get_file_path(file_id, filename)
        if object_key != final_object_key:
            self.bucket.copy_object(
                settings.OSS_BUCKET_NAME,
                object_key,
                final_object_key
            )
            # 删除临时对象
            self.bucket.delete_object(object_key)

        # 清理缓存
        del self._multipart_uploads[upload_id]

        return final_object_key

    async def get_file(self, file_id: str, range_header: Optional[str] = None) -> Tuple[bytes, int, int, int]:
        """
        获取文件数据（支持 Range 请求）
        """
        import oss2

        # 查找文件对象
        object_key = self._find_object_by_file_id(file_id)
        if not object_key:
            raise FileNotFoundError(f"文件不存在: {file_id}")

        # 获取对象元数据
        meta = self.bucket.head_object(object_key)
        file_size = meta.content_length

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
        if range_header:
            # OSS 使用 HTTP Range 头格式
            oss_range = f"bytes={start}-{end}"
            result = self.bucket.get_object(object_key, headers={'Range': oss_range})
            data = result.read()
        else:
            result = self.bucket.get_object(object_key)
            data = result.read()

        return data, start, end, file_size

    async def delete_file(self, file_id: str) -> bool:
        """删除文件"""
        try:
            object_key = self._find_object_by_file_id(file_id)
            if object_key:
                self.bucket.delete_object(object_key)
                return True
            return False
        except Exception:
            return False

    async def cleanup_chunks(self, upload_id: str):
        """
        清理临时分片

        取消未完成的分片上传
        """
        if upload_id in self._multipart_uploads:
            upload_info = self._multipart_uploads[upload_id]
            try:
                self.bucket.abort_multipart_upload(
                    upload_info['object_key'],
                    upload_info['oss_upload_id']
                )
            except Exception:
                pass
            finally:
                del self._multipart_uploads[upload_id]

    def get_file_path(self, file_id: str, filename: str) -> str:
        """生成 OSS 对象路径"""
        # 使用 file_id 作为前缀避免冲突
        safe_filename = self._sanitize_filename(filename)
        return f"files/{file_id}_{safe_filename}"

    def _get_chunk_object_key(self, upload_id: str) -> str:
        """获取分片临时对象路径"""
        return f"chunks/{upload_id}/data"

    def _find_object_by_file_id(self, file_id: str) -> Optional[str]:
        """根据 file_id 查找 OSS 对象"""
        import oss2

        # 列出以 file_id 开头的对象
        prefix = f"files/{file_id}_"
        for obj in oss2.ObjectIterator(self.bucket, prefix=prefix):
            return obj.key

        return None

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，防止路径问题"""
        # 移除路径分隔符
        filename = filename.replace('/', '_').replace('\\', '_')
        # 移除特殊字符
        filename = ''.join(c for c in filename if c.isalnum() or c in '._-')
        return filename