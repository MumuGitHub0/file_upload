# 测试客户端

大文件上传下载服务的命令行客户端工具，用于测试服务端 API 功能。

## 功能特性

- **分片上传**: 自动将大文件分片上传
- **断点续传**: 上传中断后可从断点继续
- **进度显示**: 实时显示上传/下载进度条
- **文件管理**: 支持文件列表查看和删除

## 安装依赖

客户端依赖已配置为开发依赖，需要使用 `--extra dev` 参数安装：

```bash
uv sync --extra dev
```

## 使用方法

所有命令需要通过 `uv run` 执行，确保在正确的虚拟环境中运行。

### 上传文件

```bash
uv run python tests/main.py upload <文件路径>
```

示例：
```bash
uv run python tests/main.py upload video.mp4
uv run python tests/main.py upload /path/to/large_file.zip
```

### 下载文件

```bash
uv run python tests/main.py download <文件ID> [-o 输出路径]
```

示例：
```bash
# 下载到当前目录
uv run python tests/main.py download abc123-def456

# 下载到指定路径
uv run python tests/main.py download abc123-def456 -o /path/to/save/
```

### 列出文件

```bash
uv run python tests/main.py list [--skip N] [--limit N]
```

示例：
```bash
# 列出所有文件
uv run python tests/main.py list

# 分页查询
uv run python tests/main.py list --skip 10 --limit 20
```

### 删除文件

```bash
uv run python tests/main.py delete <文件ID>
```

示例：
```bash
uv run python tests/main.py delete abc123-def456
```

### 查询上传进度

```bash
uv run python tests/main.py progress <上传ID>
```

示例：
```bash
uv run python tests/main.py progress upload-uuid-12345
```

## 高级选项

### 指定服务端地址

所有命令都支持 `--server` 参数指定服务端地址：

```bash
uv run python tests/main.py --server http://192.168.1.100:8000 upload file.mp4
```

默认服务端地址为 `http://127.0.0.1:8001`

### 查看帮助

```bash
# 查看总帮助
uv run python tests/main.py --help

# 查看子命令帮助
uv run python tests/main.py upload --help
uv run python tests/main.py download --help
```

## 工作原理

1. **上传流程**:
   - 计算文件MD5哈希
   - 调用服务端初始化上传接口
   - 根据返回的分片大小分片上传
   - 自动跳过已上传的分片（断点续传）
   - 完成上传并返回文件ID

2. **下载流程**:
   - 通过文件ID请求下载
   - 流式下载并显示进度条
   - 自动从响应头获取文件名

## 依赖项

- `requests>=2.31.0` - HTTP请求库
- `tqdm>=4.66.0` - 进度条显示

## 许可证

MIT License