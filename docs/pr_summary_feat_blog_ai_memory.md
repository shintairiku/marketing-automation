# PR概要: Blog Memory機能追加とorganization_id整合性の統一

## 目的
このPRの目的は、ブログ生成に再利用可能なMemory機能を導入し、生成品質を継続的に改善できる基盤を作ることです。  
特に重要な変更は、**会社ID（`organization_id`）を process 起点で一貫して扱うようにしたこと**です。これにより、使用量計測・ログ・Memoryスコープの整合性を揃えています。

## 最重要変更（organization_id）
1. 生成開始時の使用量チェックを、サイトに紐づく `organization_id` 基準に統一  
   `backend/app/domains/blog/endpoints.py:1098`
2. `blog_generation_state` 作成時に `organization_id` を process に固定保存  
   `backend/app/domains/blog/endpoints.py:1146`
3. 生成完了時の `usage_service.record_success(...)` で、`process_id` から取得した `organization_id` を使用  
   `backend/app/domains/blog/services/generation_service.py:1967`
4. ログセッション作成時も process 固定の `organization_id` を使用  
   `backend/app/domains/blog/services/generation_service.py:245`  
   `backend/app/domains/blog/services/generation_service.py:367`

## 変更概要
1. Blog MemoryのDB基盤（テーブル/RLS/RPC）を追加  
   `supabase/migrations/20260223113000_add_blog_memory_tables_rpc_rls.sql`
2. roleに `qa` を追加する追補マイグレーションを追加  
   `supabase/migrations/20260227143000_add_blog_memory_qa_role.sql`
3. Memoryサービス層（append/upsert/search/embedding batch）を実装  
   `backend/app/domains/blog/services/memory_service.py`  
   `backend/app/domains/blog/services/memory_embedding_job.py`
4. Memory API（append/meta upsert/search/sync-post）を追加  
   `backend/app/domains/blog/endpoints.py`  
   `backend/app/domains/blog/schemas.py`
5. 生成フローへMemory連携を追加（事前検索注入、自動保存、tool_result保存制御）  
   `backend/app/domains/blog/services/generation_service.py`
6. ツール説明/エージェント指示をMemory運用に合わせて整理  
   `backend/app/domains/blog/agents/tools.py`  
   `backend/app/domains/blog/agents/definitions.py`
7. WordPressツール実行時の process 整合性チェックを追加  
   `backend/app/domains/blog/services/wordpress_mcp_service.py`
8. TDD/検証用データを追加  
   `backend/tests/test_blog_memory_tdd.py`  
   `test/blog_memory_seed/*`
9. 仕様書・実装ログを追加  
   `docs/memory_spec_v6_1_implementation_ready.md`  
   `docs/memory_spec_v6_1_implementation_ready_prosess.md`

## ファイル別の主な変更
### `backend/app/domains/blog/endpoints.py`
- `/generation/{process_id}/memory/*` API群を追加
- `process_id` 所有者チェックを共通化し、エラーコードを統一
- 生成開始時の利用制限チェックをサイト由来 `organization_id` で実行

### `backend/app/domains/blog/services/memory_service.py`
- `blog_memory_*` RPC呼び出し、埋め込み生成、roleバリデーション、検索結果整形を実装
- `tool_result` は一般append経由で拒否し、専用RPC経由のみ許可

### `backend/app/domains/blog/services/generation_service.py`
- 初回入力前にMemory検索して文脈注入
- `user_input`/`qa`/`final_summary`/`decision_memo`/`post_snapshot` の自動保存を追加
- `memory_search` ログを `system_note` として保存
- `web_search` と `memory_search` は `tool_result` 保存対象外に設定

### `backend/app/domains/blog/services/wordpress_mcp_service.py`
- `process_id` 未設定・所有不一致・site不一致の早期拒否チェックを追加

### `supabase/migrations/*.sql`
- Memoryテーブル、RLS、RPC（append/upsert/search/get-items）を追加
- 後続マイグレーションで `qa` role を追加

### `backend/tests/test_blog_memory_tdd.py`
- `organization_id` 引き回し、Memory APIエラー、role制約、フォーマット処理などをテスト

### `test/blog_memory_seed/*`
- 大量シード投入と状態確認SQLを追加
- ローカルで埋め込み/検索の検証を容易化

## 動作イメージ
1. 生成開始時に `user_prompt` でMemory検索し、関連文脈を入力に注入
2. 生成中の重要情報を自動保存
3. 完了時に要約・メタ・意思決定メモ・投稿スナップショットを保存
4. 次回生成時に再検索して再利用

## 今後の拡張候補
1. 検索スコア閾値の運用設定（環境変数化と観測）
2. `continue_generation` 側への事前Memory注入（初回と同等化）
3. `tool_result` 保存対象ツールのホワイトリスト運用
4. embeddingバッチの定期実行基盤（Cron/Job Runner統合）
5. `sync-post` の正式運用フロー統合可否の判断

## 確認済みポイント
1. `organization_id` は process 起点で一貫利用
2. Memory APIに `process_id` 所有者制御あり
3. `tool_result` は一般append不可、専用経路のみ
4. roleに `qa` を追加済み

## 補足
PR作成時は、PR対象外のローカル変更（例: `supabase/config.toml`）が混入しないよう最終確認してください。
