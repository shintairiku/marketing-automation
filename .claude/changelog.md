# 変更履歴 (直近)

> 新しい変更はこのファイルに追記する。古い項目は @.claude/changelog-archive.md を参照。

### 41. Blog AIトレースの精査・動的詳細ページ化・delta保存抑制 (2026-02-21)

**概要**: 管理者向け Blog Usage トレースを「モーダル閲覧」だけでなく **動的ルートページ** でも確認できるように拡張。あわせて実DBを直接検証し、`blog_agent_trace_events` が初期実装では delta 系イベントを大量保存していたことを確認し、今後の新規実行では保存しないよう修正。

**フロントエンド変更**:
- `frontend/src/app/(admin)/admin/blog-usage/[processId]/page.tsx` を新規追加
  - `GET /admin/usage/blog/{process_id}/trace` を取得し、以下を一画面表示:
    - 会話履歴
    - レスポンス別トークン（LLM call）
    - ツール呼び出し入出力
    - 時系列イベント
- `frontend/src/app/(admin)/admin/blog-usage/page.tsx`
  - 各行に `ページ` ボタンを追加（`/admin/blog-usage/{process_id}` へ遷移）
  - 従来の `詳細` モーダル導線も維持

**バックエンド変更**:
- `backend/app/domains/blog/services/generation_service.py`
  - `_build_raw_trace_event` で `keepalive` と `*.delta` を保存対象外に変更
    - 初期実装で行数が爆発していたため、`done/completed` 系中心に圧縮
  - 同関数内の delta 分岐処理を削除し、`done/completed` のみを明示的に処理する形へ整理
  - `ToolCallOutputItem` の `call_id` 解決を改善
    - `call_id` が無い場合は `id` をフォールバック利用
    - `tool_output` と `tool_call_logs` の紐付け精度を改善
- `backend/app/domains/admin/service.py`
  - `blog_agent_trace_events` 読み出しを `.range()` のページングループ化（1000件上限を突破して全件取得）

**検証スクリプト追加**:
- `backend/testing/verify_blog_trace_logs.py`
  - 対象 process の `blog_generation_state / agent_log_sessions / agent_execution_logs / llm_call_logs / tool_call_logs / blog_agent_trace_events` を横断検証
  - 実装チェック:
    - execution token合計と llm token合計の一致
    - `llm_call_logs.api_response_id` と `response.completed.response_id` の一致
    - `tool_called` 件数と `tool_call_logs` 件数の一致
- `backend/testing/cleanup_blog_trace_delta_events.py`
  - 既存の noisy trace（`*.delta` / `keepalive`）を対象に dry-run で件数確認
  - `--apply` 指定時のみ batch delete を実行（デフォルトは削除しない）

**実DB確認結果（既存セッション）**:
- 対象: `process_id=80f5c267-f740-405f-a66e-123f2840d89e`
- `trace_event_count=2898`
- 大量イベントの内訳:
  - `response.reasoning_summary_text.delta=1436`
  - `response.function_call_arguments.delta=1088`
  - `response.output_text.delta=106`
  - `keepalive=1`
- cleanup dry-run 結果:
  - `total_rows=2898`
  - `noisy_rows=2631`
- ローカルSupabaseで cleanup apply を2回実行:
  - 1回目 `deleted_rows=2631`
  - 2回目 `deleted_rows=1`（実行中に新規追加された残件を除去）
- cleanup 後の再検証:
  - `trace_event_count=267`
  - `trace_event_type_counts` から `*.delta` / `keepalive` は消滅
- これは **修正前に保存された履歴**。検証スクリプトの整合性チェック自体は `VERDICT: OK`。

**関数レベル確認（修正後挙動）**:
- `_build_raw_trace_event({'type':'response.output_text.delta', ...}) -> (None, None)`
- `_build_raw_trace_event({'type':'keepalive'}) -> (None, None)`
- `response.output_text.done` は通常通り保存
- つまり、新規実行分では delta/keepalive の行増殖は発生しない。

### 42. Blog AIトレース精度の根本修正（会話履歴欠落・unknown多発・ツールI/O不整合）(2026-02-21)

