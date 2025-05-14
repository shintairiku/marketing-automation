# Backend API (SEO Article Generation)

このディレクトリには、SEO記事をインタラクティブに生成するためのバックエンドAPIが含まれています。FastAPIフレームワークとOpenAI APIを利用して構築されています。

## 概要

このバックエンドAPIは、WebSocket通信を通じてクライアントと連携し、以下のステップでSEO記事を生成します。

1.  **初期リクエスト**: クライアントは記事のキーワード、ターゲットペルソナ、目標文字数などの初期パラメータを送信します。
2.  **テーマ提案**: APIは複数の記事テーマを提案し、クライアントに選択を促します。
3.  **リサーチ計画**: 選択されたテーマに基づいて、APIはリサーチ計画を作成し、クライアントに承認を求めます。
4.  **リサーチ実行と統合**: 承認された計画に従い、関連情報を収集・統合します。
5.  **アウトライン作成**: 統合された情報に基づいて記事のアウトラインを作成し、クライアントに承認を求めます。
6.  **記事執筆**: 承認されたアウトラインに従い、各セクションの記事本文を執筆します。
7.  **編集**: 生成された記事全体を編集し、最終的な成果物をクライアントに提供します。

進捗状況やユーザーの入力が必要なタイミングで、WebSocketを通じてクライアントに通知が送られます。

## 技術スタック

*   **フレームワーク**: FastAPI
*   **言語**: Python 3.12
*   **主要ライブラリ**:
    *   `uvicorn`: ASGIサーバー
    *   `openai`: OpenAI API連携
    *   `openai-agents`: エージェントベースの処理フロー管理 (カスタム実装の可能性あり)
    *   `python-dotenv`: 環境変数管理
    *   `pydantic-settings`: 設定管理
    *   `rich`: (開発時の)リッチなコンソール出力
*   **API**: WebSocket, REST (一部)

## APIエンドポイント

### WebSocket

*   `ws:///articles/ws/generate`:
    *   記事生成プロセス全体をインタラクティブに処理します。
    *   クライアントはJSON形式でリクエストとレスポンスを送受信します。
    *   詳細なメッセージスキーマは `schemas/request.py` および `schemas/response.py` を参照してください。

### HTTP

*   `GET /`: APIのルートエンドポイント。動作確認用。
*   `GET /test-client`: WebSocket接続をテストするための簡単なHTMLクライアントページを提供します。

## 設定

アプリケーションの設定は、`.env` ファイルを通じて環境変数から読み込まれます。主要な設定項目は以下の通りです。

*   `OPENAI_API_KEY`: (必須) OpenAI APIのキー。
*   `DEFAULT_MODEL`: デフォルトで使用するGPTモデル名 (例: `gpt-4o-mini`)。
*   `RESEARCH_MODEL`: リサーチ用に使用するGPTモデル名。
*   `WRITING_MODEL`: 執筆用に使用するGPTモデル名。
*   `EDITING_MODEL`: 編集用に使用するGPTモデル名。
*   `MAX_RETRIES`: APIリクエストの最大リトライ回数。
*   `INITIAL_RETRY_DELAY`: APIリクエストの初期リトライ遅延秒数。

プロジェクトルートに `.env` ファイルを作成し、必要な値を設定してください。`.env.example` のようなテンプレートファイルがあれば、それをコピーして使用することを推奨します。

## 実行方法

### 開発環境

1.  **依存関係のインストール**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **(推奨) `.env` ファイルの作成**: プロジェクトのルート (この `backend` ディレクトリ) に `.env` ファイルを作成し、`OPENAI_API_KEY` などの必要な環境変数を設定します。
3.  **APIサーバーの起動**:
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```
    `--reload` オプションにより、コード変更時にサーバーが自動的にリロードされます。

### Docker

1.  **(推奨) `.env` ファイルの作成**: `backend` ディレクトリに `.env` ファイルを作成します (Dockerビルドコンテキストに含める場合)。あるいは、Docker実行時に環境変数を渡すことも可能です。
2.  **Dockerイメージのビルド**: `backend` ディレクトリで以下のコマンドを実行します。
    ```bash
    docker build -t seo-article-backend .
    ```
3.  **Dockerコンテナの実行**:
    ```bash
    docker run -p 8000:8000 --env-file .env seo-article-backend
    ```
    または、個別の環境変数を指定する場合:
    ```bash
    docker run -p 8000:8000 -e OPENAI_API_KEY="your_api_key" seo-article-backend
    ```

アクセスは `http://localhost:8000` から可能です。テストクライアントは `http://localhost:8000/test-client` で利用できます。

## ディレクトリ構成の概要

*   `api/`: APIエンドポイントの定義
    *   `endpoints/`: 各リソースのエンドポイント (例: `article.py`)
*   `core/`: アプリケーションのコア設定と例外処理
    *   `config.py`: 環境変数や設定値の管理
    *   `exceptions.py`: カスタム例外とハンドラ
*   `schemas/`: リクエスト/レスポンスのデータモデル (Pydanticモデル)
    *   `request.py`: リクエストボディのスキーマ
    *   `response.py`: レスポンスボディやWebSocketメッセージのスキーマ
*   `services/`: ビジネスロジック層
    *   `article_service.py`: 記事生成の中核となるサービス
    *   `agents.py`: 各処理ステップを実行するエージェントの定義 (例: テーマ提案、リサーチ)
    *   `context.py`: 記事生成プロセスの状態を管理するコンテキスト
    *   `models.py`: サービス内部で使用するデータ構造
*   `utils/`: 汎用的なユーティリティ関数
*   `main.py`: FastAPIアプリケーションのインスタンス化と起動ポイント
*   `Dockerfile`: Dockerイメージ作成のための定義ファイル
*   `requirements.txt`: Pythonの依存ライブラリリスト
*   `pyproject.toml`: プロジェクトメタデータと依存関係 (Poetryなどを使用する場合)
*   `test_client.html`: WebSocketテスト用のHTMLクライアント

## 今後の改善点 (TODO例)

*   認証・認可機能の追加
*   より詳細なロギングとモニタリング
*   単体テスト・結合テストの拡充
*   データベース連携 (生成記事の保存など)
*   対応LLMモデルの拡充 (Anthropic, Geminiなど)
*   エラーハンドリングの強化とリカバリ戦略の改善
