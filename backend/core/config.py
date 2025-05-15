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

    # デフォルトモデル名 (環境変数またはデフォルト値)
    default_model: str = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
    research_model: str = os.getenv("RESEARCH_MODEL", "gpt-4o-mini")
    writing_model: str = os.getenv("WRITING_MODEL", "gpt-4o-mini")
    editing_model: str = os.getenv("EDITING_MODEL", "gpt-4o-mini")

    # リトライ設定
    max_retries: int = 3
    initial_retry_delay: int = 1

    class Config:
        # 環境変数ファイルからの読み込みを有効化
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore' # .envに余分な変数があっても無視する

# 設定インスタンスを作成
settings = Settings()