**背景（ユーザー指摘）**:
- 会話履歴が「質問回答後」からしか表示されない
- `unknown` / 空欄が多く、ツール入力・出力が不正確
- UIで全文を確認できない

**公式仕様の確認（OpenAI）**:
- Agents SDK streaming: `RunItemStreamEvent` / `RawResponsesStreamEvent` の構造を再確認
  - https://openai.github.io/openai-agents-python/streaming/
  - https://openai.github.io/openai-agents-python/ref/stream_events/
- `RunResult.to_input_list()` は「元入力 + 今回runで生成された新規アイテム」の形で返るため、`previous_response_id`運用時は保存済み履歴の明示マージが必要
  - https://openai.github.io/openai-agents-python/results/
- Responses API event（`response.output_item.done`, `response.web_search_call.completed` など）の扱いを確認
  - https://platform.openai.com/docs/api-reference/responses-streaming

**根本原因**:
1. `continue_generation` で `previous_response_id` 経由再開時、`to_input_list()` の結果をそのまま上書き保存していたため、初回ターンが欠落
2. `ToolCallOutputItem.raw_item` が `dict` のケースで `getattr` 参照しており、`call_id` / `tool_name` を取得できず欠損
3. `tool_output` の補完を `tool_called` 順に行うと、`web_search` のように `ToolCallOutputItem` を返さないケースでズレる
4. 詳細画面が省略表示のみで、全文確認ができなかった

**バックエンド修正**:
- `backend/app/domains/blog/services/generation_service.py`
  - `ToolCallOutputItem` の `call_id` 取得を `self._safe_get(..., "call_id"/"id")` に変更（dict/obj両対応）
  - `response.output_item.done`（`item_type=function_call`）を基準に `pending_output_call_ids` を構築し、`tool_output` を高精度に紐付け
  - `response.web_search_call.completed` を検出して `tool_call_logs` を `completed` 更新（web_search系の取りこぼし防止）
  - 会話履歴マージヘルパー `_merge_conversation_histories()` を追加し、継続実行時に既存履歴と新履歴を重複なく結合
  - `agent_log_sessions` ステータスを完了/失敗で更新
  - `response.web_search_call.*` を traceイベントとして `tool_call_id`/`tool_name` 付きで保存

- `backend/app/domains/admin/service.py`
  - trace取得後に `_enrich_trace_rows()` で `tool_output` 欠損情報を補完
  - `_enrich_tool_call_rows()` で `tool_call_logs` を trace情報から補正（status/output/execution_time）
  - `conversation_history` が不足時、`initial_input.user_prompt` を先頭に補完する `_compose_conversation_history()` を追加

**DB補正スクリプト追加**:
- `backend/testing/backfill_blog_tool_logs_from_trace.py`
  - legacyデータ向けに `blog_agent_trace_events` / `tool_call_logs` を backfill
  - `--apply` 指定時のみ実更新

**UI修正（全文閲覧）**:
- `frontend/src/app/(admin)/admin/blog-usage/[processId]/page.tsx`
  - 会話履歴、LLM call、ツール入力/出力、時系列イベントの各行に `全文` ボタン追加
  - ダイアログでフルテキスト/フルJSON表示を実装
  - `tool_name/model_name/tool_call_id` のフォールバック表示を改善

**ローカルDB再検証（process_id=80f5c267-f740-405f-a66e-123f2840d89e）**:
- `verify_blog_trace_logs.py` 最終結果: `VERDICT: OK`
- `tool_output_missing_call_id=0`
- `tool_output_missing_tool_name=0`
- `tool_call_logs status`: `completed=28`
- `session.status`: `completed`
- `AdminService.get_blog_usage_trace()` 返却:
  - `conversation_history` 先頭に初回ユーザープロンプトを補完
  - `unknown` ツール名は 0

### 43. 継続生成時のストリーミング断（incomplete chunked read）自動リトライ対応 (2026-02-21)

**背景**:
- 継続生成中に `httpx.RemoteProtocolError: peer closed connection without sending complete message body (incomplete chunked read)` が発生し、処理全体が `error` 終了していた。

