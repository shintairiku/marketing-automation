# -*- coding: utf-8 -*-
"""
Blog AI Domain - Agent Tools

OpenAI Agents SDK の function_tool を使って WordPress MCP ツールをラップ

参考: shintairiku-ai-agent/backend/app/infrastructure/chatkit/wordpress_tools.py
"""
import json
import logging
from typing import List, Literal, Optional

from agents import function_tool, WebSearchTool

from app.domains.blog.services.wordpress_mcp_service import (
    call_wordpress_mcp_tool,
    get_current_process_id,
    MCP_LONG_TIMEOUT,
    MCPError,
)

logger = logging.getLogger(__name__)


# ========== ユーザー質問ツール ==========

@function_tool
async def ask_user_questions(
    questions: List[str],
    input_types: Optional[List[str]] = None,
    context: Optional[str] = None,
) -> str:
    """記事作成に必要な情報をユーザーに質問します。

    このツールを使うと、ユーザーに質問を送信し、回答を待ちます。
    質問数に制限はありません。記事に必要な情報を自由に聞いてください。

    Args:
        questions: ユーザーへの質問リスト（日本語で記述）
            例: ["インタビュー対象者のお名前を教えてください", "商品の写真をアップロードしてください"]
        input_types: 各質問の入力タイプ（省略時は全て "textarea"）
            指定可能な値:
            - "textarea": テキスト入力（デフォルト）
            - "image_upload": 画像アップロード（写真・商品画像・人物写真など）
            例: ["textarea", "image_upload"]
        context: 質問の文脈説明（オプション）
            例: "インタビュー記事を作成するために、以下の情報が必要です"

    Returns:
        質問送信成功メッセージ。このツール呼び出し後、
        処理は一時停止しユーザーの回答を待ちます。
        回答が届き次第、その情報を使って記事生成を続行します。
    """
    return json.dumps({
        "status": "questions_sent",
        "question_count": len(questions),
        "input_types": input_types or (["textarea"] * len(questions)),
        "message": "質問をユーザーに送信しました。ユーザーの回答を待っています。これ以上の処理は行わないでください。",
    }, ensure_ascii=False)


# ========== 記事取得系ツール ==========

@function_tool
async def wp_get_posts_by_category(
    category_id: int,
    limit: Optional[int] = None,
    order: Optional[Literal["DESC", "ASC"]] = None,
    orderby: Optional[Literal["date", "title", "modified"]] = None,
) -> str:
    """指定カテゴリの記事一覧を取得します。

    Args:
        category_id: カテゴリID
        limit: 取得件数（最大100、デフォルト10）
        order: 並び順
        orderby: ソート基準
    """
    args = {"category_id": category_id}
    if limit is not None:
        args["limit"] = limit
    if order is not None:
        args["order"] = order
    if orderby is not None:
        args["orderby"] = orderby
    return await call_wordpress_mcp_tool("wp-mcp-get-posts-by-category", args)


@function_tool
async def wp_get_post_block_structure(post_id: int) -> str:
    """記事のGutenbergブロック構造をJSON形式で取得します。

    Args:
        post_id: 記事ID
    """
    return await call_wordpress_mcp_tool("wp-mcp-get-post-block-structure", {"post_id": post_id})


@function_tool
async def wp_get_post_raw_content(post_id: int) -> str:
    """記事の生コンテンツ（ブロックHTML）を取得します。

    Args:
        post_id: 記事ID
    """
    return await call_wordpress_mcp_tool("wp-mcp-get-post-raw-content", {"post_id": post_id})


@function_tool
async def wp_get_recent_posts(
    limit: Optional[int] = None,
    post_type: Optional[str] = None,
) -> str:
    """最近の記事一覧を取得します。

    Args:
        limit: 取得件数（デフォルト10）
        post_type: 投稿タイプ（デフォルト: post）
    """
    args = {}
    if limit is not None:
        args["limit"] = limit
    if post_type is not None:
        args["post_type"] = post_type
    return await call_wordpress_mcp_tool("wp-mcp-get-recent-posts", args)


@function_tool
async def wp_get_post_by_url(url: str) -> str:
    """URLから記事を取得します。

    Args:
        url: 記事URL
    """
    return await call_wordpress_mcp_tool("wp-mcp-get-post-by-url", {"url": url})


