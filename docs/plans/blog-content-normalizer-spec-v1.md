# Blog Content Normalizer Spec v1

## 目的

WordPress 取得系ツールの返り値から、LLM にとってノイズになりやすい HTML 断片を落とした **normalized 版ツール** を追加する。

このブランチでは **整形機能の追加だけ** を行う。既存ツールの挙動は変えない。

## このブランチでやること

- `backend/app/domains/blog/agents/tools.py` に正規化関数を追加する
- 既存の取得系ツールは残し、normalized 版を別名で追加する
- `backend/app/domains/blog/agents/definitions.py` に新ツールの説明を追加する
- 正規化関数のテストを追加する

## このブランチでやらないこと

- 既存ツールの削除・置き換え
- `generation_service.py` のフロー変更
- Memory / Usage / Endpoint / Migration の変更
- WordPress MCP サーバー側の返却仕様変更
- normalized 版を agent の既定フローへ強制的に組み込む変更

## 現状の返り値整理

### 共通

- 取得系ツールは最終的にすべて **JSON文字列を返す `str`** である
- 共通呼び出し口は `call_wordpress_mcp_tool(...)` で、MCP の返り値をそのまま文字列で返す

### wrapper 側で shape が確定しているもの

- `wp_get_post_raw_content`
  - デフォルト: `compact=true`, `include_rendered=false`
  - 返り値:
    - `schema`
    - `post_id`
    - `raw`
    - `rendered` は `include_rendered=true` 時のみ
- `wp_get_post_block_structure`
  - デフォルト: `compact=true`
  - 返り値:
    - `schema`
    - `keys`
    - `items`
  - `items` の短キー:
    - `b=blockName`
    - `a=attrs`
    - `i=innerBlocks`
    - `h=innerHTML`

### wrapper 側で素通しのもの

- `wp_get_post_by_url`
- `wp_get_recent_posts`
- `wp_get_posts_by_category`

これらは Python wrapper 側では raw schema を固定していない。正規化版でも、**MCP 生返却の shape はできるだけ維持**する。

## サンプルから確認できたノイズ

### `wp_get_post_raw_content` 系

- 空段落
  - `<p></p>`
  - `<p>　</p>`
- 空の list item
  - `<li></li>`
- `rendered_content` の重い画像属性
  - `loading`
  - `decoding`
  - `width`
  - `height`
  - `srcset`
  - `sizes`
  - `class`
- 末尾の著者ボックス
  - `.c-author`
- `raw_content` 末尾の `acf/author` ブロック

### `wp_get_post_by_url` 系

- ページ固有のヒーロー
  - `.mainVisual02`
- パンくず
  - `#pagePath02`
- フォーム埋め込み
  - `<script>`
  - `.entry`
- バナー導線
  - `.phone`

結論として、v1 は「単なる header 除去」ではなく、**本文以外の明らかなノイズ除去** を行う。

## v1 の追加対象ツール

既存ツールはそのまま残し、以下の normalized 版を追加する。

- `wp_get_posts_by_category_normalized`
- `wp_get_post_block_structure_normalized`
- `wp_get_post_raw_content_normalized`
- `wp_get_recent_posts_normalized`
- `wp_get_post_by_url_normalized`

## 正規化方針

### 1. 共通 HTML 正規化

HTML 文字列に対して共通で以下を行う。

- `<head>`
- `<header>`
- `<script>`
- `<style>`
- 明らかな空段落
- 明らかな空 list item
- 明らかな著者ボックス
- 明らかなパンくず
- 明らかなヒーロー領域
- 明らかなフォーム埋め込み領域
- 明らかなバナー導線

class/id ベースで最初に除去対象とする候補:

- `site-header`
- `global-header`
- `masthead`
- `header-nav`
- `breadcrumb`
- `pagePath`
- `mainVisual`
- `c-author`
- `entry`
- `phone`

### 2. 画像属性の軽量化

`rendered_content` 系では、本文理解に不要な重い属性を落とす。

- `loading`
- `decoding`
- `width`
- `height`
- `srcset`
- `sizes`
- `class`

`src` と `alt` は残す。

### 3. JSON shape は極力維持

v1 では、返却 JSON の shape を大きく作り替えない。

方針:

- 既存ツールが返す上位キーは極力維持する
- **HTML を含むフィールドだけ** 正規化関数に通す
- shape の全面統一は v2 以降で検討する

つまり v1 は、**「返り値を作り直す」のではなく「HTML 部分を掃除する」** 方針で進める。

## ツールごとの返却方針

### `wp_get_post_raw_content_normalized`

既存 `wp_get_post_raw_content` の返却 shape を可能な限り維持する。

方針:

- compact 版をベースにする
- `raw` または `raw_content` に相当する HTML を正規化する
- `rendered` または `rendered_content` がある場合のみ正規化する
- それ以外のキーは極力維持する

### `wp_get_post_block_structure_normalized`

既存 `wp_get_post_block_structure` の compact 版 shape を維持する。

方針:

- `schema`, `keys`, `items` はそのまま維持
- `h=innerHTML` がある場合だけ HTML 正規化を通す
- ブロック構造そのものは変えない

### `wp_get_post_by_url_normalized`

既存 `wp_get_post_by_url` の返却 shape を可能な限り維持する。

方針:

- `raw_content` があれば HTML 正規化を通す
- `rendered_content` があれば HTML 正規化を通す
- `post_id`, `title`, `status`, `permalink`, `acf_fields` などの既存キーは維持する
- `raw_content` を `raw` に変換するような shape の変更は行わない

### `wp_get_recent_posts_normalized`

既存 `wp_get_recent_posts` の返却 shape を維持する。

方針:

- 一覧 item に HTML フィールドが含まれている場合だけ正規化する
- 本文が含まれていない場合は、実質的に素通しになる
- 一覧 item のキー整理や再構成は v1 では行わない

### `wp_get_posts_by_category_normalized`

既存 `wp_get_posts_by_category` の返却 shape を維持する。

方針:

- `wp_get_recent_posts_normalized` と同じく、HTML フィールドがある場合だけ正規化する
- item 構造の再設計は行わない

## 実装上のルール

- 既存ツールの引数・返却は変えない
- 新ツールだけを追加する
- 新ツールは `ALL_WORDPRESS_TOOLS` に追加する
- `definitions.py` では、既存ツールと normalized 版の使い分けを明記する
- 正規化に失敗した場合は、元の MCP 返り値へフォールバックする
- 正規化版でも、上位 JSON の shape はできるだけ変えない

## 正規化の優先順位

1. `wp_get_post_raw_content_normalized`
2. `wp_get_post_by_url_normalized`
3. `wp_get_post_block_structure_normalized`
4. `wp_get_recent_posts_normalized`
5. `wp_get_posts_by_category_normalized`

ただし実装は一括で追加してよい。

## テスト観点

- `<header>` が除去される
- `script/style` が除去される
- `site-header/global-header/masthead/breadcrumb` が除去される
- 空段落と空 list item が除去される
- `.c-author` が除去される
- `img` の重い属性が除去される
- 本文段落と見出しは残る
- 既存ツールの挙動は変わらない
- normalized 版で既存 shape が大きく崩れない

## 実装順

1. `tools.py` に HTML 正規化関数と JSON 正規化関数を追加
2. 5つの normalized 版ツールを追加
3. `ALL_WORDPRESS_TOOLS` に追加
4. `definitions.py` に新ツール説明と使い分けを追加
5. 正規化関数のテストを追加