**対応**:
- `backend/app/domains/blog/services/generation_service.py`
  - `_is_retryable_stream_exception()` を追加し、以下を再試行対象に判定:
    - `httpx.RemoteProtocolError`, `httpx.ReadError`, `httpx.ReadTimeout`, `httpx.ConnectError`
    - `openai.APIConnectionError`, `openai.APITimeoutError`
    - `incomplete chunked read` 等のメッセージ一致
  - `_run_agent_streamed_with_retry()` を追加
    - 既定 `3` 回まで自動再試行（指数バックオフ）
    - 再試行中は `generation_warning` イベントを通知し、状態を `in_progress` のまま保持
  - `run_generation()` / `continue_generation()` の実行経路を `*_with_retry` に切替

**効果**:
- 一時的な上流ストリーム断では即失敗せず自動回復を試みる。
- 最終試行まで失敗した場合のみ従来どおり例外を返す。

**実データ確認（ユーザー報告の失敗プロセス）**:
- `process_id=0209872c-09c3-4a8b-a1d8-b559f89e719d`
- 失敗自体は発生済み履歴として保持（`state.status=error`, `session.status=failed`）だが、ログ整合性は補正完了:
  - `trace_tool_output_missing_call_id=0`
  - `trace_tool_output_missing_tool_name=0`
  - `tool_call_logs status_counts={'completed': 18}`
  - `tool_call_logs missing_output=0`

**実行コマンド**:
- `cd backend && uv run ruff check app/domains/blog/services/generation_service.py app/domains/admin/service.py testing/backfill_blog_tool_logs_from_trace.py`
- `cd frontend && bunx eslint "src/app/(admin)/admin/blog-usage/[processId]/page.tsx" "src/app/(admin)/admin/blog-usage/page.tsx"`
- `cd frontend && bun run lint`（既存の `<img>` 警告のみ）

### 44. Response ID表示誤認の解消とトークン積み上がり実測確認 (2026-02-21)

**背景**:
- 管理UIの「レスポンス別トークン」表で `response_id` を先頭のみ表示していたため、別IDが同一に見える事象が発生。
- その結果、「同一レスポンスが繰り返し課金されている」ように見えていた。

**実DB確認（process_id=2d63c9d7-8d7d-4761-8cc7-c4cbcb62e675）**:
- `llm_call_logs` は 8行、`api_response_id` は **8件すべてユニーク**
- `blog_agent_trace_events` の `response.completed` も **8件** で、`llm_call_logs.api_response_id` と 1:1 で一致
- `execution_token_sums.input=367,519` / `llm_token_sums.input=367,519`（一致）
- `event_type` に `*.delta` / `keepalive` は 0（トークン粒度保存は未実施）

**UI修正**:
- `frontend/src/app/(admin)/admin/blog-usage/page.tsx`
  - `formatResponseId()` を追加（`先頭20 + … + 末尾10`）
  - LLM callテーブルの `Response ID` を新フォーマットに変更し、`title` で全文を保持
- `frontend/src/app/(admin)/admin/blog-usage/[processId]/page.tsx`
  - 同様に `formatResponseId()` を追加し、詳細画面の `Response ID` 表示を修正

**狙い**:
- プレフィックス衝突による誤認を防止
- テーブル可読性を維持しつつ、IDの識別性を担保

**実行コマンド**:
- `cd backend && PYTHONPATH=. uv run python testing/verify_blog_trace_logs.py 2d63c9d7-8d7d-4761-8cc7-c4cbcb62e675`
- `cd frontend && bunx eslint "src/app/(admin)/admin/blog-usage/page.tsx" "src/app/(admin)/admin/blog-usage/[processId]/page.tsx"`

### 45. WordPress参照ツールの実測ベース圧縮最適化（精度維持）(2026-02-21)

**背景**:
- `wp_get_post_raw_content` と `wp_get_post_block_structure` が会話履歴の大半を占有し、入力トークン増大の主因。
- 「精度を落とさず、LLMが読める形で圧縮したい」という要件に対応。

**実際にツールを呼び出して検証**:
- 実行対象サイト: `wordpress_site_id=b3a33836-b5e9-41f4-8697-7776849d4c41`
- 実記事ID: `19448`, `19316`
- トークン計測: `tiktoken (gpt-4o)`

**施策と実装**:
1. `backend/app/domains/blog/services/wordpress_mcp_service.py`
   - `structuredContent` の返却を `indent=2` からミニファイJSONへ変更（情報欠損なし）
