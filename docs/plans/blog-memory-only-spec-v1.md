# Blog Memory Only Spec v1

## 1. 目的

`feat/blog-ai-memory` を土台として、テンプレ機能を除いた Blog Memory 機能のみを改修・実装する。

今回の目的は以下の3点に絞る。

1. 過去記事の再利用情報を安定して保存できること
2. 初手の取得を軽くし、必要時だけ詳細を取得できること
3. テンプレなしでも、似た記事の重要事項を再利用して記事品質を上げられること

本仕様ではテンプレ機能は凍結し、Memory 単体で完結する構成にする。

## 2. 前提

- 実装ベースブランチは `feat/blog-ai-memory`
- テンプレ関連機能は今回のスコープ外
- 今回取り込むのは Memory 側の改善のみ
- 実装中の作業ログはリポジトリルートの `progress.md` に追記する
- `progress.md` には作業ごとに以下を残す
  - 対象ファイル
  - 実施内容
  - 問題点 / 未解決事項
  - 次にやること
- 実装中に判断が変わった場合や詰まりが出た場合も、その時点で `progress.md` に追記する

## 3. スコープ

### 3.1 実装対象

- Blog Memory の保存構造見直し
- Blog Memory の検索 API / ツール見直し
- `note` の追加
- `post_type` / `category_ids` を使った絞り込み検索
- `generation_service.py` での保存タイミング整理
- Memory 用 migration / RPC 更新
- Memory 用テスト更新

### 3.2 実装対象外

- `blog_templates` テーブル
- `template_get_candidates`
- `template_get_detail`
- `template_create`
- テンプレ管理画面

## 4. 設計方針

### 4.1 全体方針

Memory は以下の2層で管理する。

1. `blog_memory_meta`
   - 1 process につき 1 行
   - 軽量な検索入口と概要返却に使う
2. `blog_memory_detail`
   - 1 process につき 1 行
   - 可変な詳細情報を `memory_json` にまとめて持つ

### 4.2 目指す挙動

- 初手では `overview` だけを軽く返す
- 足りない時だけ `qa` などを追加取得する
- 記事完成後に、次回再利用用の `note` を毎回保存する
- テンプレがなくても、過去記事の重要事項メモだけで再利用判断できる状態を作る

## 5. データモデル

### 5.1 `blog_memory_meta`

1 process 1 行のメタ情報。

保持項目:
- `process_id`
- `user_id`
- `organization_id`
- `scope_type`
- `draft_post_id`
- `title`
- `summary`
- `embedding_input`
- `embedding`
- `embedding_updated_at`
- `post_type`
- `category_ids`
- `created_at`
- `updated_at`

補足:
- 埋め込み対象は `title + summary`
- `post_type` / `category_ids` は検索絞り込み用に使う

### 5.2 `blog_memory_detail`

1 process 1 行の詳細情報。

保持項目:
- `process_id`
- `user_id`
- `organization_id`
- `scope_type`
- `memory_json`
- `created_at`
- `updated_at`

### 5.3 `memory_json` の標準構造

`memory_json` は `jsonb` で保持し、初期仕様として以下のキーを持つ。

- `user_input`: 初回要求（string or null）
- `qa`: 追加質問回答の配列
- `summary`: 最終 summary（string or null）
- `note`: 次回再利用用の重要事項メモ（string or null）
- `tool_results`: 共通フォーマットのツール結果配列
- `execution_trace`: 実行フローの軽量要約オブジェクト
- `references`: 参照記事や参照URLの配列

例:

