# 長期記憶（Memory）機能 実装仕様書（Blog専用・実装用 v7.2）
**Blog Domain専用 / process_id正規ID / 段階導入（Autologは後続）**
対象：本リポジトリの Blog AI（`/blog/generation/*`）
目的：ブログ生成で再利用可能な長期記憶を、安全に保存・検索・注入する。

## 実装運用ルール（本セッション）
- 本仕様に基づく実装はこのブランチで進める。
- **データベース操作（Supabase起動/停止、migration適用、db push 等）**はユーザー実行とする。
- **Gitの大きな操作（branch操作、push、PR、merge等）**はユーザー実行とする。コミットは適宜行い、コミットメッセージはfeat: ●●●（日本度でわかりやすく）の形で書く。
- 実装で確定した事項・作業ログ・未解決事項は `docs/memory_spec_v6_1_implementation_ready_prosess.md` に都度追記する。
- 不明点や分岐判断が必要な点は、実装を進める前に即時ユーザーへ確認する。

---

## 変更履歴
- v7.2: 合意内容に合わせて段階導入へ調整（責任範囲内のみ）。
  - `process_id` は LLM引数必須ではなく、サーバーコンテキスト注入を基本方針化
  - `organization_id` 開始時確定・プロセス固定を必須のまま維持
  - `web_search` の `tool_result` 保存は本フェーズ対象外（後続実装）に変更
  - 既存のAutolog仕様は削除せず「将来拡張（フェーズ2）」として保持
- v7.1: 実装前最終調整。
  - `organization_id` の開始時確定・プロセス固定を明文化
  - 認可方針をプロジェクト標準（service role + アプリ層判定 + RLS防御層）に統一
  - Blog生成で呼ぶ全Function Toolの `process_id` 必須化を明文化（`ask_user_questions`, `wp_*` 含む）
  - Embeddingの環境変数可変 + 一般的デフォルトを明記
  - 生成プロセス削除は運用上発生しない前提を明文化
- v7.0: 仕様を全面改訂。SEO前提を廃止し、**Blog専用**に再定義。
  - 正規IDを `process_id`（=`blog_generation_state.id`）に統一
  - `post_id` は外部システム（WordPress）IDとして別管理
  - 組織未所属（`organization_id IS NULL`）の個人利用を正式サポート

---

## 1. 目的と非目的
### 1.1 目的
1. Blog生成プロセス単位（`process_id`）で、生成に必要な情報を永続化して再利用する。
2. 生成開始時に、過去のBlog Memoryを検索してプロンプトへ注入できるようにする。
3. `organization_id` を開始時に確定し、`process_id` と一貫した所有境界で扱う。
4. `process_id` はサーバー側コンテキストで注入し、ツール呼び出し時の紐付け漏れを防ぐ。
5. 外部ツール結果のMemory保存（`tool_result`）は将来拡張として仕様を保持する。

### 1.2 非目的
- SEO記事ドメイン（`/articles/*`）への適用
- `articles.id` を主IDとして扱う設計
- WordPress `post_id` をMemory主キーにする設計
- `tool_call_logs / llm_call_logs` の廃止（併存）
- 本フェーズでの `web_search` Autolog 実装

---

## 2. 最重要決定事項（固定）
### 2.1 正規IDは `process_id`
- 本仕様での対象エンティティIDは **`process_id` のみ**。
- `process_id` は `blog_generation_state.id`（UUID）。
- Memory API / RPCの入力は `process_id` を必須とする。
- Blog生成ツール（LLM公開スキーマ）では `process_id` を明示入力させず、サーバーコンテキストで注入する。

### 2.2 `post_id` は外部ID
- WordPress `post_id` は外部参照用。
- Memoryの主キー・境界判定・検索キーには使わない。

### 2.3 組織境界は「org優先、個人フォールバック」
- `blog_generation_state.organization_id` が非NULLなら org境界。
- NULLなら個人境界（`user_id`）として扱う。
- これにより個人サイト利用でもMemoryを有効化する。

### 2.4 所有境界情報をリクエストから受け取らない
- `organization_id` / `user_id` をBodyやTool引数で受け取らない。
- すべて `process_id -> blog_generation_state` から解決する。