@function_tool
async def wp_analyze_category_format_patterns(
    category_id: int,
    sample_count: Optional[int] = None,
) -> str:
    """カテゴリ内の記事から共通フォーマットパターンを抽出します。

    Args:
        category_id: カテゴリID
        sample_count: サンプル数（最大20、デフォルト5）
    """
    args = {"category_id": category_id}
    if sample_count is not None:
        args["sample_count"] = sample_count
    return await call_wordpress_mcp_tool("wp-mcp-analyze-category-format-patterns", args)


# ========== ブロック・テーマ系ツール ==========

@function_tool
async def wp_extract_used_blocks(
    post_type: Optional[str] = None,
    limit: Optional[int] = None,
) -> str:
    """指定範囲の記事から使用ブロックの頻度を抽出します。

    Args:
        post_type: 投稿タイプ（デフォルト: post）
        limit: 取得件数（最大500、デフォルト100）
    """
    args = {}
    if post_type is not None:
        args["post_type"] = post_type
    if limit is not None:
        args["limit"] = limit
    return await call_wordpress_mcp_tool("wp-mcp-extract-used-blocks", args)


@function_tool
async def wp_get_theme_styles() -> str:
    """テーマのグローバルスタイル設定を取得します。"""
    return await call_wordpress_mcp_tool("wp-mcp-get-theme-styles", {})


@function_tool
async def wp_get_block_patterns(category: Optional[str] = None) -> str:
    """登録済みのブロックパターン一覧を取得します。

    Args:
        category: パターンカテゴリ
    """
    args = {}
    if category is not None:
        args["category"] = category
    return await call_wordpress_mcp_tool("wp-mcp-get-block-patterns", args)


@function_tool
async def wp_get_reusable_blocks(per_page: Optional[int] = None) -> str:
    """再利用ブロック一覧を取得します。

    Args:
        per_page: 取得件数（最大200、デフォルト100）
    """
    args = {}
    if per_page is not None:
        args["per_page"] = per_page
    return await call_wordpress_mcp_tool("wp-mcp-get-reusable-blocks", args)


# ========== 記事作成・更新系ツール ==========

@function_tool
async def wp_create_draft_post(
    title: str,
    content: str,
    post_type: Optional[str] = None,
    category_ids: Optional[List[int]] = None,
    tag_ids: Optional[List[int]] = None,
    excerpt: Optional[str] = None,
) -> str:
    """GutenbergブロックHTMLで新規下書きを作成します。

    必ず下書き（draft）として保存されます。公開（publish）にはしません。
    指定した投稿タイプが無効な場合は、post で再試行します。

    Args:
        title: 記事タイトル
        content: ブロックHTML形式のコンテンツ
        post_type: 投稿タイプ（デフォルト: post）
        category_ids: カテゴリIDの配列
        tag_ids: タグIDの配列
        excerpt: 抜粋
    """
    args = {"title": title, "content": content}
    if post_type is not None:
        args["post_type"] = post_type
    if category_ids is not None:
        args["category_ids"] = category_ids
    if tag_ids is not None:
        args["tag_ids"] = tag_ids
    if excerpt is not None:
        args["excerpt"] = excerpt

    requested_post_type = args.get("post_type")

    try:
        return await call_wordpress_mcp_tool("wp-mcp-create-draft-post", args)
    except MCPError as e:
        # 新仕様の invalid_post_type に対して post へフォールバック（後方互換のため）
        error_message = (e.message or "").lower()
        error_code = str(e.code).lower() if e.code is not None else ""
        is_invalid_post_type = (
            "invalid_post_type" in error_message
            or "invalid_post_type" in error_code
            or "post_type not found" in error_message
        )
        if requested_post_type and requested_post_type != "post" and is_invalid_post_type:
            logger.warning(
                "投稿タイプ '%s' が無効のため post にフォールバックします: %s",
                requested_post_type,
                e.message,
            )
            fallback_args = dict(args)
            fallback_args["post_type"] = "post"
            return await call_wordpress_mcp_tool("wp-mcp-create-draft-post", fallback_args)
        raise


