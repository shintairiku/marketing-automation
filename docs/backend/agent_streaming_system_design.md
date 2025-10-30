# AIエージェント編集フロー ストリーミング対応システム設計

最終更新: 2025-10-29

本ドキュメントでは `/seo/generate/edit-article/[id]` の AI エージェント編集タブで動作するバックエンド〜フロントエンドの構成を整理し、特に OpenAI Agents SDK と Responses API を用いたストリーミング実行・イベント表示の仕組みを詳細に説明する。OpenAI の最新リファレンス（2025-10-29 時点）に基づき、実装で採用した考慮点と合わせてまとめる。[^1][^2][^3][^6]

## 全体像

```
ユーザー入力
   │
   ▼
Next.js (useAgentChat → API 呼び出し)
   │  POST /articles/{article_id}/agent/session/{session_id}/chat (FastAPI)
   ▼
FastAPI ルーター (backend/app/domains/seo_article/endpoints.py)
   │  AgentChatQueuedResponse(status="processing", run_state=...)
   ▼
ArticleAgentService / ArticleAgentSession
   │  OpenAI Agents SDK Runner.run_streamed(...)[^1]
   ▼
OpenAI Responses API (model=gpt-5-mini) + 定義済みツール
   │  → ResponseStreamEvent (text delta, tool call, reasoning summary 等)[^1][^2][^3]
   ▼
ArticleAgentSession._handle_*() で run_state に蓄積
   │  run_state.events[], status=running/completed/failed
   ▼
フロントエンドが GET /agent/session をポーリング → run_state 取得
   │
   ▼
AgentRunProgress コンポーネントで推論・ツール進行を可視化
```

## バックエンド

### エンドポイント構成

- `POST /articles/{article_id}/agent/session` : セッション作成 (`AgentSessionResponse`)
- `POST /articles/{article_id}/agent/session/{session_id}/activate` : 切り替え (`run_state` 同梱)
- `GET /articles/{article_id}/agent/session` : アクティブセッション詳細 (`AgentSessionDetailResponse`)
- `POST /articles/{article_id}/agent/session/{session_id}/chat` : チャット投入。即座に `202 Accepted` と `run_state` を返却し、非同期タスクでエージェント実行を継続。
- その他: `get_current_content` / `diff` / `extract-changes` など既存の編集 API 群。

レスポンスモデルには `AgentRunState` を追加済み。ポーリングレスポンスでは常に `run_state` を返し、エージェント未起動時は `status="idle"`・events 空配列となる。

```python
class AgentRunState(BaseModel):
    run_id: Optional[str]
    status: Literal["idle", "running", "completed", "failed"]
    started_at: Optional[str]
    completed_at: Optional[str]
    error: Optional[str]
    events: List[AgentStreamEvent]

class AgentStreamEvent(BaseModel):
    event_id: str
    sequence: int
    event_type: str
    message: str
    created_at: str
    updated_at: Optional[str]
    payload: Optional[Dict[str, Any]]
```

### ドメインサービス

`ArticleAgentSession` (backend/app/domains/seo_article/services/article_agent_wrapper.py)

1. `chat()` 呼び出し時に `_start_run()` で run_state を初期化し、`Runner.run_streamed` を実行。
2. ストリーミングイベントをハンドリング:
   - `RawResponsesStreamEvent`: Responses API の `response.output_text.delta`, `response.function_call_arguments.delta`, `response.web_search_call.searching` などを識別し `_handle_raw_stream_event` で run_state.events に書き込み。[^1][^4]
   - `RunItemStreamEvent`: Agents SDK の `tool_called`, `message_output_created`, `reasoning_item_created` を `_handle_run_item_stream_event` で整形。
   - `AgentUpdatedStreamEvent`: ハンドオフ時に記録。
3. 処理完了時 `_complete_run()` / 失敗時 `_fail_run()` で status, error を更新。

#### ツール実行ログのキー

|イベント種別|説明|payload 主要キー|ソース|
|--|--|--|--|
|`tool_called`|OpenAI 側の Function / Hosted tool 呼び出し開始|`tool_name`, `tool_type`, `arguments`|Agents SDK `RunItemStreamEvent`[^1]|
|`tool_output`|Function Tool コールの戻り|`output`|Agents SDK `RunItemStreamEvent`|
|`tool_web_search_*`|Hosted WebSearch 呼び出し段階 (`response.web_search_call.*`)|`item_id`, `output_index`|Responses API 新機能[^2]|
|`text_delta` / `text_delta_done`|アシスタントメッセージ生成差分|`delta`, `text`|Responses API streaming[^1]|
|`reasoning`|Reasoning summary の生成|`reasoning_id`, `summary`|Responses reasoning summary[^2]|
|`agent_updated`|ハンドオフ先エージェント名|—|Agents SDK Streaming[^1]|
|`tool_arguments_delta` / `tool_arguments_ready`|Function 引数の増分/確定|`item_id`, `delta`, `arguments`|OpenAI Responses API 型定義[^4]|

`ResponseFunctionCallArguments*` 系イベントは公式型定義上 `call_id` フィールドが存在するが、2025-10-29 時点の Python SDK 実行では `item_id` と `sequence_number` のみが提供されるケースを確認したため、実装では `item_id` ベースで追跡し不足分は payload にミラーしている（リグレッション防止用ログあり）。[^4]

