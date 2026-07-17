"""
上传回调通知服务
"""
import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class CallbackService:
    """回调通知服务"""

    def __init__(self):
        """初始化回调服务"""
        self.callback_url = settings.UPLOAD_CALLBACK_URL
        self.timeout = settings.UPLOAD_CALLBACK_TIMEOUT
        self.retries = settings.UPLOAD_CALLBACK_RETRIES

    async def send_callback(
        self,
        upload_id: str,
        file_id: str,
        filename: str,
        file_size: int,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送回调通知

        Args:
            upload_id: 上传任务 ID
            file_id: 文件 ID
            filename: 文件名
            file_size: 文件大小
            status: 状态
            metadata: 额外元数据

        Returns:
            是否发送成功
        """
        if not self.callback_url:
            logger.debug("回调 URL 未配置，跳过回调")
            return True

        payload = {
            "upload_id": upload_id,
            "file_id": file_id,
            "filename": filename,
            "file_size": file_size,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        for attempt in range(1, self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.callback_url,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )

                if response.status_code == 200:
                    logger.info(f"回调发送成功: {upload_id}")
                    return True
                else:
                    logger.warning(
                        f"回调返回非 200 状态码: {response.status_code}, "
                        f"尝试 {attempt}/{self.retries}"
                    )

            except httpx.TimeoutException:
                logger.warning(f"回调超时，尝试 {attempt}/{self.retries}")
            except Exception as e:
                logger.error(f"回调发送异常: {e}, 尝试 {attempt}/{self.retries}")

            # 等待后重试
            if attempt < self.retries:
                await asyncio.sleep(2 ** attempt)  # 指数退避

        logger.error(f"回调发送失败，已重试 {self.retries} 次: {upload_id}")
        return False

    async def send_upload_complete_callback(
        self,
        upload_id: str,
        file_id: str,
        filename: str,
        file_size: int,
        download_url: str
    ) -> bool:
        """
        发送上传完成回调

        Args:
            upload_id: 上传任务 ID
            file_id: 文件 ID
            filename: 文件名
            file_size: 文件大小
            download_url: 下载链接

        Returns:
            是否发送成功
        """
        return await self.send_callback(
            upload_id=upload_id,
            file_id=file_id,
            filename=filename,
            file_size=file_size,
            status="completed",
            metadata={"download_url": download_url}
        )

    async def send_upload_failed_callback(
        self,
        upload_id: str,
        file_id: str,
        filename: str,
        file_size: int,
        error_message: str
    ) -> bool:
        """
        发送上传失败回调

        Args:
            upload_id: 上传任务 ID
            file_id: 文件 ID
            filename: 文件名
            file_size: 文件大小
            error_message: 错误信息

        Returns:
            是否发送成功
        """
        return await self.send_callback(
            upload_id=upload_id,
            file_id=file_id,
            filename=filename,
            file_size=file_size,
            status="failed",
            metadata={"error": error_message}
        )


# 全局回调服务实例
callback_service = CallbackService() if settings.UPLOAD_CALLBACK_URL else None


def get_callback_service() -> Optional[CallbackService]:
    """获取回调服务实例"""
    return callback_service