```json
{
  "user_input": "高専生向けのAI勉強法セミナー記事を書いてほしい",
  "qa": [
    {
      "question": "画像はどうするか",
      "answer": "画像生成は使わず既存画像を再利用"
    }
  ],
  "summary": "高専生向けのAI勉強法セミナー告知記事を作成...",
  "note": "高専1-2年生向け。初心者向け。画像生成なし。CTAは最後に1回。",
  "tool_results": [
    {
      "tool_name": "wp_get_recent_posts",
      "input": {
        "category_id": 12
      },
      "output_preview": "{\"posts\":[{\"id\":10,\"title\":\"参考記事\"}]}",
      "references": [
        {
          "type": "wp_post",
          "post_id": 10,
          "url": "https://example.com/post/10",
          "title": "参考記事"
        }
      ],
      "captured_at": "2026-03-12T12:00:00+09:00"
    }
  ],
  "execution_trace": {
    "tools": ["wp_get_site_info", "memory_search", "ask_user_questions", "wp_create_draft_post"],
    "flow": ["site_info", "memory_overview", "question", "draft_created"]
  },
  "references": [
    {
      "type": "wp_post",
      "post_id": 10,
      "url": "https://example.com/post/10",
      "title": "参考記事"
    }
  ]
}
```

### 5.4 設計ルール

- `meta` は固定でよく使うものだけ持つ
- `detail.memory_json` は可変な詳細情報をまとめる
- `memory_json` は自由帳にせず、使うキーは仕様で固定する
- 新しいキーを正式に増やす時は仕様書更新を前提とする

## 6. 保存仕様

### 6.1 生データ方針

Memory では以下を基本方針とする。

- 後から再解釈したい raw データは残す
- ノイズになりやすい中間推論や検索結果全文は残さない
- 初手で返すのは軽い `overview` のみとし、raw データは必要時だけ取得する

必須で残すもの:
- `user_input`
- `qa`
- `summary`
- `note`
- `meta.title / summary / post_type / category_ids / draft_post_id`

条件付きで残すもの:
- `tool_results`
- `execution_trace`
- `references`

保存しないもの:
- `memory_search` のヒット全文
- `web_search` の検索結果全文
- 会話履歴全文
- その場限りの中間推論ログ

### 6.2 生成開始時

保存するもの:
- `detail.memory_json.user_input`

### 6.3 追加質問後

保存するもの:
- `detail.memory_json.qa`

方針:
- Q/A の raw データは残す
- ただし初手 overview では raw QA は返さない

### 6.4 ツール実行中

保存するもの:
- 必要な外部ツール結果を共通フォーマットで `detail.memory_json.tool_results` に保存
- 必要に応じて、使用ツール名と大まかな流れを `detail.memory_json.execution_trace` に保存
- 参照した投稿ID / URL / タイトルを `detail.memory_json.references` に保存

保存しないもの:
- `memory_search`
- `web_search`

### 6.5 完了時

保存するもの:
- `detail.memory_json.summary`
- `detail.memory_json.note`
- `blog_memory_meta` の upsert
- 埋め込み更新

## 7. `note` 仕様

### 7.1 生成方法

- エージェントの最終構造化出力に `note` を追加する
- バックエンドが完了時に自動保存する
- 追加ツール呼び出しはさせない
- `note` は最終出力の必須項目とする

### 7.2 内容

`note` には以下のような「再利用価値の高い重要事項」だけを残す。

- 記事のねらい
- ターゲット
- 重視点
- 画像方針
- CTA 方針
- 注意点
- 追加質問で確定した重要事項の要約

禁止:
- 質問と回答の全文ログ
- その場限りの細かすぎる会話ログ
- なくても記事の再利用に影響しない情報

## 8. 検索仕様

### 8.1 検索の入口

`memory_search` はまず `blog_memory_meta` をベクトル検索し、その後必要なら `blog_memory_detail.memory_json` を取得する。

### 8.2 絞り込み優先順位

`post_type` / `category_ids` が分かっている場合、検索フェーズは以下とする。

1. 同一 `post_type` かつ `category_ids` 完全一致
2. 同一 `post_type` かつ `category_ids` の一致数が多い順
3. 同一 `post_type` かつ `category_ids` 一致なし
4. それでも不足する場合のみ全体検索

`post_type` のみ分かっている場合:
- 同一 `post_type`
- その後に全体検索

何も分からない場合:
- 全体検索のみ

`category_ids` の扱い:
- 整数配列として保存する
- 保存時に重複除去する
- 保存時に昇順ソートして正規化する
- 完全一致は正規化後の配列一致で判定する
- 一致数は共通要素数で判定する