@function_tool
async def wp_update_post_content(
    post_id: int,
    content: str,
    title: Optional[str] = None,
) -> str:
    """既存記事のコンテンツを更新します。

    Args:
        post_id: 記事ID
        content: 新しいブロックHTML形式のコンテンツ
        title: 新しいタイトル
    """
    args = {"post_id": post_id, "content": content}
    if title is not None:
        args["title"] = title
    return await call_wordpress_mcp_tool("wp-mcp-update-post-content", args)


@function_tool
async def wp_update_post_meta(
    post_id: int,
    meta_key: str,
    meta_value: str,
) -> str:
    """記事のメタ情報を更新します。

    Args:
        post_id: 記事ID
        meta_key: メタキー
        meta_value: メタ値（文字列）
    """
    return await call_wordpress_mcp_tool("wp-mcp-update-post-meta", {
        "post_id": post_id,
        "meta_key": meta_key,
        "meta_value": meta_value,
    })


# ========== バリデーション系ツール ==========

@function_tool
async def wp_validate_block_content(content: str) -> str:
    """ブロックコンテンツの構文・形式チェックを行います。

    Args:
        content: 検証するブロックHTMLコンテンツ
    """
    return await call_wordpress_mcp_tool("wp-mcp-validate-block-content", {"content": content})


@function_tool
async def wp_check_regulation_compliance(
    content: str,
    category_id: int,
) -> str:
    """カテゴリ別レギュレーションへの準拠を検証します。

    Args:
        content: 検証するコンテンツ
        category_id: カテゴリID
    """
    return await call_wordpress_mcp_tool("wp-mcp-check-regulation-compliance", {
        "content": content,
        "category_id": category_id,
    })


@function_tool
async def wp_check_seo_requirements(
    content: str,
    target_keywords: Optional[List[str]] = None,
    title: Optional[str] = None,
) -> str:
    """SEO要件チェックを行います。

    Args:
        content: 検証するコンテンツ
        target_keywords: ターゲットキーワード
        title: 記事タイトル
    """
    args = {"content": content}
    if target_keywords is not None:
        args["target_keywords"] = target_keywords
    if title is not None:
        args["title"] = title
    return await call_wordpress_mcp_tool("wp-mcp-check-seo-requirements", args)


# ========== メディア系ツール ==========

@function_tool
async def wp_get_media_library(
    search: Optional[str] = None,
    mime_type: Optional[str] = None,
    per_page: Optional[int] = None,
) -> str:
    """メディアライブラリから画像・ファイル一覧を取得します。

    Args:
        search: 検索キーワード
        mime_type: MIMEタイプ
        per_page: 取得件数（最大100、デフォルト20）
    """
    args = {}
    if search is not None:
        args["search"] = search
    if mime_type is not None:
        args["mime_type"] = mime_type
    if per_page is not None:
        args["per_page"] = per_page
    return await call_wordpress_mcp_tool("wp-mcp-get-media-library", args)


@function_tool
async def wp_upload_media(
    source: str,
    filename: str,
    title: Optional[str] = None,
    alt: Optional[str] = None,
    caption: Optional[str] = None,
) -> str:
    """URLまたはBase64からメディアをアップロードします。

    Args:
        source: 画像URL or Base64データ
        filename: ファイル名
        title: メディアタイトル
        alt: 代替テキスト
        caption: キャプション
    """
    args = {"source": source, "filename": filename}
    if title is not None:
        args["title"] = title
    if alt is not None:
        args["alt"] = alt
    if caption is not None:
        args["caption"] = caption
    return await call_wordpress_mcp_tool("wp-mcp-upload-media", args, timeout=MCP_LONG_TIMEOUT)


@function_tool
async def wp_set_featured_image(post_id: int, media_id: int) -> str:
    """記事のアイキャッチ画像を設定します。

    Args:
        post_id: 記事ID
        media_id: メディアID
    """
    return await call_wordpress_mcp_tool("wp-mcp-set-featured-image", {
        "post_id": post_id,
        "media_id": media_id,
    })


# ========== タクソノミー・サイト情報系ツール ==========

