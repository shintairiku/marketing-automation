# -*- coding: utf-8 -*-
"""
Blog AI Domain - Context

ブログ生成プロセスのコンテキスト（エージェント実行に使用）
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

if TYPE_CHECKING:
    from app.domains.blog.services.wordpress_mcp_service import WordPressMcpService


@dataclass
class UploadedImage:
    """アップロードされた画像情報"""
    filename: str
    local_path: Optional[str] = None
    wp_media_id: Optional[int] = None
    wp_url: Optional[str] = None
    uploaded_at: Optional[datetime] = None


@dataclass
class WordPressArticle:
    """WordPress記事情報"""
    post_id: int
    title: str
    content: str
    excerpt: Optional[str] = None
    status: str = "publish"
    categories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    featured_image_id: Optional[int] = None
    custom_css: Optional[str] = None
    block_structure: Optional[Dict[str, Any]] = None


@dataclass
class ArticleStyle:
    """記事スタイル分析結果"""
    tone: str = ""  # フォーマル、カジュアル、etc.
    vocabulary: List[str] = field(default_factory=list)
    sentence_patterns: List[str] = field(default_factory=list)
    block_patterns: List[Dict[str, Any]] = field(default_factory=list)
    custom_css_classes: List[str] = field(default_factory=list)
    heading_style: Optional[str] = None
    paragraph_style: Optional[str] = None


@dataclass
class AIQuestion:
    """AIからの質問"""
    question_id: str
    question: str
    context: Optional[str] = None
    input_type: str = "text"  # text, textarea, file, select
    options: Optional[List[str]] = None
    required: bool = True


@dataclass
class BlogContext:
    """ブログ生成プロセスのコンテキスト"""

    # ===== ユーザー入力 =====
    user_prompt: str = ""
    reference_url: Optional[str] = None
    wordpress_site_id: Optional[str] = None

    # ===== WordPress MCP =====
    mcp_endpoint: Optional[str] = None
    mcp_access_token: Optional[str] = None
    mcp_session_id: Optional[str] = None
    mcp_service: Optional["WordPressMcpService"] = field(default=None, repr=False)

    # ===== 参考記事分析 =====
    reference_article: Optional[WordPressArticle] = None
    analyzed_style: Optional[ArticleStyle] = None

    # ===== AI対話 =====
    ai_questions: List[AIQuestion] = field(default_factory=list)
    user_answers: Dict[str, Any] = field(default_factory=dict)

    # ===== アップロード画像 =====
    uploaded_images: List[UploadedImage] = field(default_factory=list)

    # ===== 生成コンテンツ =====
    generated_title: Optional[str] = None
    generated_content: Optional[str] = None  # Gutenbergブロック形式
    generated_excerpt: Optional[str] = None

    # ===== 結果 =====
    draft_post_id: Optional[int] = None
    draft_preview_url: Optional[str] = None
    draft_edit_url: Optional[str] = None

    # ===== プロセス状態 =====
    current_step: Literal[
        "start",
        "analyzing_reference",
        "gathering_info",
        "waiting_for_user_input",
        "generating_content",
        "applying_style",
        "uploading_media",
        "creating_draft",
        "completed",
        "error"
    ] = "start"

    # ===== プロセス管理 =====
    process_id: Optional[str] = None
    user_id: Optional[str] = None
    response_id: Optional[str] = None  # OpenAI Responses API
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """コンテキストを辞書に変換（DB保存用）"""
        return {
            "user_prompt": self.user_prompt,
            "reference_url": self.reference_url,
            "wordpress_site_id": self.wordpress_site_id,
            "mcp_session_id": self.mcp_session_id,
            "reference_article": (
                {
                    "post_id": self.reference_article.post_id,
                    "title": self.reference_article.title,
                    "status": self.reference_article.status,
                }
                if self.reference_article
                else None
            ),
            "analyzed_style": (
                {
                    "tone": self.analyzed_style.tone,
                    "vocabulary": self.analyzed_style.vocabulary[:10],  # 上位10件
                    "block_patterns": self.analyzed_style.block_patterns[:5],
                }
                if self.analyzed_style
                else None
            ),
            "ai_questions": [
                {
                    "question_id": q.question_id,
                    "question": q.question,
                    "input_type": q.input_type,
                }
                for q in self.ai_questions
            ],
            "user_answers": self.user_answers,
            "uploaded_images": [
                {
                    "filename": img.filename,
                    "wp_media_id": img.wp_media_id,
                    "wp_url": img.wp_url,
                }
                for img in self.uploaded_images
            ],
            "generated_title": self.generated_title,
            "draft_post_id": self.draft_post_id,
            "draft_preview_url": self.draft_preview_url,
            "draft_edit_url": self.draft_edit_url,
            "current_step": self.current_step,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BlogContext":
        """辞書からコンテキストを復元"""
        ctx = cls(
            user_prompt=data.get("user_prompt", ""),
            reference_url=data.get("reference_url"),
            wordpress_site_id=data.get("wordpress_site_id"),
            mcp_session_id=data.get("mcp_session_id"),
            generated_title=data.get("generated_title"),
            draft_post_id=data.get("draft_post_id"),
            draft_preview_url=data.get("draft_preview_url"),
            draft_edit_url=data.get("draft_edit_url"),
            current_step=data.get("current_step", "start"),
            error_message=data.get("error_message"),
            user_answers=data.get("user_answers", {}),
        )

        # AI質問の復元
        if "ai_questions" in data:
            ctx.ai_questions = [
                AIQuestion(
                    question_id=q["question_id"],
                    question=q["question"],
                    input_type=q.get("input_type", "text"),
                )
                for q in data["ai_questions"]
            ]

        # アップロード画像の復元
        if "uploaded_images" in data:
            ctx.uploaded_images = [
                UploadedImage(
                    filename=img["filename"],
                    wp_media_id=img.get("wp_media_id"),
                    wp_url=img.get("wp_url"),
                )
                for img in data["uploaded_images"]
            ]

        return ctx
