# -*- coding: utf-8 -*-
import os
from pathlib import Path
import tempfile
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv

# シンプルに.envファイルを読み込み
backend_dir = Path(__file__).parent.parent.parent
env_path = backend_dir / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)

class Settings(BaseSettings):
    """アプリケーション設定を管理するクラス"""
    # --- AI API Keys ---
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    serpapi_key: str = Field(default_factory=lambda: os.getenv("SERPAPI_API_KEY", ""))
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))

    # --- Database ---
    supabase_url: str = Field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_service_role_key: str = Field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))

    # --- Authentication ---
    clerk_secret_key: str = Field(default_factory=lambda: os.getenv("CLERK_SECRET_KEY", ""))
    clerk_publishable_key: str = Field(default_factory=lambda: os.getenv("CLERK_PUBLISHABLE_KEY", ""))
    # JWKS URL 自動導出が失敗する場合のフォールバック
    clerk_frontend_api: str = Field(default_factory=lambda: os.getenv("CLERK_FRONTEND_API", ""))

    # --- CORS ---
    allowed_origins: str = Field(default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "http://localhost:3000"))

    # --- AI Model Settings ---
    research_model: str = os.getenv("RESEARCH_MODEL", "gpt-5-mini")
    writing_model: str = os.getenv("WRITING_MODEL", "gpt-4o-mini")
    outline_model: str = os.getenv("OUTLINE_MODEL") or writing_model  # 未指定時は執筆モデルを利用
    editing_model: str = os.getenv("EDITING_MODEL", "gpt-4o-mini")
    serp_analysis_model: str = os.getenv("SERP_ANALYSIS_MODEL") or research_model
    persona_model: str = os.getenv("PERSONA_MODEL") or writing_model
    theme_model: str = os.getenv("THEME_MODEL") or writing_model

    # Article editing agents
    article_edit_agent_model: str = os.getenv("ARTICLE_EDIT_AGENT_MODEL", "gpt-5-mini")
    article_edit_agent_reasoning_summary: str = os.getenv("ARTICLE_EDIT_AGENT_REASONING_SUMMARY", "detailed")
    article_edit_service_model: str = os.getenv("ARTICLE_EDIT_SERVICE_MODEL", "gpt-4o")

    # AI Content Generation settings (using Responses API)
    ai_content_generation_model: str = os.getenv("AI_CONTENT_GENERATION_MODEL", "gpt-5-mini")
    ai_content_generation_reasoning_effort: str = os.getenv("AI_CONTENT_GENERATION_REASONING_EFFORT", "low")
    ai_content_enable_web_search: bool = os.getenv("AI_CONTENT_ENABLE_WEB_SEARCH", "true").lower() == "true"

    # Reasoning summary translation
    reasoning_translate_model: str = os.getenv("REASONING_TRANSLATE_MODEL", "gpt-5-nano")

    # Scraping settings
    max_concurrent_scraping: int = int(os.getenv("MAX_CONCURRENT_SCRAPING", "5"))

    # デバッグフラグ
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Google Cloud設定 (画像生成用)
    google_cloud_project: str = Field(default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT", ""))
    google_cloud_location: str = Field(default_factory=lambda: os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
    google_service_account_json: str = Field(default_factory=lambda: os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", ""))
    google_service_account_json_file: str = Field(default_factory=lambda: os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_FILE", ""))
    
    # 画像生成モデル設定
    imagen_model_name: str = Field(default_factory=lambda: os.getenv("IMAGEN_MODEL_NAME", "imagen-4.0-generate-preview-06-06"))
    imagen_aspect_ratio: str = Field(default_factory=lambda: os.getenv("IMAGEN_ASPECT_RATIO", "4:3"))
    imagen_output_format: str = Field(default_factory=lambda: os.getenv("IMAGEN_OUTPUT_FORMAT", "JPEG"))
    imagen_quality: int = Field(default_factory=lambda: int(os.getenv("IMAGEN_QUALITY", "85")))
    imagen_safety_filter: str = Field(default_factory=lambda: os.getenv("IMAGEN_SAFETY_FILTER", "block_only_high"))
    imagen_person_generation: str = Field(default_factory=lambda: os.getenv("IMAGEN_PERSON_GENERATION", "allow_all"))
    imagen_add_japan_prefix: bool = Field(default_factory=lambda: os.getenv("IMAGEN_ADD_JAPAN_PREFIX", "true").lower() == "true")
    
    # 画像ストレージ設定（Cloud Run対応）
    image_storage_path: str = Field(default_factory=lambda: os.getenv("IMAGE_STORAGE_PATH", "/tmp/images"))
    
    # Google Cloud Storage設定
    gcs_bucket_name: str = Field(default_factory=lambda: os.getenv("GCS_BUCKET_NAME", ""))
    gcs_public_url_base: str = Field(default_factory=lambda: os.getenv("GCS_PUBLIC_URL_BASE", ""))

    # リトライ設定
    max_retries: int = 3
    initial_retry_delay: int = 1

    # OpenAI Agents SDKトレーシング設定
    enable_tracing: bool = os.getenv("OPENAI_AGENTS_ENABLE_TRACING", "true").lower() == "true"
    trace_include_sensitive_data: bool = os.getenv("OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA", "false").lower() == "true"

    # Agent session persistence settings
    agent_session_storage_dir: str = Field(
        default_factory=lambda: os.getenv(
            "AGENT_SESSION_STORAGE_DIR",
            str(Path(tempfile.gettempdir()) / "openai-agent-sessions")
        )
    )

    # Blog AI設定
    blog_generation_model: str = Field(default_factory=lambda: os.getenv("BLOG_GENERATION_MODEL", "gpt-5.2"))
    blog_generation_reasoning_effort: str = Field(default_factory=lambda: os.getenv("BLOG_GENERATION_REASONING_EFFORT", "medium"))
    blog_generation_reasoning_summary: str = Field(default_factory=lambda: os.getenv("BLOG_GENERATION_REASONING_SUMMARY", "detailed"))
    blog_generation_max_turns: int = Field(default_factory=lambda: int(os.getenv("BLOG_GENERATION_MAX_TURNS", "100")))
    blog_generation_parallel_tool_calls: bool = Field(default_factory=lambda: os.getenv("BLOG_GENERATION_PARALLEL_TOOL_CALLS", "true").lower() == "true")
    blog_prompt_cache_enabled: bool = Field(default_factory=lambda: os.getenv("BLOG_PROMPT_CACHE_ENABLED", "true").lower() == "true")
    blog_prompt_cache_scope: str = Field(default_factory=lambda: os.getenv("BLOG_PROMPT_CACHE_SCOPE", "global"))
    blog_prompt_cache_key_version: str = Field(default_factory=lambda: os.getenv("BLOG_PROMPT_CACHE_KEY_VERSION", "v1"))
    blog_prompt_cache_retention_24h: bool = Field(default_factory=lambda: os.getenv("BLOG_PROMPT_CACHE_RETENTION_24H", "true").lower() == "true")
    credential_encryption_key: str = Field(default_factory=lambda: os.getenv("CREDENTIAL_ENCRYPTION_KEY", ""))

    # SMTP / Contact notification settings
    smtp_host: str = Field(default_factory=lambda: os.getenv("SMTP_HOST", ""))
    smtp_port: int = Field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_user: str = Field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_password: str = Field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    smtp_from_email: str = Field(default_factory=lambda: os.getenv("SMTP_FROM_EMAIL", ""))
    contact_notification_email: str = Field(default_factory=lambda: os.getenv("CONTACT_NOTIFICATION_EMAIL", ""))

    # Resend (preferred over SMTP)
    resend_api_key: str = Field(default_factory=lambda: os.getenv("RESEND_API_KEY", ""))
    resend_from_email: str = Field(default_factory=lambda: os.getenv("RESEND_FROM_EMAIL", "BlogAI <noreply@yourdomain.com>"))

    model_config = SettingsConfigDict(
        env_file=[
            '.env',
            Path(__file__).parent.parent.parent / '.env',
        ],
        env_file_encoding='utf-8',
        env_ignore_empty=False,  # 空の環境変数も読み込む
        extra='allow',  # 余分な環境変数を許可
        case_sensitive=False
    )

# 設定インスタンスを作成
settings = Settings()

# openai-agents SDK設定の初期化
def setup_agents_sdk():
    """OpenAI Agents SDKのセットアップ"""
    try:
        # API キーが設定されていない場合はスキップ
        if not settings.openai_api_key:
            print("OpenAI API キーが設定されていません。SDK設定をスキップします。")
            return

        from agents import (
            set_default_openai_key, 
            set_tracing_disabled,
            set_tracing_export_api_key,
            enable_verbose_stdout_logging
        )
        
        # OpenAI APIキーを設定
        set_default_openai_key(settings.openai_api_key)
        print(f"OpenAI API キーを設定しました: {settings.openai_api_key[:8]}...")
        
        # トレーシング設定
        if settings.enable_tracing:
            # トレーシング用のAPIキーを設定（同じキーを使用）
            set_tracing_export_api_key(settings.openai_api_key)
            print("OpenAI Agents SDK トレーシングAPIキーを設定しました")
            
            # 機密データログ設定を環境変数で制御
            if settings.trace_include_sensitive_data:
                # 機密データを含める場合は環境変数をクリア
                os.environ.pop("OPENAI_AGENTS_DONT_LOG_MODEL_DATA", None)
                os.environ.pop("OPENAI_AGENTS_DONT_LOG_TOOL_DATA", None)
                print("トレーシングで機密データを含めるように設定しました")
            else:
                # 機密データを除外する場合は環境変数を設定
                os.environ["OPENAI_AGENTS_DONT_LOG_MODEL_DATA"] = "1"
                os.environ["OPENAI_AGENTS_DONT_LOG_TOOL_DATA"] = "1"
                print("トレーシングで機密データを除外するように設定しました")
            
            print("OpenAI Agents SDK トレーシングが有効化されました")
        else:
            # トレーシングを無効化
            set_tracing_disabled(True)
            print("OpenAI Agents SDK トレーシングが無効化されました")
        
        # 詳細ログを有効化（デバッグ時のみ）
        if settings.debug:
            enable_verbose_stdout_logging()
            print("OpenAI Agents SDK デバッグログが有効化されました")
            
    except ImportError as e:
        print(f"OpenAI Agents SDKのインポートに失敗しました: {e}")
        print("pip install openai-agents を実行してください")
    except Exception as e:
        print(f"OpenAI Agents SDKのセットアップに失敗しました: {e}")
        # エラーがあってもアプリケーションの起動は継続

# 初期化実行
setup_agents_sdk()