2. `backend/app/domains/blog/agents/tools.py`
   - `wp_get_post_raw_content(post_id, include_rendered=False, compact=True)`
     - デフォルトで `{schema, post_id, raw}` を返す（`rendered` は必要時のみ）
   - `wp_get_post_block_structure(post_id, compact=True)`
     - 短キー形式で返却: `b=blockName, a=attrs, i=innerBlocks, h=innerHTML`
     - `keys` マップを同梱し、LLMが展開可能な形を維持
3. `backend/app/domains/blog/agents/definitions.py`
   - ツール利用方針に「トークン効率ルール」を追加
   - `include_rendered` は必要時のみ有効化する運用を明文化

**実測結果（変更後）**:
- `post_id=19448`
  - `wp_get_post_raw_content`:
    - フル（`include_rendered=true, compact=false`）: `3484 tokens`
    - デフォルト（`include_rendered=false, compact=true`）: `1925 tokens`（**-44.7%**）
  - `wp_get_post_block_structure`:
    - フル（`compact=false`）: `2618 tokens`
    - デフォルト（`compact=true`）: `1968 tokens`（**-24.8%**）
- `post_id=19316`
  - `wp_get_post_raw_content`:
    - フル: `8984 tokens`
    - デフォルト: `4585 tokens`（**-49.0%**）
  - `wp_get_post_block_structure`:
    - フル: `5874 tokens`
    - デフォルト: `4646 tokens`（**-20.9%**）

**結論**:
- 最適解は「情報を削らずに表現を最適化し、重複（rendered）を必要時のみ取得」。
- 精度重視ケースでも `include_rendered=true` を明示すれば従来相当の情報量に戻せるため、品質とコストを両立できる。

**実行コマンド**:
- `cd backend && PYTHONPATH=. uv run python - <<'PY' ... 実ツール呼び出し比較スクリプト ... PY`
- `cd backend && uv run ruff check app/domains/blog/agents/tools.py app/domains/blog/agents/definitions.py app/domains/blog/services/wordpress_mcp_service.py`

### 46. Prompt Caching 最大化の実装（Blog AI / Responses API）(2026-02-22)

**背景**:
- `cached_tokens=0` が一部ターンで発生し、キャッシュ効果が不安定だった。
- 実DB（`process_id=cd1abfe9-9a13-4cc9-881b-e0e28dacf1ea`）で `llm_call_logs` を確認すると、同一実行内でも `0%` と `80%+` が混在。
- 公式仕様に沿って、`prompt_cache_key` の明示・保持期間設定・観測メタデータ追加を実施。

**公式根拠**:
- Prompt caching は先頭プレフィックス一致ベースで、`prompt_cache_key` はヒット率最適化に有効。
- `prompt_cache_retention=24h` で保持期間を延長できる。
- Responses API / Agents SDK では `ModelSettings.extra_body` と `prompt_cache_retention` 経由で設定可能。

**実装内容**:
1. `backend/app/domains/blog/services/generation_service.py`
   - `RunConfig` 生成を共通化: `_build_blog_run_config()`
   - キャッシュ設定付き `ModelSettings` を注入: `_build_run_model_settings()`
   - 安定 `prompt_cache_key` を生成: `_build_prompt_cache_key()`
   - 入力が画像付きかを判定して cache key に反映: `_input_has_images()`
   - `llm_call_logs.response_data` に以下を追加:
     - `cache_hit_rate`
     - `cache_config.prompt_cache_key`
     - `cache_config.prompt_cache_retention`
     - `cache_config.parallel_tool_calls`
2. `backend/app/core/config.py`
   - 追加環境変数:
     - `BLOG_GENERATION_PARALLEL_TOOL_CALLS` (default: `true`)
     - `BLOG_PROMPT_CACHE_ENABLED` (default: `true`)
     - `BLOG_PROMPT_CACHE_SCOPE` (default: `site`)
     - `BLOG_PROMPT_CACHE_KEY_VERSION` (default: `v1`)
     - `BLOG_PROMPT_CACHE_RETENTION_24H` (default: `true`)