### 2.5 tool_result保存方針（段階導入）
- Agentが `memory_append_item(role="tool_result")` を呼ぶのは禁止。
- `tool_result` の自動保存は将来拡張（フェーズ2）で導入する。
- 本フェーズでは `tool_call_logs / llm_call_logs` を監査ログとして利用する。

### 2.6 tool_resultのcontentはJSON文字列
トップレベル必須キー:
- `tool_name`: string
- `status`: `"ok" | "error"`
- `input`: object（必ず `process_id` を含む）
- `output`: object|string
- `ts`: UTC ISO-8601 string

### 2.7 サイズ制限
- tool_result JSON文字列は最大 **100,000文字**。
- 超過時は `output` を先頭から切り詰め、`truncated=true` と `original_length` を付与。

### 2.8 保存失敗時の扱い（フェーズ2ルール）
- ツール本体が成功しても、Autolog保存失敗時はツール呼び出し失敗として扱う。
- 本フェーズでは Autolog 自体を導入しないため、このルールは将来拡張時に適用する。

### 2.9 `organization_id` の確定ルール（固定）
- `organization_id` は `POST /blog/generation/start` でのみ確定する。
- 確定値は `wordpress_sites.organization_id` をそのまま `blog_generation_state.organization_id` へ保存する。
- リクエストBody・Tool引数で `organization_id` を受け取って上書きしてはならない。
- `blog_generation_state.organization_id` は生成プロセス中に更新しない（開始時固定）。
- `organization_id IS NULL` の場合は userスコープとして扱う。

### 2.10 認可実装方針（プロジェクト整合）
- Backendは本プロジェクト標準どおり Supabase service role でDBアクセスする。
- 認可の主判定はアプリ層で実施し、`process_id` 所有者検証（`blog_generation_state.user_id` および組織所属）を必須とする。
- RLSは防御層（defense-in-depth）として維持し、実装ミス時の越境アクセスを抑止する。

### 2.11 削除運用の前提
- 本仕様では「生成プロセス削除は運用上発生しない」を前提とする。
- したがって `blog_generation_state` からの `on delete cascade` は許容する。
- 将来削除要件が発生した場合のみ、保持ポリシーと物理削除方針を再設計する。

### 2.12 フェーズ定義（責任範囲）
- フェーズ1（本ブランチ責任範囲）:
  - `organization_id` の開始時確定・固定
  - Memory基盤（テーブル/RPC/API）の整備
  - `process_id` サーバー注入前提でのツール整合
- フェーズ2（後続）:
  - `web_search` を含む外部ツールの `tool_result` Autolog
  - Autolog失敗時のツール失敗統一

---

## 3. アーキテクチャ概要
### 3.1 コンポーネント
- Supabase(Postgres): Memoryテーブル、RLS、RPC、vector index
- Backend(FastAPI): Memory API、ツール実装、Embedding投入ジョブ、アプリ層認可
- Agent(OpenAI Agents SDK): Function Tool呼び出し、生成制御、Memory注入

### 3.2 データフロー
1. `POST /blog/generation/start` で `process_id` を発行
2. Agent開始時に `memory_search(process_id, query, ...)`
3. ヒットしたMemoryをコンテキストへ注入
4. 外部ツール実行（`process_id` はサーバーコンテキストで解決）
5. 必要に応じて `memory_append_item(process_id, role, content)`
6. 最後に `memory_upsert_meta(process_id, title, short_summary)`
7. 非同期ジョブで `embedding_input -> embedding` を更新
8. フェーズ2で `tool_result` Autolog を追加

---

## 4. DB設計（Blog専用）
### 4.1 Extensions
```sql
create extension if not exists pgcrypto;
create extension if not exists vector;
```

### 4.2 テーブル
#### 4.2.1 `blog_memory_items`（追記ログ）
```sql
create table if not exists public.blog_memory_items (
  id uuid primary key default gen_random_uuid(),
  process_id uuid not null references public.blog_generation_state(id) on delete cascade,

  user_id text not null,
  organization_id uuid null references public.organizations(id) on delete set null,
  scope_type text not null check (scope_type in ('org','user')),

  role text not null check (role in (
    'user_input',
    'assistant_output',
    'tool_result',
    'source',
    'system_note',
    'final_summary'
  )),

  content text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_blog_memory_items_process_created
  on public.blog_memory_items(process_id, created_at desc);

create index if not exists idx_blog_memory_items_scope_created
  on public.blog_memory_items(scope_type, organization_id, user_id, created_at desc);

create index if not exists idx_blog_memory_items_process_role_created
  on public.blog_memory_items(process_id, role, created_at desc);
```

