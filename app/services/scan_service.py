"""
病毒扫描服务
"""
import logging
import socket
from typing import Optional, Tuple
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ScanResult:
    """扫描结果"""

    def __init__(self, is_clean: bool, message: str = "", details: str = ""):
        self.is_clean = is_clean
        self.message = message
        self.details = details


class ScanService:
    """病毒扫描服务"""

    def __init__(self):
        """初始化扫描服务"""
        self.enabled = settings.VIRUS_SCAN_ENABLED
        self.engine = settings.VIRUS_SCAN_ENGINE

    def scan_file(self, file_path: str) -> ScanResult:
        """
        扫描文件

        Args:
            file_path: 文件路径

        Returns:
            ScanResult: 扫描结果
        """
        if not self.enabled:
            return ScanResult(is_clean=True, message="病毒扫描未启用")

        if self.engine == "clamav":
            return self._scan_with_clamav(file_path)
        elif self.engine == "api":
            return self._scan_with_api(file_path)
        else:
            logger.warning(f"未知的扫描引擎: {self.engine}")
            return ScanResult(is_clean=True, message="未知扫描引擎")

    def scan_data(self, data: bytes, filename: str = "unknown") -> ScanResult:
        """
        扫描数据

        对于数据流，需要先保存到临时文件再扫描

        Args:
            data: 文件数据
            filename: 文件名（用于日志）

        Returns:
            ScanResult: 扫描结果
        """
        if not self.enabled:
            return ScanResult(is_clean=True, message="病毒扫描未启用")

        # 保存到临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(data)
            temp_path = f.name

        try:
            return self.scan_file(temp_path)
        finally:
            # 清理临时文件
            Path(temp_path).unlink(missing_ok=True)

    def _scan_with_clamav(self, file_path: str) -> ScanResult:
        """
        使用 ClamAV 扫描文件

        通过 socket 连接 clamd daemon

        Args:
            file_path: 文件路径

        Returns:
            ScanResult: 扫描结果
        """
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(60)  # 60 秒超时
            sock.connect(settings.CLAMAV_SOCKET)

            # 发送 SCAN 命令
            command = f"SCAN {file_path}\n"
            sock.sendall(command.encode())

            # 接收响应
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk

            sock.close()

            # 解析响应
            response_str = response.decode().strip()
            logger.debug(f"ClamAV 响应: {response_str}")

            if "FOUND" in response_str:
                # 检测到病毒
                virus_name = response_str.split(":")[-1].strip().replace("FOUND", "").strip()
                return ScanResult(
                    is_clean=False,
                    message=f"检测到病毒: {virus_name}",
                    details=response_str
                )
            elif "OK" in response_str:
                return ScanResult(is_clean=True, message="文件安全")
            else:
                logger.warning(f"ClamAV 响应异常: {response_str}")
                return ScanResult(is_clean=True, message="扫描完成", details=response_str)

        except FileNotFoundError:
            logger.error(f"ClamAV socket 不存在: {settings.CLAMAV_SOCKET}")
            return ScanResult(is_clean=True, message="ClamAV 未安装或未运行")
        except socket.timeout:
            logger.error("ClamAV 扫描超时")
            return ScanResult(is_clean=True, message="扫描超时")
        except Exception as e:
            logger.error(f"ClamAV 扫描异常: {e}")
            return ScanResult(is_clean=True, message=f"扫描异常: {str(e)}")

    def _scan_with_api(self, file_path: str) -> ScanResult:
        """
        使用外部 API 扫描文件

        Args:
            file_path: 文件路径

        Returns:
            ScanResult: 扫描结果
        """
        if not settings.VIRUS_SCAN_API_URL:
            logger.error("病毒扫描 API URL 未配置")
            return ScanResult(is_clean=True, message="API URL 未配置")

        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                with httpx.Client(timeout=120) as client:
                    response = client.post(
                        settings.VIRUS_SCAN_API_URL,
                        files=files
                    )

            if response.status_code == 200:
                result = response.json()
                is_clean = result.get("is_clean", True)
                message = result.get("message", "")
                details = result.get("details", "")
                return ScanResult(is_clean=is_clean, message=message, details=details)
            else:
                logger.error(f"API 扫描失败: {response.status_code}")
                return ScanResult(is_clean=True, message=f"API 返回错误: {response.status_code}")

        except Exception as e:
            logger.error(f"API 扫描异常: {e}")
            return ScanResult(is_clean=True, message=f"扫描异常: {str(e)}")


# 全局扫描服务实例
scan_service = ScanService() if settings.VIRUS_SCAN_ENABLED else None


def get_scan_service() -> Optional[ScanService]:
    """获取扫描服务实例"""
    return scan_service