### エージェント構成

- `agents.article_agent_service` が OpenAI Agents SDK の `build_text_edit_agent` と独自のツール (`read_file`, `apply_patch`, `web_search`) を組み合わせる。
- モデルは `settings.article_edit_agent_model` (例: `gpt-5-mini`) を指定。GPT‑5 系列では Responses API の `reasoning_effort`・`verbosity` トグルや高信頼ツール連携が強化されているため、記事編集ワークフローでの長時間推論と逐次報告を両立できる。[^6]
- `Runner.run_streamed` により stream events を逐次受信し、`session.session_store` (SQLite) に会話履歴を保持。

#### モデルと推論パラメータ

- **reasoning_effort**: GPT‑5 mini は `minimal` 〜 `high` をサポートする。Responses API では `minimal` が短時間レスポンス用に最適化されているため、編集 Diff 提案を高速化したい場合は設定値を `minimal` に落とし、難易度が高い修正では `medium` 以上を選ぶ運用が可能。[^6]
- **verbosity**: モデルが返すメッセージ密度を制御。`low` を設定すると、Assistant メッセージとストリームイベントの両方がコンパクトになり、AgentRunProgress の情報量を制御しやすい。[^6]
- **背景モード**: Responses API の background 送信（`response.background=true`）と組み合わせれば、20 分のポーリングタイムアウト前にエラーを即座に検知する仕組みをバックエンドから利用できる。現状は前景実行だが、背景モード移行時も `run_state.status` を `running` → `completed/failed` に更新するだけで UI はそのまま利用できる。[^2]

## フロントエンド

### フロー概要

1. `useAgentChat.sendMessage()` が POST を送り即時レスポンスの `run_state` を受け取り、`setRunState()`。
2. `pollForAssistantResponse()` が `GET /agent/session` をポーリングし、`run_state` を逐次更新 (失敗ステータスなら即エラー表示)。背景モードと同様に長時間タスクも検知できる。[^2]
3. メッセージ配列更新後、`AgentRunProgress` コンポーネントが最新の run_state を描画。

### useAgentChat 主な state

|state|役割|
|--|--|
|`messages`|チャットバブル表示用履歴|
|`runState`|`AgentRunState` を正規化したオブジェクト|
|`sessions`|セッション一覧セレクタ用|
|`loading` / `error`|UI フィードバック|

`normalizeRunState()` ではバックエンド JSON を型安全な構造に変換し、`event.sequence` でソート。

### AgentRunProgress コンポーネント

- 直近 6 件のイベントをタイムライン表示 (アイコン + 説明 + 時刻)。`response.reasoning_text.delta` 等の追加イベントが登場した場合も `event_type` で判別可能。[^5]
- 状態別メッセージ:
  - running: 最新イベントの説明をリアルタイム表示。
  - completed: 「処理が完了しました」。
  - failed: `runState.error` を赤箱で表示。
- 旧来の固定文「AIが考え中です…」を置き換え、推論過程・ツール呼び出しを可視化。

## データモデル整合性チェック

|ソース|キー|備考|
|--|--|--|
|FastAPI レスポンス|`run_state`|常に付与 (未実行なら `status='idle'`) |
|Supabase|`article_agent_sessions`|`last_activity_at` は run_state 更新時に上書き|
|Front|`AgentRunState.events[].payload`|任意フィールド。UI 側で null チェック必須|

## エラーハンドリング

- Streaming 中に例外が発生した場合 `_fail_run()` が `status='failed'` とエラーメッセージを格納。
- フロントエンドはポーリング時に `status==='failed'` を検知すると `throw` してチャット UI にエラーを表示。以降 runState.error が維持されるため、再実行時は `startNewSession()` を推奨。

## 運用メモ

- Responses API の schema 変更に追随するため、`openai` SDK 更新時は `Response*Event` クラス定義を確認し、`_handle_raw_stream_event` のキー参照 (`item_id`, `sequence_number` 等) を再検証する。
- フロント側ポーリング間隔 (`NEXT_PUBLIC_AGENT_POLL_INTERVAL_MS`) は既定 1500ms。Responses API の背景モードを活用する場合は 3〜5 秒でも UX が成立するか要検討。[^2]
- `run_state.events` はセッションごとに揮発的に保持しているため、永続的な監査ログが必要な場合は Supabase 側に複製すること。
- Responses API の reasoning summary / encrypted reasoning item を採用する場合は、`run_state` の payload にサマリや encrypted blob を追加し、ユーザーに公開してよい情報かを UI で制御する。[^2][^5]

---

[^1]: OpenAI Agents SDK Streaming ガイド（Python） https://openai.github.io/openai-agents-python/streaming/
[^2]: 「New tools and features in the Responses API」（2025-05-21） https://openai.com/index/new-tools-and-features-in-the-responses-api/
[^3]: 「Why we built the Responses API」 https://developers.openai.com/blog/responses-api
[^4]: `ResponseFunctionCallArgumentsDeltaEvent` 型定義（openai-go v2） https://pkg.go.dev/github.com/openai/openai-go/v2/responses
[^5]: OpenAI Cookbook: Handling raw chain-of-thought / reasoning events https://cookbook.openai.com/articles/gpt-oss/handle-raw-cot
[^6]: 「Introducing GPT‑5 for developers」（2025-08-07） https://openai.com/index/introducing-gpt-5-for-developers
