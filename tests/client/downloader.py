"""
文件下载器
实现文件下载和进度显示
"""

from pathlib import Path

import requests
from tqdm import tqdm

from .api import APIClient


class FileDownloader:
    """文件下载器"""

    def __init__(self, api_client: APIClient):
        self.client = api_client

    def download(self, file_id: str, output_path: str = None) -> str:
        """
        下载文件

        Args:
            file_id: 文件ID
            output_path: 输出路径（可选，默认为当前目录）

        Returns:
            保存的文件路径
        """
        # 构建下载URL
        url = f"{self.client.base_url}{self.client.api_prefix}/download/{file_id}"

        # 发起请求
        print(f"正在下载文件: {file_id}")
        resp = requests.get(url, stream=True)
        resp.raise_for_status()

        # 获取文件信息
        total_size = int(resp.headers.get("content-length", 0))

        # 从响应头获取文件名
        content_disp = resp.headers.get("content-disposition", "")
        filename = file_id
        if "filename=" in content_disp:
            filename = content_disp.split("filename=")[1].strip('"')

        # 确定输出路径
        if output_path is None:
            output_path = filename
        else:
            output_path = Path(output_path)
            if output_path.is_dir():
                output_path = output_path / filename

        # 确保输出目录存在
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 下载文件并显示进度
        with tqdm(
            total=total_size,
            desc="下载进度",
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar.update(len(chunk))

        print(f"\n下载完成!")
        print(f"保存路径: {output_path.absolute()}")
        print(f"文件大小: {total_size / 1024 / 1024:.2f} MB")

        return str(output_path)