#### 4.2.2 `blog_memory_meta`（1プロセス1メタ）
```sql
create table if not exists public.blog_memory_meta (
  process_id uuid primary key references public.blog_generation_state(id) on delete cascade,

  user_id text not null,
  organization_id uuid null references public.organizations(id) on delete set null,
  scope_type text not null check (scope_type in ('org','user')),

  draft_post_id integer null,
  title text not null,
  short_summary text not null,
  embedding_input text not null,

  embedding vector(1536),
  embedding_updated_at timestamptz,
  updated_at timestamptz not null default now()
);

create index if not exists idx_blog_memory_meta_scope
  on public.blog_memory_meta(scope_type, organization_id, user_id);

create index if not exists idx_blog_memory_meta_embedding
  on public.blog_memory_meta using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);
```

---

## 5. RLS
### 5.1 有効化
```sql
alter table public.blog_memory_items enable row level security;
alter table public.blog_memory_meta  enable row level security;
```

### 5.2 所有判定関数
```sql
create or replace function public.is_owner_in_scope(
  p_scope_type text,
  p_org_id uuid,
  p_user_id text
) returns boolean
language sql
stable
as $$
  select case
    when p_scope_type = 'org' then exists (
      select 1
      from public.organization_members om
      where om.organization_id = p_org_id
        and om.user_id = auth.uid()::text
    )
    when p_scope_type = 'user' then p_user_id = auth.uid()::text
    else false
  end;
$$;
```

### 5.3 Policy
```sql
create policy "blog_memory_items_select_own_scope"
  on public.blog_memory_items for select
  using (public.is_owner_in_scope(scope_type, organization_id, user_id));

create policy "blog_memory_items_insert_own_scope"
  on public.blog_memory_items for insert
  with check (public.is_owner_in_scope(scope_type, organization_id, user_id));

create policy "blog_memory_meta_select_own_scope"
  on public.blog_memory_meta for select
  using (public.is_owner_in_scope(scope_type, organization_id, user_id));

create policy "blog_memory_meta_insert_own_scope"
  on public.blog_memory_meta for insert
  with check (public.is_owner_in_scope(scope_type, organization_id, user_id));

create policy "blog_memory_meta_update_own_scope"
  on public.blog_memory_meta for update
  using (public.is_owner_in_scope(scope_type, organization_id, user_id))
  with check (public.is_owner_in_scope(scope_type, organization_id, user_id));
```

### 5.4 UPDATE/DELETE
- `blog_memory_items`: アプリからUPDATE/DELETEしない。
- 管理メンテ時はservice roleで実施。

---

## 6. DB RPC（Blog専用）
方針:
- `process_id` から `user_id / organization_id / scope_type` を解決
- 引数でorg/userを受け取らない

### 6.1 外部API用 `blog_memory_append_item`
```sql
create or replace function public.blog_memory_append_item(
  p_process_id uuid,
  p_role text,
  p_content text
) returns uuid
language plpgsql
security definer
as $$
declare
  v_user_id text;
  v_org_id uuid;
  v_scope text;
  v_id uuid;
begin
  select user_id, organization_id
    into v_user_id, v_org_id
  from public.blog_generation_state
  where id = p_process_id;

  if v_user_id is null then
    raise exception 'BLOG_PROCESS_NOT_FOUND';
  end if;

  if p_role = 'tool_result' then
    raise exception 'ROLE_TOOL_RESULT_FORBIDDEN';
  end if;

  v_scope := case when v_org_id is null then 'user' else 'org' end;

  insert into public.blog_memory_items(
    process_id, user_id, organization_id, scope_type, role, content
  )
  values (
    p_process_id, v_user_id, v_org_id, v_scope, p_role, p_content
  )
  returning id into v_id;

  return v_id;
end;
$$;
```