3. `backend/testing/analyze_blog_prompt_cache.py` を新規追加
   - プロセス単位で `llm_call_logs` の cache hit 率を可視化
   - 各レスポンスの `in/cache/out/reasoning/hit%` を時系列表示
   - `response_data.cache_config` も確認可能

**期待効果**:
- 同一サイト・同一ワークフローでのキャッシュ命中率を安定化
- `parallel_tool_calls` 明示化で依存のないツールを同一ターンで実行しやすくし、ターン数増加を抑制
- 「なぜそのターンが `cached=0` だったか」をDBログから追跡可能に

**実行コマンド**:
- `cd backend && uv run ruff check app/core/config.py app/domains/blog/services/generation_service.py testing/analyze_blog_prompt_cache.py`
- `cd backend && PYTHONPATH=. uv run python testing/analyze_blog_prompt_cache.py cd1abfe9-9a13-4cc9-881b-e0e28dacf1ea`

**追記（2026-02-22 hotfix）**:
- `prompt_cache_key` を可読文字列連結で生成した結果、OpenAI の上限64文字を超えて `400 invalid_request_error` が発生。
- `generation_service.py` の `_build_prompt_cache_key()` を修正し、`可読な短い接頭辞 + SHA-256ハッシュ(24hex)` 方式に変更。
- `site/process/global` + `text/image` の差分は維持しつつ、常時64文字以下（実測45文字）を保証。
- 続く実運用観測で `site` スコープでも途中 `cached_tokens=0` が残るケースがあったため、`backend/app/core/config.py` の既定値を `BLOG_PROMPT_CACHE_SCOPE=process` に変更（未指定時のみ適用）。

### 47. 管理画面Trace詳細の会話履歴 `unknown` 表示解消（function_call / output / reasoning対応）(2026-02-22)

**背景**:
- `blog_context.conversation_history` は `result.to_input_list()` をそのまま保存しているため、`role=user/assistant` だけでなく
  `type=reasoning`, `type=function_call`, `type=function_call_output` が大量に含まれる。
- 管理画面詳細 `frontend/src/app/(admin)/admin/blog-usage/[processId]/page.tsx` では `item.role` のみで表示ラベルを作っていたため、
  これらがすべて `unknown` と表示され、本文も `-` になっていた。

**実DB確認（process_id=8f4b300a-a5cf-4cb4-8fff-3f1b03623f30）**:
- `conversation_history` 32件中、`reasoning` / `function_call` / `function_call_output` が多数存在
- 例: `wp_get_site_info`, `wp_get_post_types`, `ask_user_questions`, `wp_create_draft_post` の引数・返却が履歴内に正しく保存されている
- つまり「ログ欠損」ではなく「UI解釈不足」が原因

**UI修正**:
- `page.tsx` に会話履歴専用の解釈ヘルパーを追加
  - `tool_call:<name>`
  - `tool_output:<name>`
  - `reasoning`
  - `assistant` / `user`
- `function_call.arguments`, `function_call_output.output`, `reasoning.summary`, `message.content` を型別にプレビュー表示
- `全文` ボタンはテキストではなく **履歴アイテムの生JSON** を開くよう変更（引数/返却値を正確に確認可能）
- `function_call_output` は同一履歴内の `call_id -> tool_name` マップでツール名を補完表示

**実行コマンド**:
- `cd frontend && bunx eslint "src/app/(admin)/admin/blog-usage/[processId]/page.tsx"`

### 48. Prompt Caching 根本最適化 — グローバルスコープ化 & モダリティ分離廃止 (2026-02-22)

**背景**:
- 実データ分析で4プロセスのキャッシュヒット率が 26-66%（平均 ~45%）と低かった
- 特に2回目の実行（ユーザー回答後の continue_generation）で 0% になるケースが頻発
- gpt-5.2 はキャッシュ入力 90% 割引（$1.75 → $0.175/Mトークン）のため、改善の経済効果が大きい

**根本原因（大規模調査で特定）**:

1. **`prompt_cache_key` のスコープが `process`**: 各プロセスが固有キーを持つため、プロセス間でキャッシュが共有されない。全Blog AIリクエストで tools + instructions プレフィックス（~12,000+トークン）は同一なのに、プロセスごとに異なるサーバーにルーティングされていた
2. **modality（text/image）でキーを分割**: 画像付きリクエストが別サーバーにルーティングされ、キャッシュが不必要に分断。キャッシュはプレフィックス一致で動作し、tools + instructions プレフィックスはモダリティに関係なく同一
3. **gpt-5.2 は `prompt_cache_key` 必須**: テストで実証。`prompt_cache_key` なしだと gpt-5.2 は自動キャッシュされない（gpt-5-mini は自動で機能する）

**公式仕様の検証結果**:
- `instructions` パラメータと `developer` ロールメッセージは **キャッシュ的に完全同一**（テストで実証、同じプレフィックスを共有）
- `prompt_cache_key` は **サーバールーティング** に影響（同一キー → 同一サーバー → キャッシュヒット率向上）
- `prompt_cache_key` が異なると、内容が同一でも **キャッシュミス**（隔離されたバケット）
- Agents SDK は内部の全ターンで `extra_body`（`prompt_cache_key` 含む）を正しく伝搬（SDK ソース確認済み）
- 最小キャッシュ閾値: 1024 トークン、128 トークン刻みでプレフィックス一致
- `prompt_cache_retention='24h'`: キャッシュ保持を最大24時間に延長

**変更内容**:

| ファイル | 変更 |
|---------|------|
| `backend/app/core/config.py` | `BLOG_PROMPT_CACHE_SCOPE` デフォルトを `"process"` → `"global"` に変更 |
| `backend/app/domains/blog/services/generation_service.py` | `_build_prompt_cache_key()` から `has_images` パラメータとモダリティ分岐を削除 |
| 同上 | `_build_run_model_settings()` から `has_images` パラメータを削除 |
| 同上 | `_build_blog_run_config()` から `has_images` パラメータを削除 |
| 同上 | `run_generation()` / `continue_generation()` から `has_images` 変数と `_input_has_images()` 呼び出しを削除 |
| 同上 | `_input_has_images()` メソッドを削除（未参照） |
| 同上 | キー生成のフォールバックスコープを `"site"` → `"global"` に変更 |

**キーの変化**:
- 旧: `bai:v1:gpt-5.2:p:txt:HASH1` (process/site ごとに異なるキー、modality で分岐)
- 新: `bai:v1:gpt-5.2:g:HASH2` (全Blog AIリクエストで同一キー)

**実測テスト結果（gpt-5.2、実際の BLOG_WRITER_INSTRUCTIONS 使用）**:
| リクエスト | input_tokens | cached_tokens | ヒット率 |
|-----------|-------------|--------------|---------|
| 1 (コールドスタート) | 2,791 | 0 | 0.0% |
| 2 (ウォームアップ後) | 2,793 | 2,688 | **96.2%** |
| 3 (別プロセス、同一キー) | 2,791 | 2,560 | **91.7%** |
| 4 (previous_response_id) | 2,867 | 2,688 | **93.8%** |
| **合計** | 11,242 | 7,936 | **70.6%** (コールドスタート含む) |
| **コスト削減** | | | **63.5%** |

**本番でのキャッシュ率予測**:
- 22ツールのスキーマ定義（~8,000-15,000トークン）が追加のキャッシュ対象プレフィックスに
- 2回目以降のリクエストでは tools + instructions プレフィックス全体がキャッシュヒット
- **推定キャッシュ率: 80-95%**（コールドスタートを除く）
- **推定コスト削減: 60-80%**（入力トークンコスト）

**OpenAI Prompt Caching 重要な技術知見**:

| 項目 | 詳細 | ソース |
|------|------|--------|
| `instructions` vs `developer` | キャッシュ的に同一。同じプレフィックスを共有 | 実測テスト |
| gpt-5.2 自動キャッシュ | **されない**。`prompt_cache_key` 必須 | 実測テスト |
| gpt-5-mini 自動キャッシュ | される。`prompt_cache_key` なしでも95%+ | 実測テスト |
| `prompt_cache_key` 隔離 | 異なるキー = 異なるバケット。内容同一でもキャッシュミス | 実測テスト |
| 最小閾値 | 1024 トークン。以下はキャッシュされない | OpenAI公式 |
| 増分単位 | 128 トークン刻みでプレフィックス一致 | OpenAI公式 |
| `previous_response_id` との組み合わせ | `instructions` は持ち越されない（毎回再送）が、キャッシュは効く | SDK docstring + 実測 |
| RPM上限 | prefix + key あたり ~15 RPM 以下が推奨 | OpenAI公式 |
| 料金割引 | gpt-5系: 90%、gpt-4.1系: 75%、gpt-4o系: 50% | OpenAI pricing |

