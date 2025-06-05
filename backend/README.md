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

### OpenAI Agents SDKトレーシング設定

*   `OPENAI_AGENTS_ENABLE_TRACING`: (オプション、デフォルト: `true`) OpenAI Agents SDKのトレーシング機能の有効化。`true` でトレースを記録し、OpenAI プラットフォームで可視化可能。
*   `OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA`: (オプション、デフォルト: `false`) トレースに機密データ（LLM入出力、ツール実行結果など）を含めるかどうか。

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
*   `agents/`: 各処理ステップを実行するエージェントのモジュール群 (例: テーマ提案、リサーチ)
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

## トレーシング設定

本アプリケーションは OpenAI Agents SDK のトレーシング機能を統合しており、記事生成ワークフロー全体の詳細な追跡と監視が可能です。

### 環境変数

```bash
# トレーシングの有効化（デフォルト: true）
OPENAI_AGENTS_ENABLE_TRACING=true

# 機密データをトレースに含める（デフォルト: false）
# レスポンス詳細を表示したい場合は true に設定
OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA=true

# デバッグログの有効化（開発環境用）
DEBUG=true
```

### トレーシングの特徴

#### 最新のResponses API統合
- **OpenAI Agents SDK** はデフォルトでResponses APIを使用
- 従来のChat Completions APIと比較して、トレーシング機能が大幅に改善
- ステートフル（状態管理）なAPIによる会話履歴の自動管理

#### 単一トレースでの統合フロー
- 記事生成ワークフロー全体が単一のトレースとして記録
- 複数エージェント実行が適切に階層化されて表示
- 一意のトレースIDとグループIDによる識別

#### 詳細なスパン情報
以下の処理がカスタムスパンで詳細記録されます：

- **エージェント実行**: 各エージェントの実行時間、リトライ回数、入力データサイズ
- **リサーチクエリ実行**: クエリごとの実行状況と進捗
- **セクション執筆**: セクションごとの執筆進捗と出力サイズ

#### パフォーマンス監視
- 実行時間の詳細記録
- エラー発生箇所とリトライ状況の追跡
- リソース使用量の監視

#### エラーハンドリング
- トレーシング機能の失敗時も主要ワークフローの継続
- 安全なフォールバック処理
- 詳細なエラーログとメトリクス

### トレースデータの確認

1. **OpenAI Platform**: OpenAI プラットフォームのトレースダッシュボードで視覚的に確認
2. **ログ出力**: アプリケーションログでパフォーマンスメトリクスを確認
3. **WebSocket**: リアルタイムでの進捗状況をクライアントで監視

### "Could not fetch Response" エラーの解決方法

このエラーが発生する場合は、以下の手順で解決してください：

#### 1. 環境変数の設定確認
```bash
# 必須: トレーシングの有効化
export OPENAI_AGENTS_ENABLE_TRACING=true

# 重要: レスポンス詳細を表示するため
export OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA=true

# デバッグ情報を確認するため
export DEBUG=true
```

#### 2. APIキーの権限確認
- OpenAI Platform (https://platform.openai.com) でAPIキーが有効であることを確認
- トレーシング機能への access 権限があることを確認
- 正しいプロジェクト内でトレースを確認

#### 3. アプリケーションの再起動
環境変数を変更した後は必ずアプリケーションを再起動してください：
```bash
# 開発環境
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Docker環境
docker-compose down && docker-compose up --build
```

#### 4. ログの確認
アプリケーション起動時に以下のようなログが表示されることを確認：
```
OpenAI API キーを設定しました: sk-proj-...
OpenAI Agents SDK トレーシングAPIキーを設定しました
トレーシングで機密データを含めるように設定しました
OpenAI Agents SDK トレーシングが有効化されました
```

#### 5. ネットワーク設定の確認
- ファイアウォールやプロキシがトレースデータの送信を阻害していないか確認
- 企業ネットワークの場合、IT部門に相談

### よくあるエラーと対処法

| エラーメッセージ | 原因 | 対処法 |
|----------------|------|--------|
| `Could not fetch Response` | APIキーの権限不足 | `OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA=true`に設定 |
| `An error occurred while fetching log details` | 一時的なサーバーエラー | 数分待ってから再試行 |
| `403 Forbidden` | プロジェクトアクセス権限不足 | OpenAI Platformで正しいプロジェクトを選択 |
| `Traces not appearing` | トレーシング設定問題 | 環境変数とAPIキーを再確認 |

### トラブルシューティング手順

1. **設定確認**: 環境変数が正しく設定されているか確認
2. **再起動**: アプリケーションを完全に再起動
3. **ログ確認**: 起動時のトレーシング関連ログを確認
4. **APIキー確認**: OpenAI Platformでキーの権限を確認
5. **時間待機**: OpenAI Platform側の処理に時間がかかる場合があります（数分程度）