### 6.2 内部Autolog用 `blog_memory_append_tool_result`
```sql
create or replace function public.blog_memory_append_tool_result(
  p_process_id uuid,
  p_content text
) returns uuid
language plpgsql
security definer
as $$
declare
  v_user_id text;
  v_org_id uuid;
  v_scope text;
  v_id uuid;
begin
  select user_id, organization_id
    into v_user_id, v_org_id
  from public.blog_generation_state
  where id = p_process_id;

  if v_user_id is null then
    raise exception 'BLOG_PROCESS_NOT_FOUND';
  end if;

  v_scope := case when v_org_id is null then 'user' else 'org' end;

  insert into public.blog_memory_items(
    process_id, user_id, organization_id, scope_type, role, content
  )
  values (
    p_process_id, v_user_id, v_org_id, v_scope, 'tool_result', p_content
  )
  returning id into v_id;

  return v_id;
end;
$$;
```

### 6.3 `blog_memory_upsert_meta`
```sql
create or replace function public.blog_memory_upsert_meta(
  p_process_id uuid,
  p_title text,
  p_short_summary text,
  p_embedding_input text,
  p_draft_post_id integer
) returns void
language plpgsql
security definer
as $$
declare
  v_user_id text;
  v_org_id uuid;
  v_scope text;
begin
  select user_id, organization_id
    into v_user_id, v_org_id
  from public.blog_generation_state
  where id = p_process_id;

  if v_user_id is null then
    raise exception 'BLOG_PROCESS_NOT_FOUND';
  end if;

  v_scope := case when v_org_id is null then 'user' else 'org' end;

  insert into public.blog_memory_meta(
    process_id, user_id, organization_id, scope_type,
    draft_post_id, title, short_summary, embedding_input
  )
  values (
    p_process_id, v_user_id, v_org_id, v_scope,
    p_draft_post_id, p_title, p_short_summary, p_embedding_input
  )
  on conflict (process_id) do update
    set draft_post_id = excluded.draft_post_id,
        title = excluded.title,
        short_summary = excluded.short_summary,
        embedding_input = excluded.embedding_input,
        updated_at = now();
end;
$$;
```

### 6.4 `blog_memory_search_meta`
```sql
create or replace function public.blog_memory_search_meta(
  p_process_id uuid,
  p_query vector(1536),
  p_k int
) returns table(
  hit_process_id uuid,
  score double precision,
  draft_post_id integer,
  title text,
  short_summary text
)
language sql
security definer
as $$
  with src as (
    select user_id, organization_id,
           case when organization_id is null then 'user' else 'org' end as scope_type
    from public.blog_generation_state
    where id = p_process_id
  )
  select
    m.process_id as hit_process_id,
    (m.embedding <=> p_query) as score,
    m.draft_post_id,
    m.title,
    m.short_summary
  from public.blog_memory_meta m
  join src on (
    (src.scope_type = 'org' and m.scope_type = 'org' and m.organization_id = src.organization_id)
    or
    (src.scope_type = 'user' and m.scope_type = 'user' and m.user_id = src.user_id)
  )
  where m.embedding is not null
    and m.process_id <> p_process_id
  order by m.embedding <=> p_query
  limit p_k;
$$;
```

### 6.5 `blog_memory_get_items`
```sql
create or replace function public.blog_memory_get_items(
  p_process_id uuid,
  p_roles text[],
  p_time_window_days int,
  p_limit int
) returns table(
  role text,
  content text,
  created_at timestamptz
)
language sql
security definer
as $$
  select role, content, created_at
  from public.blog_memory_items
  where process_id = p_process_id
    and (p_roles is null or role = any(p_roles))
    and (
      p_time_window_days is null
      or created_at >= now() - (p_time_window_days || ' days')::interval
    )
  order by created_at desc
  limit p_limit;
$$;
```

---

## 7. HTTP API（Blog専用）
### 7.1 ルート
- ベース: `/blog/generation/{process_id}/memory`

### 7.2 共通レスポンス
```json
{ "ok": true, "data": ... }
{ "ok": false, "error": { "code": "SOME_CODE", "message": "human readable" } }
```

### 7.3 エラーコード
| code | HTTP | 意味 |
|---|---:|---|
| BLOG_PROCESS_NOT_FOUND | 404 | process_id が存在しない |
| ROLE_TOOL_RESULT_FORBIDDEN | 400 | 外部APIで tool_result append を試行 |
| INVALID_ARGUMENT | 400 | 入力不正 |
| UNAUTHORIZED | 401 | 認証失敗 |
| FORBIDDEN | 403 | 所有境界外 |
| INTERNAL_ERROR | 500 | 予期しないエラー |

