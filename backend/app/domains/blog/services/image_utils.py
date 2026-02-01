# -*- coding: utf-8 -*-
"""
Blog AI Domain - Image Utilities

ユーザーアップロード画像の WebP 変換・Base64 読み込みユーティリティ。
WordPress MCP には WebP 形式で送信するため、アップロード時に変換する。
"""

import base64
import io
import logging
import os
import uuid

from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

# WebP 変換設定
WEBP_QUALITY = 85
MAX_DIMENSION = 2048  # 長辺の最大ピクセル数


def _get_upload_dir(process_id: str) -> str:
    """プロセス別アップロードディレクトリを取得（なければ作成）"""
    base_dir = getattr(settings, "temp_upload_dir", None) or "/tmp/blog_uploads"
    upload_dir = os.path.join(base_dir, process_id)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def convert_and_save_as_webp(
    image_bytes: bytes,
    original_filename: str,
    process_id: str,
    quality: int = WEBP_QUALITY,
) -> str:
    """
    画像バイトを WebP に変換してローカルに保存する。

    Args:
        image_bytes: 元画像のバイトデータ
        original_filename: 元のファイル名（拡張子を除いて WebP にリネーム）
        process_id: プロセスID（保存先ディレクトリ名）
        quality: WebP 圧縮品質 (1-100)

    Returns:
        保存先のローカルパス
    """
    img = Image.open(io.BytesIO(image_bytes))

    # RGBA/P モードは RGB に変換（WebP は RGB で保存）
    if img.mode in ("RGBA", "LA", "P"):
        # RGBA は透過情報を保持したまま WebP に保存可能だが、
        # WordPress での互換性を考慮して RGB に変換
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = background

    # 大きすぎる画像はリサイズ
    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
        logger.info(
            f"Image resized to {img.size[0]}x{img.size[1]} "
            f"(max dimension: {MAX_DIMENSION})"
        )

    upload_dir = _get_upload_dir(process_id)
    name_without_ext = os.path.splitext(original_filename)[0]
    filename = f"{uuid.uuid4()}_{name_without_ext}.webp"
    local_path = os.path.join(upload_dir, filename)

    img.save(local_path, format="WEBP", quality=quality)
    logger.info(f"Image saved as WebP: {local_path} ({os.path.getsize(local_path)} bytes)")

    return local_path


def read_as_base64(local_path: str) -> str:
    """
    ローカルファイルを Base64 エンコードして返す。

    Args:
        local_path: ファイルパス

    Returns:
        Base64 エンコード文字列（data URI プレフィックスなし）
    """
    with open(local_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def read_as_data_uri(local_path: str) -> str:
    """
    ローカル WebP ファイルを data URI 形式で返す。

    Args:
        local_path: WebP ファイルパス

    Returns:
        data:image/webp;base64,... 形式の文字列
    """
    b64 = read_as_base64(local_path)
    return f"data:image/webp;base64,{b64}"


def cleanup_process_images(process_id: str) -> None:
    """
    プロセスの一時画像ファイルを全て削除する。

    Args:
        process_id: プロセスID
    """
    import shutil

    base_dir = getattr(settings, "temp_upload_dir", None) or "/tmp/blog_uploads"
    upload_dir = os.path.join(base_dir, process_id)
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir, ignore_errors=True)
        logger.info(f"Cleaned up images for process {process_id}")
