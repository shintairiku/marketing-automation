# Pythonベースイメージ
FROM python:3.12-slim

# 環境変数
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 作業ディレクトリ
WORKDIR /app

# 依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# ポート開放 (Cloud Runでは動的に設定される)
EXPOSE 8000

# アプリケーションの起動コマンド
# Cloud RunではPORT環境変数が動的に設定されるため、それを使用
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"] 