**情報ソース**:
- https://developers.openai.com/api/docs/guides/prompt-caching/
- https://developers.openai.com/cookbook/examples/prompt_caching_201/
- https://developers.openai.com/api/docs/pricing
- SDK: `openai` v2.16.0 (`responses.py` L222-224, `response_create_params.py` L85-91)
- SDK: `openai-agents` v0.7.0 (`openai_responses.py` L338-341, `run.py` L1469-1527)

### 49. Admin Blog Usage UI リデザイン (2026-02-22)

**概要**: `/admin/blog-usage` のダイアログ式詳細表示を廃止し、動的ルート `/admin/blog-usage/[processId]` の詳細ページを全面リデザイン。

**`blog-usage/page.tsx` 変更 (1235行→~800行)**:
- Dialog式「詳細」ボタンを削除
- 「ページ」ボタンを「詳細」にリネーム（動的ルートへの遷移のみ）
- Dialog関連コード全削除: imports, state (traceOpen/traceData/traceLoading/traceError), fetchTrace, traceLlmCalls/traceToolCalls memo, Dialog JSX (~225行), 5つの型定義, 3つのヘルパー関数

**`blog-usage/[processId]/page.tsx` 全面リライト (723行→~1287行)**:
- **ヘッダー**: ユーザープロンプト表示、ステータスバッジ（色分け）、作成日時・ユーザーメール・セッション時間
- **メトリクスカード (6枚)**: Total Cost / Total Tokens / Cache Hit Rate（プログレスバー付き） / LLM Calls / Tool Calls / Duration
- **キャッシュパフォーマンスセクション**: LLM Call ごとの水平バーチャート（emerald >70% / amber 40-70% / red <40%）
- **LLM Calls テーブル**: クリックで行展開（response_data JSON表示）、Cache%に色付きテキスト
- **Tool Calls セクション**: カードベースレイアウト、クリック展開で入出力JSON表示
- **会話履歴**: Collapsible（デフォルト閉じ）、チャット風レイアウト（user=右寄せ青、assistant=左寄せ灰、tool_call=amber、reasoning=purple）
- **時系列イベント**: Collapsible（デフォルト閉じ）、シンプルテーブル

### 50. 管理画面レイアウト: 日本語化 + 折りたたみサイドバー + shadcn UI化 (2026-02-22)

**変更ファイル**: `frontend/src/app/(admin)/admin/layout.tsx` (155行→~190行)

**ナビゲーション日本語化**:
- Dashboard → ダッシュボード
- Users → ユーザー管理
- Usage → 記事別Usage
- Inquiries → お問い合わせ
- Plans → プラン設定
- Back → アプリに戻る
- ヘッダータイトル: Admin → 管理画面

**折りたたみサイドバー（デスクトップ）**:
- サイドバー下部に「閉じる」ボタン（ChevronLeft/ChevronRight アイコン）
- 折りたたみ時: w-[60px]、アイコンのみ表示
- 展開時: w-56、アイコン + ラベル表示
- `transition-[width] duration-200` でスムーズなアニメーション
- `localStorage('admin-sidebar-collapsed')` で状態を永続化
- 折りたたみ時はホバーで **Tooltip** にラベル表示

**shadcn UI 化**:
- モバイルサイドバー: 素のdiv overlay → **Sheet** コンポーネント（side="left"、スライドインアニメーション）
- ハンバーガーボタン: 素のbutton → **Button** variant="ghost" size="icon"
- 「アプリに戻る」: 素のLink → **Button** variant="ghost" asChild
- 折りたたみトグル: **Button** variant="ghost"
- アイコンホバー: **Tooltip** / **TooltipTrigger** / **TooltipContent** (TooltipProvider delayDuration=100)
- パス一致判定: 厳密一致(/) + プレフィックス一致(子ルート)
