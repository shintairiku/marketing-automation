# Blog Memory Seed Data

このディレクトリは、Blog Memory のローカル検証用シードデータです。

## ファイル

- `generate_seed_csv.py`
  - 120記事分のCSVを生成
- `blog_memory_meta_seed.csv`
  - タイトル・要約・ユーザー入力などメタ情報
  - 学習系だけでなく、イベント告知・社員紹介・導入事例・機能アップデート等を含む
- `blog_memory_items_seed.csv`
  - role別メモリ本文（`user_input`, `source`, `system_note`, `assistant_output`, `final_summary`, `tool_result`）
  - `user_input` には通常入力に加えて `Q(question)+A(answer)` 形式の行も含む
- `load_seed_to_local.sql`
  - CSVをローカルDBへ投入するSQL

## 1. CSV生成

```bash
python3 test/blog_memory_seed/generate_seed_csv.py
```

## 2. ローカルDBへ投入

`$PID` は既存の `blog_generation_state.id`（同じ user/org/site をコピー元に使う）を指定してください。

```bash
psql "$DB_URL" -v base_pid="$PID" -f test/blog_memory_seed/load_seed_to_local.sql
```

## 3. 埋め込み投入

```bash
cd backend
uv run python -c "import asyncio; from app.domains.blog.services.memory_embedding_job import run_blog_memory_embedding_job; print(asyncio.run(run_blog_memory_embedding_job()))"
cd ..
```

## 4. 検索確認

```bash
curl -sS -X POST "$API_URL/blog/generation/$PID/memory/search" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"query":"高専 勉強法 過去問 学習計画","k":5,"per_process_item_limit":5}' | jq
```
