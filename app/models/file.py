"""
文件元数据模型
"""
import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Integer, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

Base = declarative_base()


class FileMetadata(Base):
    """文件元数据模型"""
    __tablename__ = "file_metadata"
    
    id = Column(String(36), primary_key=True)  # UUID
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_hash = Column(String(64), nullable=False)  # MD5 hash
    upload_id = Column(String(36), unique=True, nullable=False)  # UUID
    chunk_size = Column(Integer, nullable=False)
    chunk_count = Column(Integer, nullable=False)
    uploaded_chunks = Column(Text, default="[]")  # JSON list
    status = Column(String(20), default="uploading")  # uploading/completed/failed
    storage_backend = Column(String(20), nullable=False)
    storage_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_uploaded_chunks(self) -> List[int]:
        """获取已上传分片列表"""
        return json.loads(self.uploaded_chunks)
    
    def set_uploaded_chunks(self, chunks: List[int]):
        """设置已上传分片列表"""
        self.uploaded_chunks = json.dumps(sorted(chunks))
    
    def add_uploaded_chunk(self, chunk_index: int):
        """添加已上传分片"""
        chunks = self.get_uploaded_chunks()
        if chunk_index not in chunks:
            chunks.append(chunk_index)
            self.set_uploaded_chunks(chunks)
    
    @property
    def progress(self) -> float:
        """计算上传进度"""
        if self.chunk_count == 0:
            return 0.0
        return len(self.get_uploaded_chunks()) / self.chunk_count * 100


# 创建数据库引擎和会话
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite 需要
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)