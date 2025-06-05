# -*- coding: utf-8 -*-
import os
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# .env ファイルを読み込む
load_dotenv()

class Settings(BaseSettings):
    """アプリケーション設定を管理するクラス"""
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    # 他のAPIキーが必要な場合は追加
    # anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    # gemini_api_key: Optional[str] = Field(None, env="GEMINI_API_KEY")

    # Supabase設定
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(..., env="SUPABASE_SERVICE_ROLE_KEY")

    # Clerk設定 (optional)
    clerk_secret_key: str = Field("", env="CLERK_SECRET_KEY")
    clerk_publishable_key: str = Field("", env="CLERK_PUBLISHABLE_KEY")

    # Stripe設定 (optional)
    stripe_secret_key: str = Field("", env="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field("", env="STRIPE_WEBHOOK_SECRET")

    # デフォルトモデル名 (環境変数またはデフォルト値)
    default_model: str = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
    research_model: str = os.getenv("RESEARCH_MODEL", "gpt-4o-mini")
    writing_model: str = os.getenv("WRITING_MODEL", "gpt-4o-mini")
    editing_model: str = os.getenv("EDITING_MODEL", "gpt-4o-mini")

    # デバッグフラグ
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # リトライ設定
    max_retries: int = 3
    initial_retry_delay: int = 1

    # OpenAI Agents SDKトレーシング設定
    enable_tracing: bool = os.getenv("OPENAI_AGENTS_ENABLE_TRACING", "true").lower() == "true"
    trace_include_sensitive_data: bool = os.getenv("OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA", "false").lower() == "true"

    class Config:
        # 環境変数ファイルからの読み込みを有効化
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore' # .envに余分な変数があっても無視する

# 設定インスタンスを作成
settings = Settings()

# openai-agents SDK設定の初期化
def setup_agents_sdk():
    """OpenAI Agents SDKのセットアップ"""
    try:
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

