# Blog Company Memory Spec v1

## 目的

ブログ生成時に、毎回ほぼ同じ内容を WordPress ツールや追加質問で取りに行くコストを減らすため、会社共通の文脈メモを DB に保存し、生成開始時に毎回読み込む。

このメモは blog memory のような記事単位の再利用情報ではなく、会社・サイト共通で使う固定寄りの文脈を扱う。

## このブランチでやること

- `company_memory` 機能を追加する
- ブログ生成開始時に `company_memory` を読み込んで入力コンテキストへ差し込む
- 記事完了時に `company_memory` 更新フェーズを設ける前提で仕様を定義する

## このブランチでやらないこと

- 記事タイプ別テンプレート
- `article_strategy_memory`
- ユーザーが明示選択するテンプレ機能
- 分類キーだけで自動的に記事方針を切り替える仕組み
- company memory の管理 UI

理由:
- 同じ `post_type` / カテゴリでも記事の型が複数ありうる
- そこを自動分岐にすると誤誘導しやすい
- 記事戦略やテンプレは別機能として分離した方が安定する

## スコープ単位

v1 の `company_memory` は **organization 単位 / user 単位** で持つ。

ルール:
- `organization_id` がある場合は organization 単位
- `organization_id` がない場合は user 単位
- `scope_type` は `org` / `user`

理由:
- 同じ WordPress サイトを複数回登録できる現状では、`wordpress_site_id` 単位にすると memory が分裂しやすい
- v1 では「同じ会社が複数 WordPress サイトを持つケースは扱わない」と割り切る
- 会社共通メモという目的には org/user スコープの方が自然

## データモデル

### テーブル案

`company_memory`

- `id uuid primary key default gen_random_uuid()`
- `user_id text not null`
- `organization_id uuid null references public.organizations(id) on delete set null`
- `scope_type text not null check (scope_type in ('org', 'user'))`
- `content_json jsonb not null`
- `content_md text null`
- `schema_version integer not null default 1`
- `version integer not null default 1`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`

### 制約

- `unique (organization_id) where scope_type = 'org'`
- `unique (user_id) where scope_type = 'user'`

### 正本

v1 の正本は `content_json` とする。

理由:
- フィールド単位で扱いやすい
- 将来、一部フィールドの変更ロックを導入しやすい
- 生成時に必要な項目だけ抜き出して注入しやすい
- サーバー側で schema validation を行いやすい

### `content_md` の扱い

- `content_md` は nullable で持つ
- v1 では保存必須にしない
- 必要なら `content_json` から表示用・参照用に生成できる補助カラムとする
- v1 の更新正本にはしない

## JSON フォーマット

`content_json` は固定 schema の JSON とする。

### 初期テンプレート

```json
{
  "schema_version": 1,
  "company_name": "",
  "site_name": "",
  "site_url": "",
  "language": "ja",
  "business_summary": "",
  "company_positioning": "",
  "site_positioning": "",
  "core_services": [],
  "strengths": [],
  "target_customers": [],
  "brand_voice": [],
  "avoid_expressions": [],
  "preferred_messages": [],
  "style_rules": [],
  "primary_post_types": [],
  "primary_categories": [],
  "site_operational_notes": []
}
```

Markdown の参考テンプレートは `docs/plans/blog-company-memory-template-v1.md` に置く。
ただし v1 の DB 正本は JSON とする。

### フィールド型

- `company_name`: string
- `site_name`: string
- `site_url`: string
- `language`: string
- `schema_version`: integer
- `business_summary`: string
- `company_positioning`: string
- `site_positioning`: string
- `core_services`: string[]
- `strengths`: string[]
- `target_customers`: string[]
- `brand_voice`: string[]
- `avoid_expressions`: string[]
- `preferred_messages`: string[]
- `style_rules`: string[]
- `primary_post_types`: string[]
- `primary_categories`: string[]
- `site_operational_notes`: string[]

### アプリケーション内の型定義

保存前に `content_json` をアプリケーション側の schema に通し、正規化済みの canonical JSON のみを DB に保存する。

Pydantic イメージ:

```python
class CompanyMemoryContent(BaseModel):
    schema_version: int = 1
    company_name: str = ""
    site_name: str = ""
    site_url: str = ""
    language: str = "ja"
    business_summary: str = ""
    company_positioning: str = ""
    site_positioning: str = ""
    core_services: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    target_customers: list[str] = Field(default_factory=list)
    brand_voice: list[str] = Field(default_factory=list)
    avoid_expressions: list[str] = Field(default_factory=list)
    preferred_messages: list[str] = Field(default_factory=list)
    style_rules: list[str] = Field(default_factory=list)
    primary_post_types: list[str] = Field(default_factory=list)
    primary_categories: list[str] = Field(default_factory=list)
    site_operational_notes: list[str] = Field(default_factory=list)
