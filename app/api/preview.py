"""
预览 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config import settings
from app.models.file import get_db
from app.services.preview_service import PreviewService

router = APIRouter(prefix=settings.API_PREFIX, tags=["preview"])


@router.get("/preview/{file_id}", summary="获取文件预览")
async def get_preview(
    file_id: str,
    db: Session = Depends(get_db)
):
    """
    获取文件预览

    支持图片和视频文件的在线预览

    - **file_id**: 文件 ID
    """
    if not settings.PREVIEW_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="预览功能未启用"
        )

    try:
        service = PreviewService(db)
        data, mime_type, file_type = await service.get_preview(file_id)

        return Response(
            content=data,
            media_type=mime_type,
            headers={
                "Content-Disposition": f"inline; filename={file_id}",
                "X-File-Type": file_type
            }
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/thumbnail/{file_id}", summary="获取文件缩略图")
async def get_thumbnail(
    file_id: str,
    width: int = None,
    height: int = None,
    db: Session = Depends(get_db)
):
    """
    获取文件缩略图

    为图片和视频文件生成缩略图

    - **file_id**: 文件 ID
    - **width**: 缩略图宽度（可选）
    - **height**: 缩略图高度（可选）
    """
    if not settings.PREVIEW_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="预览功能未启用"
        )

    try:
        service = PreviewService(db)
        data, mime_type = await service.generate_thumbnail(file_id, width, height)

        return Response(
            content=data,
            media_type=mime_type,
            headers={
                "Content-Disposition": f"inline; filename={file_id}_thumbnail.jpg",
                "Cache-Control": "max-age=86400"  # 缓存 24 小时
            }
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )