# -*- coding: utf-8 -*-
"""
Blog AI Domain - Agent Tools

WordPress MCPと連携するためのOpenAI Agents SDKツール定義
"""

import base64
import re
from typing import Any, Dict, List, Optional

import logging

from agents import function_tool, RunContextWrapper

from app.domains.blog.context import BlogContext, ArticleStyle, WordPressArticle

logger = logging.getLogger(__name__)


# =====================================================
# WordPress MCP ツール
# =====================================================


@function_tool
async def get_wordpress_article(
    ctx: RunContextWrapper[BlogContext],
    url: str,
) -> Dict[str, Any]:
    """
    WordPress記事をURLから取得して分析する

    Args:
        url: 取得する記事のURL

    Returns:
        記事の内容とメタデータ
    """
    logger.info(f"WordPress記事を取得: {url}")

    # MCPサービスを取得
    mcp_service = ctx.context.mcp_service
    if not mcp_service:
        return {
            "success": False,
            "error": "WordPress MCPサービスが設定されていません",
        }

    try:
        result = await mcp_service.get_post_by_url(url)

        # コンテキストに保存
        if result.get("content"):
            ctx.context.reference_article = WordPressArticle(
                post_id=result.get("id", 0),
                title=result.get("title", ""),
                content=result.get("content", ""),
                excerpt=result.get("excerpt"),
                status=result.get("status", "publish"),
                categories=result.get("categories", []),
                tags=result.get("tags", []),
                featured_image_id=result.get("featured_media"),
            )

        return {
            "success": True,
            "article": {
                "id": result.get("id"),
                "title": result.get("title"),
                "content": result.get("content"),
                "excerpt": result.get("excerpt"),
                "status": result.get("status"),
                "categories": result.get("categories", []),
                "tags": result.get("tags", []),
                "date": result.get("date"),
                "modified": result.get("modified"),
                "link": result.get("link"),
            },
        }
    except Exception as e:
        logger.error(f"WordPress記事取得エラー: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@function_tool
async def analyze_site_style(
    ctx: RunContextWrapper[BlogContext],
    num_articles: int = 5,
) -> Dict[str, Any]:
    """
    WordPressサイトの過去記事を分析し、トンマナ・スタイルを抽出する

    Args:
        num_articles: 分析する記事数（デフォルト5件）

    Returns:
        サイトのスタイル分析結果
    """
    logger.info(f"サイトスタイルを分析: {num_articles}件の記事")

    mcp_service = ctx.context.mcp_service
    if not mcp_service:
        return {
            "success": False,
            "error": "WordPress MCPサービスが設定されていません",
        }

    try:
        # 最近の記事を取得
        recent_posts = await mcp_service.get_recent_posts(limit=num_articles)

        if not recent_posts:
            return {
                "success": True,
                "style": {
                    "tone": "neutral",
                    "vocabulary": [],
                    "block_patterns": [],
                    "note": "分析可能な記事が見つかりませんでした",
                },
            }

        # 記事内容を分析
        all_content = []
        block_patterns = []
        headings = []

        for post in recent_posts:
            content = post.get("content", "")
            all_content.append(content)

            # Gutenbergブロックパターンを抽出
            block_matches = re.findall(r'<!-- wp:([a-z0-9-/]+)', content)
            block_patterns.extend(block_matches)

            # 見出しを抽出
            heading_matches = re.findall(r'<h[2-4][^>]*>(.*?)</h[2-4]>', content)
            headings.extend(heading_matches)

        # 頻出ブロックパターンを集計
        block_freq = {}
        for block in block_patterns:
            block_freq[block] = block_freq.get(block, 0) + 1

        sorted_blocks = sorted(
            block_freq.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        # スタイル情報を構築
        style_info = ArticleStyle(
            tone="analyzed",  # 実際のトーン分析はAIモデルに任せる
            vocabulary=[],
            sentence_patterns=[],
            block_patterns=[
                {"name": name, "frequency": freq}
                for name, freq in sorted_blocks
            ],
            heading_style=headings[0] if headings else None,
        )

        ctx.context.analyzed_style = style_info

        return {
            "success": True,
            "style": {
                "total_articles_analyzed": len(recent_posts),
                "common_block_patterns": [
                    {"name": name, "frequency": freq}
                    for name, freq in sorted_blocks
                ],
                "sample_headings": headings[:5],
                "recommendation": "上記のブロックパターンと見出しスタイルを参考に記事を作成してください",
            },
        }
    except Exception as e:
        logger.error(f"サイトスタイル分析エラー: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@function_tool
async def upload_media_to_wordpress(
    ctx: RunContextWrapper[BlogContext],
    image_index: int,
    alt_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    アップロード済み画像をWordPressメディアライブラリにアップロードする

    Args:
        image_index: アップロードする画像のインデックス（uploaded_images内）
        alt_text: 代替テキスト

    Returns:
        アップロード結果（media_id, url）
    """
    logger.info(f"WordPressにメディアをアップロード: image_index={image_index}")

    mcp_service = ctx.context.mcp_service
    if not mcp_service:
        return {
            "success": False,
            "error": "WordPress MCPサービスが設定されていません",
        }

    # アップロード済み画像を取得
    if image_index < 0 or image_index >= len(ctx.context.uploaded_images):
        return {
            "success": False,
            "error": f"無効な画像インデックス: {image_index}",
        }

    image = ctx.context.uploaded_images[image_index]

    # すでにWordPressにアップロード済みの場合
    if image.wp_media_id:
        return {
            "success": True,
            "already_uploaded": True,
            "media_id": image.wp_media_id,
            "url": image.wp_url,
        }

    # ローカルパスから画像データを読み込み
    if not image.local_path:
        return {
            "success": False,
            "error": "画像のローカルパスが設定されていません",
        }

    try:
        with open(image.local_path, "rb") as f:
            file_data = f.read()

        # MIMEタイプを推定
        mime_type = "image/jpeg"
        if image.filename.lower().endswith(".png"):
            mime_type = "image/png"
        elif image.filename.lower().endswith(".gif"):
            mime_type = "image/gif"
        elif image.filename.lower().endswith(".webp"):
            mime_type = "image/webp"

        result = await mcp_service.upload_media(
            file_data=file_data,
            filename=image.filename,
            mime_type=mime_type,
            alt_text=alt_text,
        )

        # コンテキストを更新
        image.wp_media_id = result.get("id")
        image.wp_url = result.get("url")

        return {
            "success": True,
            "media_id": result.get("id"),
            "url": result.get("url"),
            "alt": result.get("alt_text"),
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"画像ファイルが見つかりません: {image.local_path}",
        }
    except Exception as e:
        logger.error(f"メディアアップロードエラー: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@function_tool
async def create_draft_post(
    ctx: RunContextWrapper[BlogContext],
    title: str,
    content: str,
    excerpt: Optional[str] = None,
    categories: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    featured_image_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    WordPressに下書き記事を作成する

    Args:
        title: 記事タイトル
        content: 記事本文（Gutenbergブロック形式推奨）
        excerpt: 抜粋
        categories: カテゴリ名のリスト
        tags: タグ名のリスト
        featured_image_id: アイキャッチ画像のメディアID

    Returns:
        作成された下書き記事の情報
    """
    logger.info(f"下書き記事を作成: {title}")

    mcp_service = ctx.context.mcp_service
    if not mcp_service:
        return {
            "success": False,
            "error": "WordPress MCPサービスが設定されていません",
        }

    try:
        result = await mcp_service.create_draft_post(
            title=title,
            content=content,
            excerpt=excerpt,
            categories=categories,
            tags=tags,
            featured_image_id=featured_image_id,
        )

        # コンテキストを更新
        ctx.context.generated_title = title
        ctx.context.generated_content = content
        ctx.context.generated_excerpt = excerpt
        ctx.context.draft_post_id = result.get("id")
        ctx.context.draft_preview_url = result.get("preview_url")
        ctx.context.draft_edit_url = result.get("edit_url")
        ctx.context.current_step = "completed"

        return {
            "success": True,
            "post_id": result.get("id"),
            "preview_url": result.get("preview_url"),
            "edit_url": result.get("edit_url"),
            "status": "draft",
            "message": "下書き記事が正常に作成されました",
        }
    except Exception as e:
        logger.error(f"下書き作成エラー: {e}")
        ctx.context.current_step = "error"
        ctx.context.error_message = str(e)
        return {
            "success": False,
            "error": str(e),
        }


@function_tool
async def request_additional_info(
    ctx: RunContextWrapper[BlogContext],
    questions: List[Dict[str, Any]],
    explanation: str,
) -> Dict[str, Any]:
    """
    ユーザーに追加情報をリクエストする

    Args:
        questions: 質問のリスト
            各質問: {
                "question_id": str,
                "question": str,
                "input_type": "text" | "textarea" | "file" | "select",
                "options": List[str] (selectの場合),
                "required": bool
            }
        explanation: なぜこの情報が必要かの説明

    Returns:
        リクエスト結果
    """
    logger.info(f"追加情報をリクエスト: {len(questions)}件の質問")

    from app.domains.blog.context import AIQuestion

    # コンテキストに質問を保存
    ctx.context.ai_questions = [
        AIQuestion(
            question_id=q["question_id"],
            question=q["question"],
            context=explanation,
            input_type=q.get("input_type", "text"),
            options=q.get("options"),
            required=q.get("required", True),
        )
        for q in questions
    ]

    ctx.context.current_step = "waiting_for_user_input"

    return {
        "success": True,
        "status": "waiting_for_user_input",
        "questions_count": len(questions),
        "message": "ユーザーからの回答を待機中です",
    }


@function_tool
async def get_available_images(
    ctx: RunContextWrapper[BlogContext],
) -> Dict[str, Any]:
    """
    ユーザーがアップロードした画像の一覧を取得する

    Returns:
        アップロード済み画像のリスト
    """
    images = ctx.context.uploaded_images

    if not images:
        return {
            "success": True,
            "images": [],
            "message": "アップロードされた画像はありません",
        }

    return {
        "success": True,
        "images": [
            {
                "index": i,
                "filename": img.filename,
                "local_path": img.local_path,
                "wp_media_id": img.wp_media_id,
                "wp_url": img.wp_url,
                "uploaded_to_wordpress": img.wp_media_id is not None,
            }
            for i, img in enumerate(images)
        ],
        "total_count": len(images),
    }