@function_tool
async def wp_get_categories(
    parent: Optional[int] = None,
    hide_empty: Optional[bool] = None,
) -> str:
    """カテゴリ一覧を取得します。

    Args:
        parent: 親カテゴリID
        hide_empty: 空のカテゴリを非表示
    """
    args = {}
    if parent is not None:
        args["parent"] = parent
    if hide_empty is not None:
        args["hide_empty"] = hide_empty
    return await call_wordpress_mcp_tool("wp-mcp-get-categories", args)


@function_tool
async def wp_get_tags(
    search: Optional[str] = None,
    per_page: Optional[int] = None,
) -> str:
    """タグ一覧を取得します。

    Args:
        search: 検索キーワード
        per_page: 取得件数（最大200、デフォルト100）
    """
    args = {}
    if search is not None:
        args["search"] = search
    if per_page is not None:
        args["per_page"] = per_page
    return await call_wordpress_mcp_tool("wp-mcp-get-tags", args)


@function_tool
async def wp_create_term(
    taxonomy: Literal["category", "post_tag"],
    name: str,
    slug: Optional[str] = None,
    parent: Optional[int] = None,
) -> str:
    """カテゴリまたはタグを新規作成します。

    Args:
        taxonomy: タクソノミー種別
        name: 名前
        slug: スラッグ
        parent: 親ID（カテゴリのみ）
    """
    args = {"taxonomy": taxonomy, "name": name}
    if slug is not None:
        args["slug"] = slug
    if parent is not None:
        args["parent"] = parent
    return await call_wordpress_mcp_tool("wp-mcp-create-term", args)


@function_tool
async def wp_get_site_info() -> str:
    """サイトの基本情報を取得します。"""
    return await call_wordpress_mcp_tool("wp-mcp-get-site-info", {})


@function_tool
async def wp_get_post_types(public_only: Optional[bool] = None) -> str:
    """利用可能な投稿タイプ一覧を取得します。

    Args:
        public_only: 公開タイプのみ（デフォルト: true）
    """
    args = {}
    if public_only is not None:
        args["public_only"] = public_only
    return await call_wordpress_mcp_tool("wp-mcp-get-post-types", args)


@function_tool
async def wp_get_article_regulations(category_id: Optional[int] = None) -> str:
    """カテゴリ別のレギュレーション設定を取得します。

    Args:
        category_id: カテゴリID
    """
    args = {}
    if category_id is not None:
        args["category_id"] = category_id
    return await call_wordpress_mcp_tool("wp-mcp-get-article-regulations", args)


# ========== ユーザー画像 WordPress アップロードツール ==========