```

### 正規化して保存する理由

- JSON の shape を常に一定に保つため
- LLM の返した余計なキーや崩れた値をそのまま保存しないため
- 将来 lock や部分表示を入れやすくするため
- 将来 shape を拡張しても、読み込み時互換を持たせやすくするため

### 互換性と拡張方針

- `content_json` はサーバ側 schema を正本とする
- DB 内の生 JSON を各所で直接読まない
- 読み込み時は必ず `normalize_company_memory(raw_json)` を通し、最新 shape に寄せてから使う
- 保存時は必ず schema validation + canonicalize 後の最新 shape だけを書き込む
- shape 変更は基本的に加算的に行う
- キー名変更や削除が必要な場合は、読み込み時 normalize で旧キーを新キーへ吸収する
- 古い row は read 時に互換変換し、次回保存時に自然に最新 shape へ更新する

### `schema_version` の扱い

- `schema_version` は `content_json` の論理 schema バージョンを表す
- v1 の初期値は `1`
- 読み込み時は `schema_version` を見て normalize してよい
- 保存時は常に最新 `schema_version` で書き戻す
- 将来 shape を変更する場合は、互換読み込みルールとセットで更新する

### バリデーション方針

- 未知のキーは保存しない
- 文字列フィールドは `trim` して保存する
- 配列は `string[]` のみ許可する
- 空文字だけの配列要素は除去する
- 重複要素は除去する
- 順序は保持する
- 保存時は Pydantic model に通した後の `model_dump()` 結果だけを DB に保存する
- LLM の返した JSON をそのまま DB に保存しない

### canonicalize ルール

保存直前に以下を行う:

1. schema validation
2. 文字列フィールドの `trim`
3. 配列要素の `trim`
4. 空要素の除去
5. 重複除去
6. 欠損キーの default 補完
7. 最新 `schema_version` の付与
8. `model_dump()` により canonical JSON 化

これにより、更新時の JSON shape を常に一定にする。

### canonicalize 後の差分比較

- `company_memory_update(decision="update", content_json=...)` を受けても、
  canonicalize 後の JSON が現在の `content_json` と完全一致なら保存しない
- この場合は実質 `no_change` として扱う
- `version` は上げない
- デバッグログには「実質 no_change」と出してよい

### 文字量の目安

- `content_json` 全体は、生成時にテキスト化した際に過度に長くならないように保つ
- v1 では厳密な token 計測はしないが、保存時にテキスト化して 8000 文字程度を超える場合は警告または保存拒否を検討する
- まずは運用上 4000〜6000 文字程度を推奨する

### 含める内容

#### 会社情報

- 会社概要
- 主力サービス
- 強み
- 基本ターゲット
- ブランドトーン
- 避けたい表現
- よく使いたい訴求
- 表記ルール

#### サイト運用情報

- サイト名
- サイト URL
- サイトの位置づけ
- 主な投稿タイプ
- 主なカテゴリ
- 運用メモ

### 含めない内容

- 記事タイプ別テンプレート
- 記事タイプ別の細かい戦略
- 直近だけ有効なキャンペーン情報
- 毎回変わる数値や一時情報
- 実在記事 URL 一覧

## ツール代替の考え方

company memory は WordPress ツールの truth source を置き換えるものではない。
静的で変わりにくい情報の初回取得を減らすために使う。

### 代替しやすいもの

- `wp_get_site_info` の一部
  - サイト名
  - サイト URL
  - サイトの基本位置づけ

- `wp_get_post_types` の一部
  - よく使う投稿タイプ
  - 投稿タイプの用途メモ

- `wp_get_categories` の一部
  - 主なカテゴリ
  - カテゴリの意味や使い分け

- `wp_get_article_regulations` の一部
  - 固定的なトーン
  - 表記ルール
  - NG 表現

- `ask_user_questions` の一部
  - 毎回確認していた基本トーン
  - 基本ターゲット
  - よく訴求する価値

### 代替しないもの

- `wp_get_recent_posts`
- `wp_get_post_by_url`
- `wp_get_post_raw_content`
- `wp_get_post_block_structure`
- `wp_get_tags`
- `wp_create_term`
- `wp_create_draft_post`
- `wp_update_post_content`
- `wp_update_post_meta`

理由:
- これらは現在の WordPress 実データそのものだから

## 読み込みタイミング

ブログ生成開始時に現在の process / site から scope を解決し、対応する `company_memory` を読み込む。

### scope 解決方法

- `process_id` に紐づく `blog_generation_state` から
  - `user_id`
  - `organization_id`
  を取得する
- `organization_id` がある場合は `scope_type='org'`
- `organization_id` がない場合は `scope_type='user'`
- その scope に対応する `company_memory` を取得する

### 注入場所

- `backend/app/domains/blog/services/generation_service.py`
- `_build_input_message(...)` で生成する実行時入力コンテキストに追加する

### 注入方法

system prompt に直接埋め込まず、`content_json` をサーバー側で次の 3 形式に整形して、
実行時の入力メッセージに差し込む。

- `会社共通メモ`: 人向けの要約テキスト
- `会社共通メモの現在値（content_json）`: canonical JSON 全体
- `会社共通メモの空欄フィールド`: 未入力キー一覧

理由:
- 固定 prompt を肥大化させない
- サイトごとの差し替えが容易
- 将来の更新や比較がしやすい
- current JSON の shape と空欄が agent から見えるため、初回の sparse memory でも更新判断しやすい

### 注入テキストのルール

- セクション順は固定する
  1. 会社概要
  2. 主力サービス
  3. 強み
  4. 基本ターゲット
  5. ブランドトーン
  6. 避けたい表現
  7. よく使いたい訴求
  8. 表記ルール
  9. サイト運用情報
- 空のフィールド・空配列は出力しない
- 人向けの `会社共通メモ` セクションでは JSON 生文字列を使わない
- 配列は箇条書きに整形する
- サイト運用情報は
  - 主な投稿タイプ
  - 主なカテゴリ
  - 運用メモ
  の順で整形する
- 注入時には次の注意書きを前置する
  - 会社共通メモは補助文脈である
  - 現在のユーザー指示と矛盾する場合はユーザー指示を優先する
  - WordPress の最新状態が必要な場合はツールで再確認する

### current JSON の渡し方

- `会社共通メモの現在値（content_json）` として canonical JSON 全体を code fence 付きで渡す
- `company_memory_update(decision="update", content_json=...)` を呼ぶ時は、この shape を基準に更新後の JSON 全体を返させる
- current JSON は model に現在値の shape と埋まり具合を見せるために渡す

### 空欄フィールドの渡し方

- current JSON から空文字または空配列のフィールド名を抽出し、`会社共通メモの空欄フィールド` として箇条書きで渡す
- 初回や sparse な memory の場合、agent はこの一覧を見て今回の run で再利用価値の高い事実を得たなら `update` を優先する
- 逆に、今回の run で durable な情報が増えていない場合のみ `no_change` を選ぶ

## 更新フロー

v1 では、writer agent が記事作成と同じ文脈の中で company memory 更新要否を判断し、
必要なら最後に `company_memory_update` ツールを呼ぶ前提で設計する。

理由:
- 記事を書いた時の判断文脈をそのまま使えるため
- 何を company memory に反映すべきかを同一 run の中で判断できるため

### 更新の考え方

- 記事の最後の段階で writer agent が更新要否を判断する
- 更新不要なら `company_memory_update(decision="no_change")` を呼ぶ
- 更新が必要なら、更新後の `content_json` 全体を引数に含めて `company_memory_update(decision="update", content_json=...)` を呼ぶ
- ツール側で schema validation / canonicalize / version 付き保存を行う
- update 判断時は、入力に含まれる `会社共通メモの現在値（content_json）` と `会社共通メモの空欄フィールド` を基準にする
- 特に初回の sparse memory では、今回の run から会社・サイト共通で再利用価値がある情報が増えたなら `no_change` ではなく `update` を選ぶ

### `company_memory_update` ツール入力

- `decision`: `"update"` or `"no_change"`
- `content_json`: 更新後の `content_json` 全体（`decision="update"` の時のみ必須）
- `version` は引数に含めない
  - `version` は agent に持たせず、tool 内部の保存処理だけで使う

例:

```json
{
  "decision": "update",
  "content_json": {
    "company_name": "...",
    "site_name": "...",
    "site_url": "...",
    "language": "ja",
    "business_summary": "...",
    "company_positioning": "...",
    "site_positioning": "...",
    "core_services": ["..."],
    "strengths": ["..."],
    "target_customers": ["..."],
    "brand_voice": ["..."],
    "avoid_expressions": ["..."],
    "preferred_messages": ["..."],
    "style_rules": ["..."],
    "primary_post_types": ["..."],
    "primary_categories": ["..."],
    "site_operational_notes": ["..."]
  }
}
```

または:

```json
{
  "decision": "no_change",
  "content_json": null
}
```

### `company_memory_update` ツール返り値

返り値は次のいずれかとする。

- `{"status": "no_change"}`
- `{"status": "saved"}`
- `{"status": "conflict"}`
- `{"status": "validation_error", "message": "..."}`

ルール:
- canonicalize 後に current と完全一致なら `no_change`
- 保存成功時のみ `saved`
- `version` 競合は `conflict`
- schema 不正や必須欠損は `validation_error`

### `company_memory_update` ツールの責務

- `decision` に応じて保存要否を処理する
- `update` の場合は `content_json` を schema に通す
- canonicalize した JSON のみを保存する
- `version` 条件付きで更新する
- 更新失敗時はエラーを返す

### `company_memory_update` ツールの禁止事項

- `content_json` 未指定で `decision="update"` を受け付けない
- schema にないキーを保存しない
- LLM の返した JSON をそのまま保存しない
- 単発記事専用の事情を保存しない
- 一時的なキャンペーン情報を保存しない
- 実在記事 URL 一覧を保存しない
- 記事タイプ別テンプレートや戦略を保存しない
- WordPress の最新実データを推測で上書きしない

### 更新ルール

- 迷う場合は `NO_CHANGE`
- 単発記事専用の事情は保存しない
- 一時的なキャンペーンや時限情報は保存しない
- 記事戦略やテンプレ本文は保存しない
- 会社・サイト共通で再利用価値がある内容のみ反映する

### v1 の更新可能フィールド

v1 では、schema に含まれる全フィールドを更新対象にしてよい。

対象:
- `company_name`
- `site_name`
- `site_url`
- `language`
- `business_summary`
- `company_positioning`
- `site_positioning`
- `core_services`
- `strengths`
- `target_customers`
- `brand_voice`
- `avoid_expressions`
- `preferred_messages`
- `style_rules`
- `primary_post_types`
- `primary_categories`
- `site_operational_notes`

補足:
- 将来は一部フィールドに lock を入れる可能性がある
- ただし v1 では lock 機能を持たせない

### なぜ毎回このフェーズを通すか

- 事前に更新要否を厳密に判定するのが難しいため
- 毎回最後に「更新後 JSON を返す or NO_CHANGE」を判定させる方が安定するため

### v1 の正本更新

- 更新対象は `content_json`
- `content_md` は更新対象にしなくてよい

### tool 実行条件

- ブログ生成フローが最後まで進み、最終出力を返す直前に呼ぶ
- `completed` で終わる run を前提にする
- `error`
- `cancelled`
- `user_input_required`
では呼ばない

## 同時更新対策

複数人や複数実行が同時に company memory を更新する可能性があるため、楽観ロックを採用する。

### 方法

- `version` は agent に持たせず、tool 内部で最新 row を読んだ時に取得する
- 更新時に `where id = ? and version = ?` で更新する
- 成功したら `version = version + 1`

### 衝突時

- 0 件更新なら競合とみなす
- `status="conflict"` として扱う
- 必要なら最新を読み直して再生成する

v1 では自動マージは行わない。

## API / サービスの最小構成

### v1 で必要

- `get_company_memory(user_id, organization_id)`
- `upsert_company_memory(...)`
- `inject_company_memory_to_blog_input(...)`
- `render_company_memory_text(content_json)`
- `company_memory_update(...)` tool

### `company_memory_update` 実行位置

writer agent が最終出力を返す前の最後のツールとして呼ぶ。

順序:
1. 記事生成完了
2. draft 作成結果確定
3. agent が company memory 更新要否を判断
4. `company_memory_update` を呼ぶ
5. `no_change` なら保存なし
6. `update` なら `version` 条件付きで保存
7. 最終 structured output を返す

### 更新失敗時の扱い

- company memory 更新に失敗しても、記事生成自体は成功のままにする
- 失敗は warning ログとして扱う
- validation 失敗
- version 競合
- `company_memory_update` 実行失敗
のいずれでも、本処理をロールバックしない

### デバッグログ

v1 実装時は、company memory 更新の挙動確認のため、`company_memory_update` 実行後にバックエンドログへ `content_json` 全文を出力してよい。

出力対象:
- 更新前 `content_json`
- tool の返り値
- 更新後 `content_json`
- `NO_CHANGE` 判定

補足:
- これはデバッグ用の一時運用であり、後で削除する前提
- 本番運用に残す前提ではない

### v1 では不要

- 管理 UI
- 詳細な履歴 API
- テンプレ選択 API

## 既存 `company_info` との関係

`company_info` は既存の structured な会社情報テーブルとして残す。

`company_memory` はそれとは別で、ブログ生成に毎回差し込むための運用向けメモとする。

### 役割の違い

- `company_info`
  - structured profile
  - 既存の会社情報管理

- `company_memory`
  - 会社共通の生成文脈
  - サイト運用情報を含む
  - ブログ生成時に毎回読む

## 実装配置

v1 では `company_memory` を blog ドメイン内に実装する。

理由:
- 今回の利用先は blog generation のみ
- API/UI をこのブランチでは作らない
- 記事完了後の `company_memory_update` tool も blog の後処理そのもの
- `company_info` ドメインへ寄せると責務が混ざる

### 配置案

- `backend/app/domains/blog/company_memory_schemas.py`
- `backend/app/domains/blog/services/company_memory_service.py`
- `backend/app/domains/blog/services/generation_service.py`

### 各ファイルの責務

#### `company_memory_schemas.py`

- `content_json` の Pydantic schema
- canonicalize 用の型定義
- `normalize_company_memory(raw_json)` の型変換ルール
- `company_memory_update` tool の入出力 schema

#### `company_memory_service.py`

- scope 解決
- `company_memory` の取得
- lazy create
- read 時 normalize
- `content_json` の保存
- write 時 canonicalize
- `render_company_memory_text(content_json)`
- `company_memory_update(...)` tool の保存処理

#### `generation_service.py`

- 生成開始時の読み込み・注入
- lazy create 実行位置の制御
- `company_memory_update` 呼び出し前提の最終フロー制御
- 更新失敗時の warning 処理

## `company_memory_update` ツール方針

v1 の company memory 更新は、writer agent が最後に呼ぶ `company_memory_update` ツールとして実装する。

### 方針

- 記事作成と同じ文脈で更新要否を判断する
- 最後に `company_memory_update` を呼ぶ
- 保存処理自体は tool 側で行う

### 採用理由

- 記事作成時の判断文脈をそのまま使える
- hidden reasoning は外へ取り出せないため、別 LLM より同一 run の方が自然
- 保存時の validation / canonicalize / version 制御は tool 側で一元管理できる

## 生成時の優先順位

ブログ生成時の優先順位は以下とする。

1. 今回のユーザー指示
2. 今回のユーザー回答
3. WordPress ツールで取得した現在の事実
4. company memory
5. エージェントの推論

補足:
- company memory は補助文脈であり、truth source ではない
- 現在のカテゴリや投稿タイプなど、WordPress の現在値が必要な場合はツール結果を優先する

## 初期化ルール

対象 scope に `company_memory` が存在しない場合は、空オブジェクトではなく初期 JSON を作成する。

### lazy create 実行位置

- `generation_service.py` で `_build_input_message(...)` を呼ぶ直前に `get_or_create_company_memory(...)` を実行する
- 取得できた `content_json` を `render_company_memory_text(...)` で整形して入力へ注入する

### 初期化元

優先順位:
1. `wordpress_sites` の `site_name`, `site_url`
2. 現在の生成フロー内ですでに取得済みの `wp_get_site_info` の `name`, `url`, `language`
3. 既存 `company_info` に保存されている `company_name` 相当情報

### 初期化方針

- 初期化時に自動で埋めるのは `site_name`, `site_url`, `language` を基本とする
- `wp_get_site_info` は既に取得済みなら使ってよいが、lazy create のためだけに追加実行しない
- `company_name` は `company_info` など明示ソースがある場合のみ埋める
- `company_name` を `site_name` から推測して埋めない
- その他のフィールドは空文字または空配列で開始する
- 初期化時点では推測で埋めすぎない

## v1 の判断

- 記事戦略やテンプレは持たせない
- 正本は `content_json`
- `content_md` は nullable 補助カラム
- スコープは `organization_id` / `user_id`
- company memory は静的で変わりにくい情報に限定する
- v1 では「同じ会社が複数 WordPress サイトを持つケース」は扱わない
