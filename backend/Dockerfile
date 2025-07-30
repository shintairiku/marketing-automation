# Pythonベースイメージ
FROM python:3.12-slim

# 環境変数
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

# 作業ディレクトリ
WORKDIR /app

# uvをインストール
RUN pip install uv

# 依存関係をインストール
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

# アプリケーションコードをコピー
COPY . .

# ポート開放 (Cloud Runでは動的に設定される)
EXPOSE 8000

# アプリケーションの起動コマンド
# Cloud RunではPORT環境変数が動的に設定されるため、それを使用
CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"] 