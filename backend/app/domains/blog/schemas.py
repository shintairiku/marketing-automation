# -*- coding: utf-8 -*-
"""
Blog AI Domain - Pydantic Schemas

ブログAI機能のリクエスト/レスポンススキーマ定義
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


# =====================================================
# WordPress連携関連
# =====================================================

class WordPressSiteBase(BaseModel):
    """WordPressサイト基本情報"""
    site_url: str = Field(..., description="WordPressサイトURL")
    site_name: Optional[str] = Field(None, description="サイト名")


class WordPressSiteCreate(WordPressSiteBase):
    """WordPressサイト作成リクエスト（内部使用）"""
    mcp_endpoint: str
    access_token: str
    api_key: str
    api_secret: str


class WordPressSiteResponse(WordPressSiteBase):
    """WordPressサイトレスポンス"""
    id: str
    mcp_endpoint: str
    connection_status: Literal["connected", "disconnected", "error"]
    is_active: bool
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    last_connected_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WordPressConnectionTestStep(BaseModel):
    """接続テストの個別ステップ結果"""
    name: str = Field(..., description="ステップ名")
    label: str = Field(..., description="表示用ラベル")
    status: Literal["success", "error", "skipped"] = Field(..., description="ステップの結果")
    message: str = Field(..., description="結果メッセージ")
    detail: Optional[str] = Field(None, description="詳細情報（デバッグ用）")
    duration_ms: Optional[int] = Field(None, description="実行時間（ミリ秒）")


class WordPressConnectionTestResult(BaseModel):
    """WordPress接続テスト結果"""
    success: bool
    message: str
    server_info: Optional[Dict[str, Any]] = None
    steps: List[WordPressConnectionTestStep] = Field(default_factory=list, description="個別テストステップ結果")


# =====================================================
# ブログ生成関連
# =====================================================

class BlogGenerationStartRequest(BaseModel):
    """ブログ生成開始リクエスト"""
    user_prompt: str = Field(
        ...,
        max_length=2000,
        description="どんな記事を作りたいか"
    )
    reference_url: Optional[str] = Field(
        None,
        description="参考記事のURL（WordPressサイト内の記事）"
    )
    wordpress_site_id: str = Field(
        ...,
        description="接続済みWordPressサイトID"
    )


class BlogGenerationUserInput(BaseModel):
    """ブログ生成ユーザー入力"""
    input_type: Literal["additional_info", "approve_draft", "upload_image"]
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="入力データ"
    )


class UploadedImageInfo(BaseModel):
    """アップロード画像情報"""
    filename: str
    local_path: Optional[str] = None
    wp_media_id: Optional[int] = None
    wp_url: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class BlogGenerationStep(BaseModel):
    """ブログ生成ステップ"""
    name: str
    status: Literal["pending", "in_progress", "completed", "error"]
    message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class BlogGenerationStateResponse(BaseModel):
    """ブログ生成状態レスポンス"""
    id: str
    user_id: str
    wordpress_site_id: Optional[str] = None
    status: Literal["pending", "in_progress", "completed", "error", "user_input_required", "cancelled"]
    current_step_name: Optional[str] = None
    progress_percentage: int = 0

    # ユーザー入力待ち
    is_waiting_for_input: bool = False
    input_type: Optional[str] = None

    # コンテキストデータ
    blog_context: Dict[str, Any] = Field(default_factory=dict)

    # 入力データ
    user_prompt: Optional[str] = None
    reference_url: Optional[str] = None

    # 画像
    uploaded_images: List[UploadedImageInfo] = Field(default_factory=list)

    # 結果
    draft_post_id: Optional[int] = None
    draft_preview_url: Optional[str] = None
    draft_edit_url: Optional[str] = None
    error_message: Optional[str] = None

    # タイムスタンプ
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BlogGenerationHistoryItem(BaseModel):
    """ブログ生成履歴アイテム（軽量版 - 一覧表示用）"""
    id: str
    status: Literal["pending", "in_progress", "completed", "error", "user_input_required", "cancelled"]
    current_step_name: Optional[str] = None
    progress_percentage: int = 0
    user_prompt: Optional[str] = None
    reference_url: Optional[str] = None
    draft_post_id: Optional[int] = None
    draft_preview_url: Optional[str] = None
    draft_edit_url: Optional[str] = None
    error_message: Optional[str] = None
    wordpress_site_name: Optional[str] = None
    image_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BlogCompletionOutput(BaseModel):
    """Blog AI エージェントの構造化最終出力

    エージェントが wp_create_draft_post の結果から抽出した情報と、
    ユーザーへのまとめメッセージを構造化して返す。
    """
    post_id: Optional[int] = Field(None, description="WordPress下書きの投稿ID")
    preview_url: Optional[str] = Field(None, description="下書きプレビューURL")
    edit_url: Optional[str] = Field(None, description="WordPress管理画面の編集URL")
    summary: str = Field(..., description="ユーザーへの完了メッセージ（日本語）。記事の概要・ポイント等を含む")


class BlogDraftResult(BaseModel):
    """ブログ下書き作成結果"""
    success: bool
    post_id: Optional[int] = None
    preview_url: Optional[str] = None
    edit_url: Optional[str] = None
    error_message: Optional[str] = None


# =====================================================
# MCP関連
# =====================================================

class MCPToolCallResult(BaseModel):
    """MCPツール呼び出し結果"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class WordPressArticleAnalysis(BaseModel):
    """WordPress記事分析結果"""
    title: str
    content_structure: Dict[str, Any]
    tone: str
    vocabulary: List[str]
    block_patterns: List[Dict[str, Any]]
    custom_css: Optional[str] = None


class WordPressMediaUploadResult(BaseModel):
    """WordPressメディアアップロード結果"""
    media_id: int
    url: str
    alt: Optional[str] = None


# =====================================================
# イベント関連
# =====================================================

class BlogProcessEvent(BaseModel):
    """ブログ生成プロセスイベント"""
    id: str
    process_id: str
    event_type: str
    event_data: Dict[str, Any] = Field(default_factory=dict)
    event_sequence: int
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# AI質問関連
# =====================================================

class AIQuestion(BaseModel):
    """AIからの質問"""
    question_id: str
    question: str
    context: Optional[str] = None
    input_type: Literal["text", "textarea", "image_upload", "select"]
    options: Optional[List[str]] = None  # selectの場合
    required: bool = True


class AIQuestionsRequest(BaseModel):
    """AIからの質問リクエスト"""
    questions: List[AIQuestion]
    explanation: str = Field(..., description="なぜこの情報が必要かの説明")


class UserAnswers(BaseModel):
    """ユーザーの回答"""
    answers: Dict[str, Any] = Field(
        ...,
        description="質問IDをキーとした回答"
    )
