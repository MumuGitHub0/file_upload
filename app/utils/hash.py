"""
文件哈希计算工具
"""
import hashlib
from typing import BinaryIO


def calculate_hash(file_data: BinaryIO, algorithm: str = "md5") -> str:
    """
    计算文件哈希值
    
    Args:
        file_data: 文件数据流
        algorithm: 哈希算法（md5, sha1, sha256）
    
    Returns:
        哈希值（十六进制字符串）
    """
    hash_func = getattr(hashlib, algorithm)()
    
    # 重置文件指针
    file_data.seek(0)
    
    # 分块读取并计算哈希
    for chunk in iter(lambda: file_data.read(8192), b""):
        hash_func.update(chunk)
    
    return hash_func.hexdigest()


def calculate_chunk_hash(chunk_data: bytes, algorithm: str = "md5") -> str:
    """
    计算分片哈希值
    
    Args:
        chunk_data: 分片数据
        algorithm: 哈希算法（md5, sha1, sha256）
    
    Returns:
        哈希值（十六进制字符串）
    """
    hash_func = getattr(hashlib, algorithm)()
    hash_func.update(chunk_data)
    return hash_func.hexdigest()