### 7.4 バリデーション
- `process_id`: UUID string 必須
- `title`: 1..200
- `short_summary`: 1..2000
- `content`: 1..200000（tool_result以外）
- `k`: 1..50
- `time_window_days`: 1..3650

### 7.5 エンドポイント
#### 7.5.1 `POST /items`
- role: `user_input | assistant_output | source | system_note | final_summary`
- `tool_result` は禁止

Request:
```json
{ "role": "user_input", "content": "..." }
```

#### 7.5.2 `POST /meta/upsert`
- serverが `embedding_input = title + "\n\n" + short_summary` を構築
- `draft_post_id` は blog_generation_state 側から読んで保存してもよい

Request:
```json
{ "title": "...", "short_summary": "..." }
```

#### 7.5.3 `POST /search`
- server側で `query` をembedding化
- `blog_memory_search_meta` -> `blog_memory_get_items` を合成して返す

Request:
```json
{
  "query": "string",
  "k": 10,
  "include_roles": ["user_input","assistant_output","source","system_note","final_summary","tool_result"],
  "time_window_days": 365,
  "per_process_item_limit": 20
}
```

Response:
```json
{
  "ok": true,
  "data": {
    "hits": [
      {
        "process_id": "uuid",
        "score": 0.123,
        "meta": {
          "draft_post_id": 123,
          "title": "...",
          "short_summary": "..."
        },
        "items": [
          { "role": "assistant_output", "content": "...", "created_at": "..." }
        ]
      }
    ]
  }
}
```

---

## 8. Embedding投入（後段ジョブ）
### 8.1 対象
- `embedding is null` または `embedding_updated_at < updated_at`

### 8.2 単位
- 1バッチN件（例: 100）

### 8.3 更新
```sql
update public.blog_memory_meta
set embedding = $1,
    embedding_updated_at = now()
where process_id = $2;
```

---

## 9. Agent / Function Toolルール
### 9.1 Memory系
1. `memory_search(process_id, query, k, include_roles, time_window_days, per_process_item_limit)`
2. `memory_upsert_meta(process_id, title, short_summary)`
3. `memory_append_item(process_id, role, content)`

### 9.2 外部ツール
- 外部ツールの入出力スキーマに `process_id` を露出させない。
- `process_id` はサーバーコンテキスト（`blog_generation_state.id`）から解決する。
- 例: `web_search(q, recency_days, max_results)`
- `web_search` の Memory Autolog はフェーズ2で導入する（本フェーズ対象外）。

### 9.3 全Blog Function Tool共通ルール
- Memory系以外の **Blog生成フローで呼ばれる全Function Tool** は、サーバー側で `process_id` が一意に決まる実装にする。
- 対象には `web_search`、`ask_user_questions`、`wp_*`、`upload_user_image_to_wordpress` を含む。
- ツール公開スキーマはビジネス引数のみを受ける（`process_id` は公開引数に含めない）。
- サーバー側で解決した `process_id` と実行中プロセスが一致しない場合は `FORBIDDEN` とする。
- `additionalProperties: false` は継続して適用する。

---

## 10. Tool schema（JSON Schema）
### 10.1 共通
- Memory API系（`memory_*`）のみ `process_id` required
- Blog生成ツール公開スキーマでは `process_id` を受け取らない（サーバー注入）
- `additionalProperties: false`

### 10.2 `memory_append_item`
```json
{
  "name": "memory_append_item",
  "parameters": {
    "type": "object",
    "additionalProperties": false,
    "required": ["process_id", "role", "content"],
    "properties": {
      "process_id": { "type": "string", "description": "UUID of blog generation process" },
      "role": {
        "type": "string",
        "enum": ["user_input","assistant_output","source","system_note","final_summary"]
      },
      "content": { "type": "string", "minLength": 1, "maxLength": 200000 }
    }
  }
}
```

