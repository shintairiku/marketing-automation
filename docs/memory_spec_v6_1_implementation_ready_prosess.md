# Memory実装プロセス記録（Blog / v7.2）

このファイルは `docs/memory_spec_v6_1_implementation_ready.md` に基づく実装の進行記録です。  
実装で確定した事項、作業ログ、未解決事項を時系列で追記します。

## 0. 運用ルール（固定）
- DB操作（Supabase起動/停止、migration適用、db push等）はユーザーが実行する。
- Gitの大きな操作（branch操作、push、PR、merge等）はユーザーが実行する。
- 不明点が出たら、実装を進める前にユーザーへ確認する。
- コミットメッセージ規約: `feat: ●●●（日本語でわかりやすく）`

## 1. 今回の実装スコープ（フェーズ1）
- `process_id` を正規IDとして Blog Memory を実装する。
- `organization_id` は `/blog/generation/start` で確定し、プロセス中は固定。
- `process_id` はツール公開引数ではなくサーバー側コンテキストで解決する。
- `web_search` の `tool_result` 自動保存は本フェーズでは実装しない（フェーズ2）。

## 2. 確定事項ログ
- 2026-02-23: 仕様書先頭に実装運用ルールを追記済み（DB/Git実行責任、記録方針、即時確認方針）。
- 2026-02-23: 記録ファイルは `docs/memory_spec_v6_1_implementation_ready_prosess.md` を使用することで確定。
- 2026-02-23: 実装順はTDD（テスト先行）で進める方針に変更。
- 2026-02-23: `organization_id` は `/blog/generation/start` 時に `wordpress_sites.organization_id` で確定・保存する実装に確定。
- 2026-02-23: Blog Memory APIは `/blog/generation/{process_id}/memory/*` で提供し、アプリ層で process 所有チェック（404/403）を必須化。
- 2026-02-23: usage計測はユーザー推定ではなく `blog_generation_state.organization_id` を参照する方式に確定。

## 3. 実装ログ
- 2026-02-23 21:10
  - 対象: `backend/tests/test_blog_memory_tdd.py`
  - 実施内容: TDD用テストを先行追加（start時organization_id保存、memory APIレスポンス、role禁止、usage組織固定）。
  - 仕様との対応: 12.1, 12.2, 12.3, 13.1, 13.4
  - 影響範囲: Backend unit tests
  - 検証結果: `uv run pytest tests/test_blog_memory_tdd.py -q` で Red->Green を確認
- 2026-02-23 21:25
  - 対象: `backend/app/domains/blog/endpoints.py`
  - 実施内容: `/generation/start` の organization_id保存、usage checkをsite基準へ変更、`/generation/{process_id}/memory/*` 3API追加。
  - 仕様との対応: 7系API, 12.1, 12.2, 12.3
  - 影響範囲: Blog API
  - 検証結果: 追加テストで確認
- 2026-02-23 21:35
  - 対象: `backend/app/domains/blog/services/memory_service.py`, `backend/app/domains/blog/services/memory_embedding_job.py`
  - 実施内容: Memory RPC呼び出し、埋め込み生成、検索、embedding batch更新のサービスを追加。
  - 仕様との対応: 6系RPC, 8系Embedding投入, 14.1
  - 影響範囲: Blog service層
  - 検証結果: compileall通過
- 2026-02-23 21:45
  - 対象: `backend/app/domains/blog/services/generation_service.py`, `backend/app/domains/blog/agents/tools.py`, `backend/app/domains/blog/agents/definitions.py`, `backend/app/domains/blog/services/wordpress_mcp_service.py`
  - 実施内容: Memory検索文脈注入・append/upsert連携、usage組織固定、memory_* Function Tool追加、全Toolのprocessコンテキスト整合ガードを追加。
  - 仕様との対応: 2.9, 9.1, 9.3, 12.1, 12.3, 13.4
  - 影響範囲: Blog generation runtime / tools
  - 検証結果: `uv run pytest tests/test_blog_memory_tdd.py -q` Green、`uv run python -m compileall ...` 通過
- 2026-02-23 22:07
  - 対象: `backend/app/domains/blog/endpoints.py`, `backend/app/domains/blog/services/memory_service.py`, `supabase/migrations/20260223113000_add_blog_memory_tables_rpc_rls.sql`
  - 実施内容: ローカルSupabase上でMemory E2E疎通を実施（`memory/items` -> `memory/meta/upsert` -> embedding job -> `memory/search`）。
  - 仕様との対応: 7.1, 7.2, 7.3, 8.1, 8.2
  - 影響範囲: Blog Memory API / RPC / embedding batch / 検索結果整合性
  - 検証結果: 別`process_id`に対して `hits` が返り、`meta.title/short_summary` と `items.content` を取得できることを確認。
- 2026-02-23 23:20
  - 対象: `backend/app/domains/blog/endpoints.py`, `backend/app/domains/blog/services/memory_service.py`, `backend/tests/test_blog_memory_tdd.py`
  - 実施内容: `process_id` 不正形式時に `INTERNAL_ERROR` ではなく `INVALID_ARGUMENT(400)` を返すよう修正。DB例外マッピングにもUUID不正を追加。
  - 仕様との対応: 7.4, 7.5, 13.1
  - 影響範囲: Blog Memory APIエラーハンドリング / テスト
  - 検証結果: `uv run pytest tests/test_blog_memory_tdd.py -q` で `8 passed`。

### ログ追記テンプレート
- YYYY-MM-DD HH:MM
  - 対象: `path/to/file`
  - 実施内容: 
  - 仕様との対応: 
  - 影響範囲: 
  - 検証結果: 

## 4. 未解決事項 / 要確認
- 現在なし

## 5. 次アクション
- ユーザー実行でコミット・PR（develop向け）を進める。
- 必要なら追加のE2E（process所有境界 / include_roles / embedding null除外）をテスト追加する。
