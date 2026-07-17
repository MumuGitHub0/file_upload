"""
文件预览服务
"""
import io
import logging
from typing import Optional, Tuple
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.file import FileMetadata
from app.storage import get_storage_backend
from app.config import settings

logger = logging.getLogger(__name__)


class PreviewService:
    """文件预览服务"""

    def __init__(self, db: Session):
        """初始化预览服务"""
        self.db = db
        self.storage = get_storage_backend()
        self.supported_types = settings.get_preview_supported_types()

    def is_preview_supported(self, filename: str) -> bool:
        """
        检查文件是否支持预览

        Args:
            filename: 文件名

        Returns:
            是否支持预览
        """
        if not settings.PREVIEW_ENABLED:
            return False

        ext = ''
        if '.' in filename:
            ext = '.' + filename.rsplit('.', 1)[-1].lower()

        return ext in self.supported_types

    def get_file_type(self, filename: str) -> str:
        """
        获取文件类型

        Args:
            filename: 文件名

        Returns:
            文件类型 (image/video/unknown)
        """
        ext = ''
        if '.' in filename:
            ext = '.' + filename.rsplit('.', 1)[-1].lower()

        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        video_extensions = ['.mp4', '.webm', '.mov', '.avi']

        if ext in image_extensions:
            return 'image'
        elif ext in video_extensions:
            return 'video'
        else:
            return 'unknown'

    async def get_preview(self, file_id: str) -> Tuple[bytes, str, str]:
        """
        获取文件预览

        Args:
            file_id: 文件 ID

        Returns:
            (文件数据, MIME 类型, 文件类型)
        """
        # 查找文件
        file_metadata = self.db.query(FileMetadata).filter(
            FileMetadata.id == file_id,
            FileMetadata.status == "completed"
        ).first()

        if not file_metadata:
            raise FileNotFoundError(f"文件不存在: {file_id}")

        if not self.is_preview_supported(file_metadata.filename):
            raise ValueError(f"文件不支持预览: {file_metadata.filename}")

        # 获取文件数据
        data, _, _, _ = await self.storage.get_file(file_id)

        # 确定 MIME 类型
        file_type = self.get_file_type(file_metadata.filename)
        mime_type = self._get_mime_type(file_metadata.filename)

        return data, mime_type, file_type

    async def generate_thumbnail(self, file_id: str, width: int = None, height: int = None) -> Tuple[bytes, str]:
        """
        生成缩略图

        Args:
            file_id: 文件 ID
            width: 缩略图宽度
            height: 缩略图高度

        Returns:
            (缩略图数据, MIME 类型)
        """
        if width is None or height is None:
            width, height = settings.get_thumbnail_size()

        # 查找文件
        file_metadata = self.db.query(FileMetadata).filter(
            FileMetadata.id == file_id,
            FileMetadata.status == "completed"
        ).first()

        if not file_metadata:
            raise FileNotFoundError(f"文件不存在: {file_id}")

        file_type = self.get_file_type(file_metadata.filename)

        if file_type == 'image':
            return await self._generate_image_thumbnail(file_id, width, height)
        elif file_type == 'video':
            return await self._generate_video_thumbnail(file_id, width, height)
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")

    async def _generate_image_thumbnail(self, file_id: str, width: int, height: int) -> Tuple[bytes, str]:
        """
        生成图片缩略图

        Args:
            file_id: 文件 ID
            width: 宽度
            height: 高度

        Returns:
            (缩略图数据, MIME 类型)
        """
        try:
            from PIL import Image
        except ImportError:
            logger.warning("Pillow 未安装，无法生成图片缩略图")
            # 返回原图
            data, _, _ = await self.get_preview(file_id)
            return data, 'image/jpeg'

        # 获取原图
        data, _, _ = await self.get_preview(file_id)

        # 打开图片
        img = Image.open(io.BytesIO(data))

        # 保持宽高比缩放
        img.thumbnail((width, height), Image.LANCZOS)

        # 转换为 RGB（如果是 RGBA）
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        # 保存到内存
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85)
        output.seek(0)

        return output.read(), 'image/jpeg'

    async def _generate_video_thumbnail(self, file_id: str, width: int, height: int) -> Tuple[bytes, str]:
        """
        生成视频缩略图

        注意：视频缩略图需要 ffmpeg 支持

        Args:
            file_id: 文件 ID
            width: 宽度
            height: 高度

        Returns:
            (缩略图数据, MIME 类型)
        """
        # 视频缩略图需要 ffmpeg，这里返回占位图
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            raise RuntimeError("Pillow 未安装，无法生成视频缩略图")

        # 生成占位图
        img = Image.new('RGB', (width, height), color='#cccccc')
        draw = ImageDraw.Draw(img)
        draw.text((width // 4, height // 2), "Video", fill='#666666')

        output = io.BytesIO()
        img.save(output, format='JPEG')
        output.seek(0)

        return output.read(), 'image/jpeg'

    def _get_mime_type(self, filename: str) -> str:
        """
        获取 MIME 类型

        Args:
            filename: 文件名

        Returns:
            MIME 类型
        """
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'