### 10.3 `memory_upsert_meta`
```json
{
  "name": "memory_upsert_meta",
  "parameters": {
    "type": "object",
    "additionalProperties": false,
    "required": ["process_id", "title", "short_summary"],
    "properties": {
      "process_id": { "type": "string" },
      "title": { "type": "string", "minLength": 1, "maxLength": 200 },
      "short_summary": { "type": "string", "minLength": 1, "maxLength": 2000 }
    }
  }
}
```

### 10.4 `memory_search`
```json
{
  "name": "memory_search",
  "parameters": {
    "type": "object",
    "additionalProperties": false,
    "required": ["process_id", "query"],
    "properties": {
      "process_id": { "type": "string" },
      "query": { "type": "string", "minLength": 1, "maxLength": 4000 },
      "k": { "type": "integer", "minimum": 1, "maximum": 50, "default": 10 },
      "include_roles": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["user_input","assistant_output","source","system_note","final_summary","tool_result"]
        }
      },
      "time_window_days": { "type": "integer", "minimum": 1, "maximum": 3650, "default": 365 },
      "per_process_item_limit": { "type": "integer", "minimum": 1, "maximum": 100, "default": 20 }
    }
  }
}
```

### 10.5 `web_search`
```json
{
  "name": "web_search",
  "description": "Search web for fresh information. process_id is resolved server-side.",
  "parameters": {
    "type": "object",
    "additionalProperties": false,
    "required": ["q"],
    "properties": {
      "q": { "type": "string", "minLength": 1, "maxLength": 2000 },
      "recency_days": { "type": "integer", "minimum": 0, "maximum": 3650, "default": 30 },
      "max_results": { "type": "integer", "minimum": 1, "maximum": 10, "default": 5 }
    }
  }
}
```

### 10.6 `ask_user_questions` / `wp_*` / `upload_user_image_to_wordpress` 共通テンプレート
```json
{
  "name": "blog_tool_template",
  "parameters": {
    "type": "object",
    "additionalProperties": false,
    "required": []
  }
}
```
- 各Tool固有パラメータは `properties` に追加する。
- `process_id` は公開引数に含めない（サーバーコンテキスト注入）。

---

## 11. tool_result Autolog 実装仕様（将来拡張 / フェーズ2）
本セクションは内容を保持するが、本フェーズの実装対象外とする。

### 11.1 共通ユーティリティ
- `build_tool_result_content(tool_name, status, input_obj, output_obj, ts_utc_iso) -> str`
- `truncate_tool_result_json(json_str) -> str`
- `append_tool_result(process_id, json_str) -> memory_item_id`

### 11.2 JSON構造
成功:
```json
{
  "tool_name": "web_search",
  "status": "ok",
  "input": { "process_id": "...", "q": "..." },
  "output": { "items": [] },
  "ts": "2026-02-20T12:34:56Z"
}
```

失敗:
```json
{
  "tool_name": "web_search",
  "status": "error",
  "input": { "process_id": "...", "q": "..." },
  "output": { "message": "...", "code": "...", "detail": "..." },
  "ts": "2026-02-20T12:34:56Z"
}
```

### 11.3 truncate仕様
- `N <= 100000`: そのまま
- `N > 100000`: `output` を文字列化して先頭 `M` 文字に切り詰め
- `truncated=true` と `original_length=N` を追加

### 11.4 失敗時挙動
- `blog_memory_append_tool_result` が失敗したらツール全体を失敗とする

---

## 12. 本リポジトリ向け実装ガイド
### 12.1 必須変更
1. `POST /blog/generation/start` で `blog_generation_state.organization_id` を必ず保存する
2. `blog_memory_*` テーブル/RPC/RLS migration追加
3. `backend/app/domains/blog/endpoints.py` にMemory API追加
4. Embedding投入ジョブ追加
5. Blog生成で利用する全Tool（`ask_user_questions`, `wp_*`, `upload_user_image_to_wordpress` を含む）をサーバーコンテキスト注入前提で整合する

### 12.2 重要修正
- `POST /blog/generation/start` の `blog_generation_state` insert時に `organization_id` を保存する
  - サイトが組織サイトなら `wordpress_sites.organization_id`
  - 個人サイトなら NULL（scope_type=user）
- `organization_id` は開始時確定後に更新しない（プロセス固定）
- `web_search` の Memory Autolog は本フェーズでは実装しない（後続タスク）