@function_tool
async def upload_user_image_to_wordpress(
    image_index: int,
    alt: str,
    title: Optional[str] = None,
    caption: Optional[str] = None,
) -> str:
    """ユーザーがアップロードした画像を WordPress にアップロードします。

    ユーザーが記事に含めたい画像をアップロードしている場合、
    このツールで WordPress メディアライブラリに登録できます。
    戻り値の url を記事の画像ブロックに使用してください。

    Args:
        image_index: アップロードする画像のインデックス（0始まり）
            入力メッセージに含まれる画像の順番に対応します。
        alt: 画像の代替テキスト（SEO・アクセシビリティ用、日本語で記述）
        title: メディアタイトル（省略時は自動生成）
        caption: キャプション（省略時はなし）

    Returns:
        JSON文字列: {"media_id": int, "url": str, "width": int, "height": int}
        または エラーメッセージ
    """
    from app.common.database import supabase
    from app.domains.blog.services.image_utils import read_as_data_uri

    process_id = get_current_process_id()
    if not process_id:
        return json.dumps({
            "error": "process_id が設定されていません。画像アップロードは利用できません。"
        }, ensure_ascii=False)

    try:
        # DB から uploaded_images を取得
        result = supabase.table("blog_generation_state").select(
            "uploaded_images"
        ).eq("id", process_id).single().execute()

        if not result.data:
            return json.dumps({
                "error": f"プロセス {process_id} が見つかりません。"
            }, ensure_ascii=False)

        uploaded_images = result.data.get("uploaded_images", [])

        if image_index < 0 or image_index >= len(uploaded_images):
            return json.dumps({
                "error": f"画像インデックス {image_index} は範囲外です。"
                         f"利用可能な画像: 0〜{len(uploaded_images) - 1}"
            }, ensure_ascii=False)

        image_info = uploaded_images[image_index]

        # 既に WordPress にアップロード済みの場合はキャッシュ返却
        if image_info.get("wp_media_id") and image_info.get("wp_url"):
            logger.info(
                f"Image {image_index} already uploaded to WordPress: "
                f"media_id={image_info['wp_media_id']}"
            )
            return json.dumps({
                "media_id": image_info["wp_media_id"],
                "url": image_info["wp_url"],
                "width": image_info.get("wp_width", 0),
                "height": image_info.get("wp_height", 0),
            }, ensure_ascii=False)

        local_path = image_info.get("local_path")
        if not local_path:
            return json.dumps({
                "error": f"画像 {image_index} のローカルパスが見つかりません。"
            }, ensure_ascii=False)

        import os
        if not os.path.exists(local_path):
            return json.dumps({
                "error": f"画像ファイルが見つかりません: {local_path}"
            }, ensure_ascii=False)

        # Base64 data URI に変換
        data_uri = read_as_data_uri(local_path)

        # WordPress MCP 経由でアップロード
        filename = image_info.get("filename", f"image_{image_index}.webp")
        mcp_args = {
            "source": data_uri,
            "filename": filename,
        }
        if title:
            mcp_args["title"] = title
        if alt:
            mcp_args["alt"] = alt
        if caption:
            mcp_args["caption"] = caption

        mcp_result = await call_wordpress_mcp_tool(
            "wp-mcp-upload-media", mcp_args, timeout=MCP_LONG_TIMEOUT
        )

        # MCP結果をパース
        try:
            mcp_data = json.loads(mcp_result)
        except (json.JSONDecodeError, TypeError):
            mcp_data = {}

        wp_media_id = mcp_data.get("media_id")
        wp_url = mcp_data.get("url", "")
        wp_width = mcp_data.get("width", 0)
        wp_height = mcp_data.get("height", 0)

        # DB の uploaded_images を更新（wp_media_id, wp_url を書き戻し）
        uploaded_images[image_index]["wp_media_id"] = wp_media_id
        uploaded_images[image_index]["wp_url"] = wp_url
        uploaded_images[image_index]["wp_width"] = wp_width
        uploaded_images[image_index]["wp_height"] = wp_height

        supabase.table("blog_generation_state").update({
            "uploaded_images": uploaded_images,
        }).eq("id", process_id).execute()

        logger.info(
            f"Image {image_index} uploaded to WordPress: "
            f"media_id={wp_media_id}, url={wp_url}"
        )

        return json.dumps({
            "media_id": wp_media_id,
            "url": wp_url,
            "width": wp_width,
            "height": wp_height,
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"upload_user_image_to_wordpress エラー: {e}", exc_info=True)
        return json.dumps({
            "error": f"画像アップロードに失敗しました: {str(e)}"
        }, ensure_ascii=False)


# ========== Web検索ツール ==========

web_search_tool = WebSearchTool(
    user_location={"type": "approximate", "country": "JP"},
    search_context_size="medium",
)


# ========== 全ツールをエクスポート ==========

ALL_WORDPRESS_TOOLS = [
    # Web検索
    web_search_tool,
    # ユーザー対話系
    ask_user_questions,
    # 記事取得系
    wp_get_posts_by_category,
    wp_get_post_block_structure,
    wp_get_post_raw_content,
    wp_get_recent_posts,
    wp_get_post_by_url,
    wp_analyze_category_format_patterns,
    # ブロック・テーマ系
    wp_extract_used_blocks,
    wp_get_theme_styles,
    wp_get_block_patterns,
    wp_get_reusable_blocks,
    # 記事作成・更新系
    wp_create_draft_post,
    wp_update_post_content,
    wp_update_post_meta,
    # バリデーション系
    wp_validate_block_content,
    wp_check_regulation_compliance,
    wp_check_seo_requirements,
    # メディア系
    wp_get_media_library,
    wp_upload_media,
    wp_set_featured_image,
    # ユーザー画像アップロード
    upload_user_image_to_wordpress,
    # タクソノミー・サイト情報系
    wp_get_categories,
    wp_get_tags,
    wp_create_term,
    wp_get_site_info,
    wp_get_post_types,
    wp_get_article_regulations,
]
