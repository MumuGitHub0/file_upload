"""
文件验证工具
"""
import mimetypes
from typing import Optional, List, Tuple
from fastapi import HTTPException, status


# 常见文件类型的 Magic Number 签名
MAGIC_NUMBERS = {
    # 图片
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'GIF87a': 'image/gif',
    b'GIF89a': 'image/gif',
    b'RIFF': 'image/webp',  # WebP 以 RIFF 开头
    b'\x00\x00\x01\x00': 'image/x-icon',  # ICO

    # 文档
    b'%PDF': 'application/pdf',
    b'PK\x03\x04': 'application/zip',  # ZIP, DOCX, XLSX 等

    # 视频
    b'\x00\x00\x00\x1cftyp': 'video/mp4',  # MP4
    b'\x00\x00\x00\x20ftyp': 'video/mp4',  # MP4
    b'ftyp': 'video/mp4',  # MP4 (通用检测)
    b'\x1aE\xdf\xa3': 'video/webm',  # WebM/MKV
    b'RIFF': 'video/webm',  # AVI 也以 RIFF 开头

    # 音频
    b'ID3': 'audio/mpeg',  # MP3
    b'\xff\xfb': 'audio/mpeg',  # MP3
    b'\xff\xfa': 'audio/mpeg',  # MP3
    b'\xff\xf3': 'audio/mpeg',  # MP3
    b'\xff\xf2': 'audio/mpeg',  # MP3
    b'OggS': 'audio/ogg',  # OGG

    # 压缩文件
    b'\x50\x4b\x03\x04': 'application/zip',
    b'\x52\x61\x72\x21': 'application/x-rar-compressed',
    b'\x1f\x8b': 'application/gzip',
}

# MIME 类型到扩展名的映射
MIME_TO_EXTENSION = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'image/webp': ['.webp'],
    'image/x-icon': ['.ico'],
    'application/pdf': ['.pdf'],
    'application/zip': ['.zip'],
    'video/mp4': ['.mp4'],
    'video/webm': ['.webm'],
    'audio/mpeg': ['.mp3'],
    'audio/ogg': ['.ogg'],
    'application/x-rar-compressed': ['.rar'],
    'application/gzip': ['.gz'],
}


def validate_file_extension(filename: str, allowed_extensions: Optional[List[str]]) -> Tuple[bool, Optional[str]]:
    """
    验证文件扩展名

    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名列表（如 ['.jpg', '.png']），None 表示不限制

    Returns:
        (是否通过, 错误消息)
    """
    if not allowed_extensions:
        return True, None

    # 获取文件扩展名
    ext = ''
    if '.' in filename:
        ext = '.' + filename.rsplit('.', 1)[-1].lower()

    if not ext:
        return False, f"文件缺少扩展名，允许的扩展名: {', '.join(allowed_extensions)}"

    if ext not in allowed_extensions:
        return False, f"文件类型不允许: {ext}，允许的扩展名: {', '.join(allowed_extensions)}"

    return True, None


def get_mime_type(filename: str) -> Optional[str]:
    """
    根据文件名获取 MIME 类型

    Args:
        filename: 文件名

    Returns:
        MIME 类型字符串
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type


def detect_mime_type(data: bytes) -> Optional[str]:
    """
    根据文件内容检测 MIME 类型（Magic Number 检测）

    Args:
        data: 文件数据（前几字节即可）

    Returns:
        检测到的 MIME 类型
    """
    # 检查常见 Magic Number
    for magic, mime_type in MAGIC_NUMBERS.items():
        if data.startswith(magic):
            return mime_type

    return None


def validate_mime_type(data: bytes, expected_types: Optional[List[str]]) -> Tuple[bool, Optional[str]]:
    """
    验证文件内容的 MIME 类型

    Args:
        data: 文件数据
        expected_types: 期望的 MIME 类型列表，None 表示不验证

    Returns:
        (是否通过, 错误消息)
    """
    if not expected_types:
        return True, None

    detected_type = detect_mime_type(data)

    if not detected_type:
        # 无法检测类型，跳过验证
        return True, None

    if detected_type not in expected_types:
        return False, f"文件内容类型不匹配: 检测到 {detected_type}，期望: {', '.join(expected_types)}"

    return True, None


def validate_upload_file(
    filename: str,
    file_data: Optional[bytes] = None,
    allowed_extensions: Optional[List[str]] = None,
    validate_content: bool = False
) -> None:
    """
    验证上传文件

    Args:
        filename: 文件名
        file_data: 文件数据（用于内容验证）
        allowed_extensions: 允许的扩展名列表
        validate_content: 是否验证文件内容

    Raises:
        HTTPException: 验证失败时抛出
    """
    # 验证扩展名
    is_valid, error_msg = validate_file_extension(filename, allowed_extensions)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # 验证文件内容
    if validate_content and file_data:
        allowed_mimes = []
        if allowed_extensions:
            for ext in allowed_extensions:
                for mime, exts in MIME_TO_EXTENSION.items():
                    if ext in exts and mime not in allowed_mimes:
                        allowed_mimes.append(mime)

        is_valid, error_msg = validate_mime_type(file_data[:32], allowed_mimes if allowed_mimes else None)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )