# 大文件上传下载服务

基于 FastAPI 构建的大文件上传下载服务，支持分片上传、断点续传、进度追踪。

## 功能特性

- **分片上传**: 将大文件分割成小块上传，提高稳定性和成功率
- **断点续传**: 上传中断后可从断点继续，无需重新上传
- **进度追踪**: 实时返回上传进度百分比
- **双存储支持**: 本地文件系统 + 对象存储（OSS/S3），可通过配置切换
- **文件去重**: 相同文件哈希只存储一次
- **分段下载**: 支持 Range 请求头实现分段下载

## 技术栈

- **框架**: FastAPI
- **数据库**: SQLite（通过 SQLAlchemy ORM）
- **异步文件操作**: aiofiles
- **配置管理**: python-dotenv

## 快速开始

### 1. 安装依赖

```bash
# 生产环境依赖
uv sync

# 包含测试客户端的开发环境依赖
uv sync --extra dev
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并根据需要修改：

```bash
cp .env.example .env
```

#### 配置项说明

**必须配置的项**：

| 配置项 | 说明 | 默认值 | 是否必须 |
|--------|------|--------|----------|
| STORAGE_BACKEND | 存储后端（local/oss） | local | 是 |
| CORS_ORIGINS | CORS 允许来源 | * | 生产环境必须修改 |
| DEBUG | 调试模式 | false | 生产环境必须为 false |

**可选配置的项**：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| HOST | 监听地址 | 0.0.0.0 |
| PORT | 监听端口 | 8000 |
| CHUNK_SIZE | 分片大小（字节） | 5242880 (5MB) |
| MAX_FILE_SIZE | 最大文件大小（字节） | 1073741824 (1GB) |
| ALLOWED_EXTENSIONS | 允许的文件扩展名 | 空（不限制） |
| LOG_LEVEL | 日志级别 | INFO |

**OSS 配置（STORAGE_BACKEND=oss 时必须）**：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| OSS_ENDPOINT | OSS 区域节点 | https://oss-cn-hangzhou.aliyuncs.com |
| OSS_ACCESS_KEY_ID | AccessKey ID | your-access-key-id |
| OSS_ACCESS_KEY_SECRET | AccessKey Secret | your-access-key-secret |
| OSS_BUCKET_NAME | Bucket 名称 | your-bucket-name |

**应用常量（硬编码，不可配置）**：

以下配置项已硬编码在代码中，不需要在 `.env` 中配置：

- APP_NAME: 大文件上传下载服务
- APP_VERSION: 0.1.0
- API_PREFIX: /api/v1
- MAX_CHUNK_SIZE: 52428800 (50MB)
- MIN_CHUNK_SIZE: 1048576 (1MB)

#### 配置示例

**最小化配置（本地开发）**

```env
STORAGE_BACKEND=local
CHUNK_SIZE=5242880
MAX_FILE_SIZE=1073741824
```

**生产环境配置示例**

```env
DEBUG=false
STORAGE_BACKEND=oss
OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com
OSS_ACCESS_KEY_ID=your-access-key-id
OSS_ACCESS_KEY_SECRET=your-access-key-secret
OSS_BUCKET_NAME=your-bucket-name
CHUNK_SIZE=10485760
MAX_FILE_SIZE=10737418240
ALLOWED_EXTENSIONS=.jpg,.png,.mp4,.pdf
CORS_ORIGINS=https://example.com,https://api.example.com
LOG_LEVEL=WARNING
DATABASE_URL=postgresql://user:password@localhost/filedb
```

### 3. 启动服务

```bash
# 使用 uv（推荐）
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或直接运行
python -m app.main
```

### 4. 访问 API 文档

启动服务后，访问以下地址查看交互式 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 接口文档

### 上传流程

#### 1. 初始化上传

**POST** `/api/v1/upload/init`

请求体：
```json
{
  "filename": "example.mp4",
  "file_size": 524288000,
  "file_hash": "md5hash"
}
```

响应：
```json
{
  "upload_id": "uuid",
  "chunk_size": 5242880,
  "chunk_count": 100,
  "uploaded_chunks": []
}
```

#### 2. 上传分片

**POST** `/api/v1/upload/chunk/{upload_id}`

请求：FormData
- `chunk_index`: 分片索引（从 0 开始）
- `chunk_data`: 分片数据（二进制）

响应：
```json
{
  "chunk_index": 0,
  "status": "success",
  "message": "分片 0 上传成功"
}
```

#### 3. 完成上传

**POST** `/api/v1/upload/complete/{upload_id}`

响应：
```json
{
  "file_id": "uuid",
  "url": "/download/{file_id}",
  "filename": "example.mp4",
  "file_size": 524288000
}
```

#### 4. 查询进度

**GET** `/api/v1/upload/progress/{upload_id}`

响应：
```json
{
  "upload_id": "uuid",
  "uploaded_chunks": 50,
  "total_chunks": 100,
  "progress": 50.0,
  "status": "uploading"
}
```

### 下载流程

#### 1. 下载文件

**GET** `/api/v1/download/{file_id}`

支持 Range 请求头实现分段下载：
```
Range: bytes=0-1023
```

响应：文件流（application/octet-stream）

#### 2. 文件列表

**GET** `/api/v1/files`

查询参数：
- `skip`: 跳过数量（默认 0）
- `limit`: 限制数量（默认 100）

响应：
```json
{
  "files": [
    {
      "file_id": "uuid",
      "filename": "example.mp4",
      "file_size": 524288000,
      "created_at": "2026-07-16T10:00:00",
      "status": "completed"
    }
  ],
  "total": 1
}
```

#### 3. 删除文件

**DELETE** `/api/v1/files/{file_id}`

响应：
```json
{
  "success": true,
  "message": "文件已删除"
}
```

## 使用示例

### Python 客户端示例

```python
import hashlib
import requests
from pathlib import Path

def calculate_file_hash(file_path):
    """计算文件 MD5 哈希"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def upload_large_file(file_path, api_base="http://localhost:8000/api/v1"):
    """上传大文件"""
    file_path = Path(file_path)
    file_size = file_path.stat().st_size
    file_hash = calculate_file_hash(file_path)
    
    # 1. 初始化上传
    init_resp = requests.post(f"{api_base}/upload/init", json={
        "filename": file_path.name,
        "file_size": file_size,
        "file_hash": file_hash
    })
    init_data = init_resp.json()
    upload_id = init_data["upload_id"]
    chunk_size = init_data["chunk_size"]
    
    print(f"Upload ID: {upload_id}")
    print(f"Chunk size: {chunk_size}")
    print(f"Already uploaded: {init_data['uploaded_chunks']}")
    
    # 2. 上传分片
    with open(file_path, "rb") as f:
        chunk_index = 0
        while True:
            chunk_data = f.read(chunk_size)
            if not chunk_data:
                break
            
            # 跳过已上传的分片
            if chunk_index in init_data["uploaded_chunks"]:
                chunk_index += 1
                continue
            
            files = {"chunk_data": chunk_data}
            data = {"chunk_index": chunk_index}
            requests.post(
                f"{api_base}/upload/chunk/{upload_id}",
                files=files,
                data=data
            )
            
            # 查询进度
            progress_resp = requests.get(f"{api_base}/upload/progress/{upload_id}")
            progress = progress_resp.json()["progress"]
            print(f"Progress: {progress:.1f}%")
            
            chunk_index += 1
    
    # 3. 完成上传
    complete_resp = requests.post(f"{api_base}/upload/complete/{upload_id}")
    result = complete_resp.json()
    print(f"Upload complete! File ID: {result['file_id']}")
    print(f"Download URL: {result['url']}")
    
    return result

# 使用示例
upload_large_file("large_file.mp4")
```

### 测试客户端

项目内置了命令行测试客户端，用于快速测试 API 功能。

**安装开发依赖**：
```bash
uv sync --extra dev
```

**使用示例**：
```bash
# 上传文件
uv run python tests/main.py upload large_file.mp4

# 列出文件
uv run python tests/main.py list

# 下载文件
uv run python tests/main.py download <file_id>

# 查看帮助
uv run python tests/main.py --help
```

详细使用说明请参见 [tests/README.md](tests/README.md)。

### cURL 示例

#### 初始化上传
```bash
curl -X POST "http://localhost:8000/api/v1/upload/init" \
  -H "Content-Type: application/json" \
  -d '{"filename":"test.mp4","file_size":104857600,"file_hash":"abc123"}'
```

#### 上传分片
```bash
curl -X POST "http://localhost:8000/api/v1/upload/chunk/{upload_id}" \
  -F "chunk_index=0" \
  -F "chunk_data=@chunk0.bin"
```

#### 完成上传
```bash
curl -X POST "http://localhost:8000/api/v1/upload/complete/{upload_id}"
```

#### 下载文件
```bash
# 下载完整文件
curl -O "http://localhost:8000/api/v1/download/{file_id}"

# 分段下载（Range 请求）
curl -H "Range: bytes=0-1023" -O "http://localhost:8000/api/v1/download/{file_id}"
```

## 项目结构

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── models/
│   │   ├── __init__.py
│   │   └── file.py          # 文件元数据模型
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── upload.py        # Pydantic 模型（请求/响应）
│   ├── api/
│   │   ├── __init__.py
│   │   └── upload.py        # 上传下载路由
│   ├── services/
│   │   ├── __init__.py
│   │   ├── upload_service.py      # 上传业务逻辑
│   │   └── download_service.py    # 下载业务逻辑
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py          # 存储抽象基类
│   │   ├── local.py         # 本地存储实现
│   │   └── oss.py           # 对象存储实现（待实现）
│   └── utils/
│       ├── __init__.py
│       └── hash.py          # 文件哈希计算工具
├── tests/                   # 测试客户端（开发依赖）
│   ├── client/
│   │   ├── __init__.py
│   │   ├── api.py           # API 客户端封装
│   │   ├── downloader.py    # 文件下载器
│   │   └── uploader.py      # 文件上传器
│   ├── main.py              # CLI 入口
│   └── README.md            # 客户端使用文档
├── data/                    # 数据目录（自动创建）
│   ├── files/               # 上传文件存储目录
│   ├── chunks/              # 临时分片存储目录
│   └── metadata.db          # SQLite 数据库文件
├── .env                     # 环境变量配置
├── .env.example             # 环境变量示例
├── pyproject.toml           # 项目配置
└── README.md                # 项目文档
```

## 安全考虑

- 文件大小限制（默认 1GB）
- 文件名清理（防止路径遍历攻击）
- 分片索引验证
- 未完成上传任务清理（待实现）

## 性能优化建议

1. **分片大小**: 根据网络状况调整，建议 5-10MB
2. **并发上传**: 客户端可并行上传多个分片
3. **对象存储**: 生产环境建议使用 OSS/S3
4. **缓存**: 使用 Redis 缓存上传状态（可选）

## 扩展功能（待实现）

- [ ] 对象存储（OSS/S3）支持
- [ ] 文件类型验证
- [ ] 病毒扫描集成
- [ ] 文件过期自动清理
- [ ] 上传回调通知
- [ ] 图片/视频在线预览

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！