### 8.3 埋め込み対象

埋め込み対象は以下とする。

- `title`
- `summary`

埋め込み入力:
- `title + "\n\n" + summary`

### 8.4 返却方針

`memory_search` は意味ベースで返す。

指定可能な `need`:
- `overview`
- `request`
- `qa`
- `tools`
- `trace`
- `references`

デフォルト:
- `need=["overview"]`

### 8.5 `overview` の返却内容

`overview` は以下のみ返す。

- `title`
- `summary`
- `note`

### 8.6 詳細取得

必要時のみ以下を返す。

- `request`: `memory_json.user_input`
- `qa`: `memory_json.qa`
- `tools`: `memory_json.tool_results`
- `trace`: `memory_json.execution_trace`
- `references`: `memory_json.references`

## 9. API / ツール仕様

### 9.1 API

1. `POST /blog/generation/{process_id}/memory/search`
   - request: `query`, `k`, `post_type?`, `category_ids?`, `need?`, `time_window_days`
   - response: `hits[]`

2. `POST /blog/generation/{process_id}/memory/meta/upsert`
   - request: `title`, `summary`, `draft_post_id?`, `post_type?`, `category_ids?`

### 9.2 エージェントツール

公開する Memory ツール:
- `memory_search`

方針:
- `memory_search` は初手で `need=["overview"]`
- 足りない時だけ `qa`, `tools`, `trace`, `references`, `request` を追加取得

## 10. 生成フロー

### 10.1 基本フロー

1. サイト情報を取得
2. 必要に応じて投稿タイプ・カテゴリを取得
3. `memory_search need=["overview"]` を実行
4. overview だけで足りればそのまま執筆
5. 不足があれば `memory_search` の追加取得または `ask_user_questions`
6. 下書き作成
7. 完了時に `summary` / `note` / meta / embedding を保存

追加ルール:
- `ask_user_questions` の前に `note` を確認し、既に確定している内容は再質問しない
- 詳細が必要な時のみ `qa` を追加取得して確認する

### 10.2 廃止するもの

- サーバー側で自動的に Memory 文脈を先に注入する仕組み
- `blog_memory_items` の行積み方式

## 11. DB変更方針

`feat/blog-ai-memory` からの主な変更点:

1. `blog_memory_items` ベースをやめ、`blog_memory_detail(memory_json)` へ変更
2. `blog_memory_meta.short_summary` を `summary` へ統一
3. `blog_memory_meta` に `post_type`, `category_ids`, `created_at` を追加
4. `blog_memory_search_meta` RPC を `post_type`, `category_ids`, `time_window_days` フィルタ対応へ変更
5. 詳細データは `blog_memory_detail.memory_json` へまとめて保存する

## 12. テスト観点

最低限必要なテスト:

1. 初回 `user_input` 保存
2. `qa` 保存
3. `note` 自動保存
4. `memory_search` の `overview` 返却
5. `memory_search` の `need` ごとの返却
6. `post_type/category_ids` による完全一致 → 一致数順 → 一致なし → 全体検索
7. `memory_search` / `web_search` を保存しないこと
8. `blog_memory_detail.memory_json` へのマージ更新が壊れないこと

## 13. 実装順

1. migration / RPC 更新
2. `schemas.py` 更新
3. `memory_service.py` 更新
4. `generation_service.py` 更新
5. `endpoints.py` / `agents/tools.py` 更新
6. `definitions.py` 更新
7. テスト更新

実装中の記録:
- 各ステップの完了時に `progress.md` を更新する
- 変更ファイル、判断理由、問題点は省略せず残す

## 14. 完了条件

以下を満たしたら完了とする。

1. テンプレ機能がなくても Memory 単体で記事再利用が成立する
2. 初手 `overview` が軽く返る
3. 必要時のみ詳細取得できる
4. `note` が毎回保存される
5. `post_type/category_ids` でノイズを減らして検索できる
6. `blog_memory_meta + blog_memory_detail(memory_json)` で無理なく拡張できる
