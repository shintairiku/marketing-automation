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

# ポート開放 (FastAPIのデフォルトは8000)
EXPOSE 8000

# アプリケーションの起動コマンド
# Uvicornを使用してmain.py内のappオブジェクトを起動
# 開発時には --reload オプションを付けるとコード変更時に自動リロードされて便利です
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 