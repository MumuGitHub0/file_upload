"""
大文件上传下载客户端CLI工具
"""

import argparse
import json
import sys

from client import APIClient, FileDownloader, FileUploader


def cmd_upload(args):
    """上传文件命令"""
    api = APIClient(base_url=args.server)
    uploader = FileUploader(api)

    try:
        result = uploader.upload(args.file)
        return 0
    except FileNotFoundError as e:
        print(f"错误: {e}")
        return 1
    except Exception as e:
        print(f"上传失败: {e}")
        return 1


def cmd_download(args):
    """下载文件命令"""
    api = APIClient(base_url=args.server)
    downloader = FileDownloader(api)

    try:
        downloader.download(args.file_id, args.output)
        return 0
    except Exception as e:
        print(f"下载失败: {e}")
        return 1


def cmd_list(args):
    """列出文件命令"""
    api = APIClient(base_url=args.server)

    try:
        result = api.list_files(skip=args.skip, limit=args.limit)
        files = result.get("files", [])
        total = result.get("total", 0)

        if not files:
            print("没有文件")
            return 0

        print(f"文件列表 (共 {total} 个):\n")
        print(f"{'文件ID':<40} {'文件名':<30} {'大小':<15} {'上传时间':<20} {'状态':<10}")
        print("-" * 115)

        for file in files:
            file_id = file.get("file_id", "")
            filename = file.get("filename", "")
            file_size = file.get("file_size", 0)
            created_at = file.get("created_at", "")
            status = file.get("status", "")

            # 格式化文件大小
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.2f} KB"
            elif file_size < 1024 * 1024 * 1024:
                size_str = f"{file_size / 1024 / 1024:.2f} MB"
            else:
                size_str = f"{file_size / 1024 / 1024 / 1024:.2f} GB"

            print(f"{file_id:<40} {filename:<30} {size_str:<15} {created_at:<20} {status:<10}")

        return 0
    except Exception as e:
        print(f"获取文件列表失败: {e}")
        return 1


def cmd_delete(args):
    """删除文件命令"""
    api = APIClient(base_url=args.server)

    try:
        result = api.delete_file(args.file_id)
        print(f"文件已删除: {args.file_id}")
        return 0
    except Exception as e:
        print(f"删除失败: {e}")
        return 1


def cmd_progress(args):
    """查询上传进度命令"""
    api = APIClient(base_url=args.server)

    try:
        result = api.get_progress(args.upload_id)
        print(f"\n上传ID: {result['upload_id']}")
        print(f"已上传分片: {result['uploaded_chunks']}/{result['total_chunks']}")
        print(f"进度: {result['progress']:.1f}%")
        print(f"状态: {result['status']}")
        return 0
    except Exception as e:
        print(f"查询进度失败: {e}")
        return 1


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="大文件上传下载客户端",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--server",
        default="http://127.0.0.1:8001",
        help="服务端地址 (默认: http://127.0.0.1:8001)",
    )

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # upload 命令
    upload_parser = subparsers.add_parser("upload", help="上传文件")
    upload_parser.add_argument("file", help="要上传的文件路径")
    upload_parser.set_defaults(func=cmd_upload)

    # download 命令
    download_parser = subparsers.add_parser("download", help="下载文件")
    download_parser.add_argument("file_id", help="文件ID")
    download_parser.add_argument("-o", "--output", help="输出路径")
    download_parser.set_defaults(func=cmd_download)

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出文件")
    list_parser.add_argument("--skip", type=int, default=0, help="跳过数量")
    list_parser.add_argument("--limit", type=int, default=100, help="限制数量")
    list_parser.set_defaults(func=cmd_list)

    # delete 命令
    delete_parser = subparsers.add_parser("delete", help="删除文件")
    delete_parser.add_argument("file_id", help="文件ID")
    delete_parser.set_defaults(func=cmd_delete)

    # progress 命令
    progress_parser = subparsers.add_parser("progress", help="查询上传进度")
    progress_parser.add_argument("upload_id", help="上传ID")
    progress_parser.set_defaults(func=cmd_progress)

    args = parser.parse_args()

    if hasattr(args, "func"):
        return args.func(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())