### 12.3 認可整合
- 既存プロジェクト方針に合わせ、Memory API/RPC呼び出し前にアプリ層で `process_id` 所有チェックを行う。
- チェック不一致時は `FORBIDDEN` を返し、DB書き込みを実行しない。

---

## 13. テスト仕様（受け入れ条件）
### 13.1 API
1. `POST /items` で role=tool_result は 400 `ROLE_TOOL_RESULT_FORBIDDEN`
2. 存在しないprocess_idで 404 `BLOG_PROCESS_NOT_FOUND`
3. `POST /meta/upsert` で upsertされ、`embedding_input=title+"\n\n"+short_summary`
4. `POST /search` で `embedding is null` はヒットしない
5. `include_roles` 指定で itemsがfilterされる

### 13.2 外部ツール（本フェーズ）
1. `web_search(...)` は最新情報取得に利用できる（Memory保存を前提にしない）
2. ツール実行ログは `tool_call_logs/llm_call_logs` で追跡できる
3. `process_id` はサーバーコンテキストから解決され、ツール公開引数に不要

### 13.3 境界
1. orgスコープのユーザーAは同orgのMemoryを検索可能
2. 別orgユーザーは検索不可
3. userスコープ（organization_id NULL）は同一userのみ検索可能

### 13.4 全Tool `process_id` 整合
1. `ask_user_questions` / `wp_*` / `upload_user_image_to_wordpress` は `process_id` を公開引数に持たない
2. サーバーで解決された `process_id` が他ユーザー所有の場合は 403 `FORBIDDEN`
3. 実行中プロセス未設定時は 400 `INVALID_ARGUMENT`

---

## 14. 運用・可観測性
- `tool_call_logs/llm_call_logs`: 監査・コスト可視化
- `blog_memory_items`: 生成文脈再利用（`tool_result` はフェーズ2で追加）
- 障害調査時は `process_id` を軸にログとMemoryを横断確認する

### 14.1 Embedding設定（環境変数）
- Embedding実装は環境変数で調整可能にする（初期値は一般的な設定）。
- 推奨デフォルト:
  - `MEMORY_EMBED_MODEL=text-embedding-3-small`
  - `MEMORY_EMBED_DIM=1536`
  - `MEMORY_EMBED_BATCH_SIZE=100`
  - `MEMORY_EMBED_MAX_RETRIES=5`
  - `MEMORY_EMBED_RETRY_BASE_SEC=1`
- 変更時は `MEMORY_EMBED_DIM` と `vector(N)` の整合を必ず保つ。

---

## 15. 実装可否評価
### 15.1 可
- 既存Blog実装は `process_id` 中心で統一されており、導入しやすい

### 15.2 工数が乗る箇所
- Memory API/RPC と既存Blogフローの統合
- サーバーコンテキスト注入前提でのツール整合
- Embeddingジョブ新設

### 15.3 リスクと対策
- `organization_id` の未設定/不整合
  - start時に `wordpress_sites.organization_id` から必ず設定
- `process_id` コンテキスト欠損
  - サーバー側ガードで 400 を返却
- 大容量レスポンス
  - 100,000文字truncateユーティリティを共通利用
- `web_search` の記録不足
  - 本フェーズは `tool_call_logs/llm_call_logs` で補完し、Autologはフェーズ2で導入

---

## 付録A: 推奨ファイル配置
- `backend/app/domains/blog_memory/`
  - `schemas.py`
  - `endpoints.py`
  - `service.py`
  - `rpc.py`
- `backend/app/domains/blog/services/autolog.py`
  - `build_tool_result_content`
  - `truncate_tool_result_json`
  - `append_tool_result`
- `supabase/migrations/`
  - `xxxxxx_add_blog_memory_tables_rpc_rls.sql`

---

## 付録B: 最低限チェックリスト
1. migration（tables/indexes/rls/rpc/vector）
2. Blog Memory API（items/meta/search）
3. `organization_id` 開始時確定（`/blog/generation/start`）
4. ツールのサーバーコンテキスト注入整合（`ask_user_questions` / `wp_*` / `upload_user_image_to_wordpress`）
5. Embeddingジョブ
6. E2Eテスト（API + scope + tool process_id context validation）
7. （フェーズ2）web_search Autolog（成功/失敗/truncate）
