# 変更履歴: 3ee6258 → HEAD (2026-02-03)

> **比較対象コミット**: `3ee62588f60c6e449e6b95b4959651b9cea896e8` (Clerk JWT署名検証の実装)
> **総コミット数**: 75コミット
> **変更規模**: 132ファイル、+27,714行 / -2,213行

---

# 🎉 新機能かんたんガイド（非技術者向け）

この期間で、BlogAI プラットフォームに大きな機能追加がありました。以下にわかりやすくまとめます。

---

## ✨ 新しくできるようになったこと

### 🤖 Blog AI（ブログ自動生成）

WordPressサイトにAIがブログ記事を自動で書いてくれる新機能です。

#### 基本機能
- ✅ **簡単な指示だけでブログ記事を自動生成** — 「○○についての記事を書いて」と伝えるだけ
- ✅ **WordPressに直接下書き保存** — 生成した記事がそのままWordPressの下書きに
- ✅ **リアルタイムで進捗確認** — AIが今何をしているか画面で見える
- ✅ **画像も一緒にアップロード** — 記事に使う画像を添付できる（最大5枚）

#### AIとの対話機能
- ✅ **AIからの質問に回答できる** — AIが「どんな読者向け？」など質問してくる
- ✅ **質問をスキップして進めることも可能** — 急いでいるときは飛ばせる
- ✅ **画像で回答もできる** — AIの質問に画像をアップロードして答えられる
- ✅ **会話の履歴を保持** — 中断しても続きから再開できる

#### 記事の品質向上機能
- ✅ **参考URLを指定できる** — 「この記事のような感じで」と参考を渡せる
- ✅ **既存記事のスタイルを学習** — サイトの過去記事を分析して文体を合わせる
- ✅ **Web検索で最新情報を調査** — AIがネットで調べて正確な情報を入れる
- ✅ **SEO対策を自動チェック** — 検索エンジンに強い記事を作成
- ✅ **Gutenbergブロック形式** — WordPressの最新エディタに対応

#### WordPress連携
- ✅ **複数サイトを登録可能** — 複数のWordPressサイトを管理
- ✅ **組織でサイトを共有** — チームメンバーと同じサイトを使える
- ✅ **接続テスト機能** — ちゃんと繋がっているか確認できる
- ✅ **かんたん接続** — WordPress管理画面で生成したURLを貼るだけ

#### 生成履歴・管理
- ✅ **過去の生成履歴を一覧表示** — いつ何を作ったか確認できる
- ✅ **進行中の記事がひと目でわかる** — 今動いている生成がすぐ見つかる
- ✅ **エラーが起きても原因がわかる** — 何が問題だったか表示される
- ✅ **生成をキャンセルできる** — 途中でやめたいときに止められる

---

### 📊 利用上限システム

使いすぎを防ぎ、公平に使えるようにする仕組みです。

- ✅ **月間の記事生成数に上限** — プランに応じた上限あり（例：30記事/月）
- ✅ **残り生成可能数がひと目でわかる** — 画面に「残り○記事」と表示
- ✅ **アドオンで上限を追加購入** — 足りなくなったら追加できる
- ✅ **チームプランはメンバー全員で共有** — 組織全体での上限
- ✅ **上限に近づくと警告** — 「あと5記事です」などお知らせ
- ✅ **特権ユーザーは無制限** — 管理者は制限なく使える

---

### 💳 サブスクリプション（課金）の改善

お支払い周りがもっと便利になりました。

#### プラン・料金
- ✅ **個人プラン** — ¥29,800/月で使い放題（上限内）
- ✅ **チームプラン** — ¥29,800/席/月でチームで使える
- ✅ **2〜50席まで柔軟に選択** — チームの人数に合わせて

#### 便利な機能
- ✅ **個人からチームへスムーズにアップグレード** — 途中で変更OK
- ✅ **日割り計算で無駄なし** — 月の途中でも公平に計算
- ✅ **変更前に料金プレビュー** — いくらになるか事前に確認
- ✅ **シート数をいつでも変更** — メンバー増減に対応
- ✅ **アドオン記事の追加購入** — 上限を超えて使いたいとき
- ✅ **Stripeポータルで明細確認** — 過去の請求を確認

#### チーム機能
- ✅ **メンバー招待** — メールで招待してチームに追加
- ✅ **役割管理** — オーナー・管理者・メンバーの3段階
- ✅ **組織でサイト・記事を共有** — チームで協力して運営

---

### 👨‍💼 管理者ダッシュボード

システム管理者向けの分析画面が大幅パワーアップしました。

#### KPI・統計
- ✅ **ユーザー数・有料会員数がひと目でわかる**
- ✅ **月間の記事生成数を確認**
- ✅ **推定月間売上（MRR）を表示**
- ✅ **先月との比較で成長がわかる**

#### グラフ・チャート
- ✅ **30日間の記事生成推移グラフ**
- ✅ **プラン別ユーザー分布の円グラフ**
- ✅ **日別・モデル別のコスト分析**

#### ユーザー管理
- ✅ **全ユーザー一覧** — 登録者を確認
- ✅ **ユーザー詳細** — 使用量・生成履歴を個別に確認
- ✅ **上限に近いユーザーを検出** — 70%以上使っている人がわかる
- ✅ **特権の付与・剥奪** — 管理者権限の管理

#### プラン設定
- ✅ **プランの上限を変更** — 月間30記事→50記事などに変更
- ✅ **アドオン単位の設定** — 1アドオン=何記事かを設定
- ✅ **変更を即時反映** — 全ユーザーに一括適用

#### コスト分析
- ✅ **AI使用コストの詳細分析** — どのくらいお金がかかっているか
- ✅ **記事ごとのコスト確認** — 1記事あたりの費用
- ✅ **モデル別のコスト比較** — どのAIモデルが高いか
- ✅ **キャッシュ効率の確認** — 節約できているか

---

### 🔐 認証・ログイン

ログイン周りがわかりやすくなりました。

- ✅ **認証選択画面を新設** — ログインか新規登録かを選ぶ画面
- ✅ **組織への招待を受けられる** — メールで届いた招待を承諾
- ✅ **複数の招待を一覧表示** — 複数のチームから招待されても対応
- ✅ **自動リダイレクト** — ログイン後は自動でBlog AIの画面へ

---

### 🎨 画面・UIの改善

見た目や使いやすさも向上しました。

- ✅ **日本語フォント（Noto Sans JP）に統一** — 読みやすく
- ✅ **進捗表示のアニメーション** — 待ち時間も楽しく
- ✅ **完了時の演出** — 記事完成時にきれいなアニメーション
- ✅ **サイドバーを整理** — メニューがスッキリ
- ✅ **ファビコンを刷新** — ブラウザタブのアイコンを新しく

---

## 📱 画面ごとの機能一覧

### `/blog/new` — 新規ブログ作成
| 機能 | 説明 |
|------|------|
| WordPressサイト選択 | 複数サイトから選べる |
| プロンプト入力 | AIへの指示を入力（2000文字まで） |
| 参考URL | 参考にしたい記事のURLを指定 |
| 画像添付 | 最大5枚の画像をアップロード |
| 残り記事数表示 | 今月あと何記事作れるか |
| 上限警告 | 上限に達したら通知 |

### `/blog/[processId]` — 生成進捗画面
| 機能 | 説明 |
|------|------|
| リアルタイム進捗バー | 何%完了したかがわかる |
| 現在のステップ表示 | 「参考記事を分析中」など |
| AIの思考過程 | AIが何を考えているか見える |
| 質問への回答 | AIからの質問に答える |
| 画像での回答 | 質問に画像で答えられる |
| 完了後のリンク | WordPressの編集画面へ直接アクセス |

### `/blog/history` — 生成履歴
| 機能 | 説明 |
|------|------|
| 進行中の一覧 | 今動いている生成がわかる |
| 過去の履歴 | 今日・昨日・今週・今月でグループ化 |
| ステータス表示 | 完了・エラー・キャンセルがアイコンで |
| サイト名表示 | どのサイトに投稿したか |
| 画像数表示 | 何枚の画像を使ったか |

### `/settings/billing` — 請求・プラン管理
| 機能 | 説明 |
|------|------|
| 現在のプラン表示 | 今どのプランか |
| 使用量プログレスバー | 今月の使用状況 |
| プラン変更 | 個人↔チームの切り替え |
| シート数変更 | チームの人数を増減 |
| アドオン購入 | 追加の記事枠を購入 |
| 請求履歴 | Stripeで過去の明細確認 |

### `/admin` — 管理者ダッシュボード
| 機能 | 説明 |
|------|------|
| KPIカード | ユーザー数・売上など |
| 生成推移グラフ | 30日間の記事数推移 |
| プラン分布図 | ユーザーのプラン内訳 |
| 最近のアクティビティ | 直近の動き |
| 上限警告リスト | 使いすぎユーザー |

---

## 🔧 技術者向け詳細

以下は技術的な詳細情報です。

---

## 目次

1. [概要サマリー](#概要サマリー)
2. [新規機能: Blog AI ドメイン](#新規機能-blog-ai-ドメイン)
3. [新規機能: 利用上限システム](#新規機能-利用上限システム)
4. [サブスクリプション機能の大幅改修](#サブスクリプション機能の大幅改修)
5. [管理者ダッシュボードの拡張](#管理者ダッシュボードの拡張)
6. [フロントエンド新規ページ](#フロントエンド新規ページ)
7. [データベースマイグレーション](#データベースマイグレーション)
8. [依存関係の更新](#依存関係の更新)
9. [その他の改善](#その他の改善)

---

## 概要サマリー

この期間で追加された主要機能:

| カテゴリ | 機能 | 状態 |
|---------|------|------|
| **Blog AI** | WordPress連携AIブログ生成システム | 🆕 完全新規 |
| **利用上限** | 月間記事生成上限 + アドオン購入 | 🆕 完全新規 |
| **サブスクリプション** | チームプラン、シート変更、日割り計算 | 🔄 大幅改修 |
| **管理者機能** | KPIダッシュボード、プラン管理、コスト分析 | 🔄 大幅拡張 |
| **認証** | 認証選択画面、組織招待受諾 | 🆕 新規 |
| **WordPress連携** | URL貼り付け方式による接続 | 🆕 新規 |

---

## 新規機能: Blog AI ドメイン

### 概要

OpenAI Agents SDK を使用したWordPressブログ記事の自動生成システム。ユーザーのプロンプトから、WordPress下書き投稿までを自動化する。

### アーキテクチャ

```
backend/app/domains/blog/
├── __init__.py
├── agents/
│   ├── definitions.py    # BlogWriter エージェント定義
│   └── tools.py          # 27個のツール定義
├── context.py            # 生成コンテキスト管理
├── endpoints.py          # REST API エンドポイント
├── schemas.py            # Pydantic スキーマ
└── services/
    ├── crypto_service.py         # 認証情報暗号化
    ├── generation_service.py     # 生成フロー管理 (1,609行)
    ├── image_utils.py            # 画像処理ユーティリティ
    └── wordpress_mcp_service.py  # WordPress MCP クライアント
```

### APIエンドポイント

#### WordPress接続管理
| Method | Path | 概要 |
|--------|------|------|
| GET | `/blog/connect/wordpress` | OAuth風リダイレクト（旧方式） |
| POST | `/blog/connect/wordpress` | MCPコールバック登録 |
| POST | `/blog/connect/wordpress/url` | **URL貼り付け方式（新方式）** |
| GET | `/blog/sites` | 接続サイト一覧 |
| DELETE | `/blog/sites/{site_id}` | サイト解除 |
| POST | `/blog/sites/{site_id}/test` | 接続テスト |
| PATCH | `/blog/sites/{site_id}/activate` | アクティブサイト設定 |

#### ブログ生成
| Method | Path | 概要 |
|--------|------|------|
| POST | `/blog/generation/start` | 生成開始（multipart/form-data、画像対応） |
| GET | `/blog/generation/{process_id}` | 生成状態取得 |
| GET | `/blog/generation/{process_id}/events` | アクティビティフィード |
| POST | `/blog/generation/{process_id}/user-input` | ユーザー回答送信 |
| POST | `/blog/generation/{process_id}/cancel` | 生成キャンセル |
| POST | `/blog/generation/{process_id}/upload-image` | 追加画像アップロード |
| GET | `/blog/generation/history` | 生成履歴一覧 |

### エージェント構成

**BlogWriter Agent** (GPT-5.2):
- 5ステップワークフロー: 分析 → 質問 → 生成 → 検証 → 下書き作成
- 最大25ターン
- Reasoning summary 付き（日本語翻訳）

**ツールセット (27個)**:
| カテゴリ | ツール数 | 主なツール |
|---------|---------|-----------|
| ユーザー対話 | 2 | `ask_user_questions`, `web_search` |
| 記事取得 | 6 | `wp_get_posts_by_category`, `wp_get_post_by_url` 等 |
| ブロック分析 | 4 | `wp_extract_used_blocks`, `wp_get_theme_styles` 等 |
| 記事作成 | 3 | `wp_create_draft_post`, `wp_update_post_content` 等 |
| バリデーション | 3 | `wp_validate_block_content`, `wp_check_seo_requirements` 等 |
| メディア | 4 | `wp_upload_media`, `upload_user_image_to_wordpress` 等 |
| タクソノミー | 6 | `wp_get_categories`, `wp_get_tags` 等 |

### 特徴的な実装

1. **マルチモーダル入力**: ユーザー画像をBase64 data URIとしてエージェントに渡す
2. **会話継続**: `previous_response_id` でトークン消費を最適化
3. **Reasoning翻訳**: gpt-5-nano で英語サマリーを日本語に翻訳（111トークン/回）
4. **MCP Protocol**: JSON-RPC 2.0 over HTTP でWordPressと通信
5. **暗号化認証情報**: AES-256-GCM で credentials を暗号化保存

---

## 新規機能: 利用上限システム

### 概要

Blog AI の月間記事生成数を制限し、アドオン購入で上限を拡張可能にするシステム。

### アーキテクチャ

```
backend/app/domains/usage/
├── __init__.py
├── endpoints.py    # /usage/* エンドポイント
├── schemas.py      # UsageInfo, UsageLimitResult 等
└── service.py      # UsageLimitService
```

### データモデル

```sql
-- プラン定義マスタ
plan_tiers (
  id TEXT PRIMARY KEY,           -- 'default', 'pro' 等
  name TEXT,                     -- '個人プラン'
  stripe_price_id TEXT,
  monthly_article_limit INTEGER, -- 30
  addon_unit_amount INTEGER,     -- 20 (アドオン1単位あたりの記事数)
  price_amount INTEGER,          -- 29800 (円)
  display_order INTEGER,
  is_active BOOLEAN
)

-- 利用量追跡（請求期間ごと）
usage_tracking (
  id UUID PRIMARY KEY,
  user_id TEXT,                  -- XOR
  organization_id UUID,          -- XOR (CHECK制約)
  billing_period_start TIMESTAMPTZ,
  billing_period_end TIMESTAMPTZ,
  articles_generated INTEGER,    -- 現在の生成数
  articles_limit INTEGER,        -- 基本上限
  addon_articles_limit INTEGER,  -- アドオン上限
  plan_tier_id TEXT FK
)

-- 監査ログ
usage_logs (
  id UUID PRIMARY KEY,
  usage_tracking_id UUID FK,
  user_id TEXT,
  generation_process_id TEXT,
  created_at TIMESTAMPTZ
)
```

### 上限チェックフロー

```
1. check_can_generate(user_id, org_id)
   ├─ 特権ユーザー (@shintairiku.jp) → 常に許可
   ├─ usage_tracking レコード取得/作成
   └─ articles_generated < total_limit → 許可

2. record_success(user_id, process_id, org_id)
   ├─ PostgreSQL関数 increment_usage_if_allowed() 呼び出し
   │   └─ FOR UPDATE ロックで原子的インクリメント
   └─ usage_logs に監査レコード挿入
```

### APIエンドポイント

| Method | Path | 概要 |
|--------|------|------|
| GET | `/usage/current` | 現在のユーザー使用量 |
| GET | `/usage/admin/stats` | 管理者: 月間統計 |
| GET | `/usage/admin/users` | 管理者: ユーザー別使用量 |

### フロントエンド統合

- `/blog/new`: 残り記事数表示、上限到達時の生成ボタン無効化
- `/settings/billing`: 使用量プログレスバー、アドオン管理UI
- 429レスポンス時のエラーハンドリング

---

## サブスクリプション機能の大幅改修

### 新規APIエンドポイント

| Path | Method | 概要 |
|------|--------|------|
| `/api/subscription/status` | GET | サブスク状態 + usage情報 |
| `/api/subscription/checkout` | POST | Stripe Checkout Session作成 |
| `/api/subscription/upgrade-to-team` | POST | 個人→チームアップグレード |
| `/api/subscription/update-seats` | POST | シート数変更 |
| `/api/subscription/preview-upgrade` | POST | 料金プレビュー |
| `/api/subscription/addon` | POST | アドオン管理 |
| `/api/subscription/portal` | POST | Stripe Customer Portal |
| `/api/subscription/webhook` | POST | Stripe Webhook |

### 主要な改善点

#### 1. 日割り計算対応
- `stripe.invoices.createPreview()` で事前に差額を表示
- `proration_behavior: 'always_invoice'` で即時請求
- 確認モーダルで明細表示後に実行

#### 2. 同一Stripe Customer方式
- 個人→チームで Customer を再利用
- 日割りクレジットが正しく適用される
- `stripe.subscriptions.update()` で quantity 変更

#### 3. チームプラン シート管理
- 2〜50席の範囲で変更可能
- owner/admin のみ変更権限
- 増減両方に対応

#### 4. アドオン機能
- `STRIPE_PRICE_ADDON_ARTICLES` で設定
- 1ユニット = 20記事（設定可能）
- 0〜100ユニットの範囲

#### 5. Webhook処理
- `checkout.session.completed`: サブスク作成
- `customer.subscription.updated`: 状態同期
- `invoice.payment_succeeded`: usage_tracking リセット
- イベント重複排除（stripe_event_id）

### 設計知見

```
【Stripe v18+ 破壊的変更】
- current_period_start/end が Subscription レベルから
  subscription.items.data[0] に移動
- 旧コードは undefined になりフォールバックが発火

【pending_if_incomplete の制限】
- items + metadata の同時更新は不可
- 2回に分けて subscriptions.update() を呼ぶ必要あり
```

---

## 管理者ダッシュボードの拡張

### 新規エンドポイント

| Method | Path | 概要 |
|--------|------|------|
| GET | `/admin/stats/overview` | KPI統計 |
| GET | `/admin/stats/generation-trend` | 記事生成推移（日別） |
| GET | `/admin/stats/subscription-distribution` | プラン別分布 |
| GET | `/admin/activity/recent` | 直近アクティビティ |
| GET | `/admin/usage/users` | ユーザー別使用量 |
| GET | `/admin/usage/blog` | 記事別Usage（コスト分析） |
| GET | `/admin/users/{user_id}/detail` | ユーザー詳細 |
| GET | `/admin/plan-tiers` | プランティア一覧 |
| POST | `/admin/plan-tiers` | ティア作成 |
| PATCH | `/admin/plan-tiers/{tier_id}` | ティア更新 |
| DELETE | `/admin/plan-tiers/{tier_id}` | ティア削除 |
| POST | `/admin/plan-tiers/{tier_id}/apply` | 即時反映 |

### フロントエンドページ

#### `/admin` - メインダッシュボード
- KPIカード4枚（ユーザー数、有料会員、月間記事、MRR）
- AreaChart: 30日記事生成推移
- PieChart: プラン別ユーザー分布
- 直近アクティビティリスト
- 上限に近いユーザー一覧（70%以上）

#### `/admin/blog-usage` - コスト分析
- KPIカード5枚（総コスト、トークン、平均コスト、キャッシュ率、記事数）
- 日別コスト推移チャート
- モデル別コスト配分（ドーナツ）
- ユーザー別コストTop10
- 記事別テーブル（ソート可能）
- 期間フィルタ（7/30/90/全期間）
- モデル料金リファレンス（折りたたみ）

#### `/admin/plans` - プラン管理
- ティアテーブル（CRUD）
- 有効/無効トグル
- 即時反映機能
- 削除時の参照チェック

#### `/admin/users/[userId]` - ユーザー詳細
- 使用量カード
- Blog AI 使用統計
- 生成履歴テーブル
- 組織情報

---

## フロントエンド新規ページ

### Blog AI ページ

#### `/blog/new` - 新規作成
- WordPressサイト選択（個人/組織でグループ化）
- プロンプト入力（最大2000文字）
- 参照URL（オプション）
- 画像アップロード（最大5枚、WebP変換）
- 使用量メーター（上限警告、アドオン誘導）

#### `/blog/[processId]` - 生成進捗
- リアルタイム進捗バー（Supabase Realtime + ポーリングフォールバック）
- アクティビティフィード（ツール呼び出し、思考過程）
- ユーザー入力フォーム（テキスト/画像/セレクト）
- 完了UI（折りたたみバナー、プレビュー/編集ボタン）
- "Quiet Triumph" 遷移アニメーション

#### `/blog/history` - 履歴
- 2ゾーン "Mission Control" デザイン
- Active Zone: SVGプログレスリング
- Past Zone: 日付グループ別リスト
- 自動ポーリング（12秒、アクティブ時のみ）
- Load More ページネーション

### 認証・招待

#### `/auth` - 認証選択
- ログイン/新規登録の選択画面
- ダークグラデーション背景
- 認証済みは `/blog/new` へリダイレクト

#### `/invitation/accept` - 招待受諾
- 自動承諾（単一招待）
- 複数招待リスト表示
- 認証フロー across リダイレクト保持

### 設定

#### `/settings/billing` - 請求&プラン管理
- 旧 `/pricing` を統合
- プラン選択タブ（個人/チーム）
- 使用量表示 + アドオン管理
- アップグレード確認モーダル
- シート変更確認モーダル
- Stripe Portal リンク

#### `/settings/integrations/wordpress` - WordPress連携
- URL貼り付け方式の接続UI
- 接続テストダイアログ
- サイト一覧管理

---

## データベースマイグレーション

### 追加されたマイグレーション (7ファイル)

| ファイル | 概要 |
|---------|------|
| `20260122000000_new_subscription_system.sql` | サブスクリプション基盤 |
| `20260130000001_add_wordpress_sites.sql` | WordPress接続テーブル |
| `20260130000002_add_blog_generation_state.sql` | Blog生成状態テーブル |
| `20260130000003_fix_org_clerk_compat.sql` | Clerk互換性修正 |
| `20260130000004_add_clerk_org_index.sql` | Clerkインデックス追加 |
| `20260201000001_subscription_upgrade_support.sql` | アップグレードサポート |
| `20260202000001_add_usage_limits.sql` | 利用上限システム |

### 新規テーブル

| テーブル | 概要 |
|---------|------|
| `user_subscriptions` | ユーザーサブスクリプション |
| `subscription_events` | Stripeイベント監査ログ |
| `wordpress_sites` | WordPress接続情報（暗号化） |
| `blog_generation_state` | Blog生成状態（Realtime対応） |
| `blog_process_events` | 生成イベントログ |
| `plan_tiers` | プラン定義マスタ |
| `usage_tracking` | 利用量追跡 |
| `usage_logs` | 利用量監査ログ |

### 既存テーブル変更

| テーブル | 追加カラム |
|---------|-----------|
| `organizations` | `billing_user_id` |
| `user_subscriptions` | `upgraded_to_org_id`, `plan_tier_id`, `addon_quantity` |
| `organization_subscriptions` | `plan_tier_id`, `addon_quantity` |
| `organization_members` | `display_name`, `email` |

### PostgreSQL関数

```sql
-- 利用量の原子的インクリメント
increment_usage_if_allowed(p_tracking_id UUID)
  → TABLE(new_count INTEGER, was_allowed BOOLEAN)

-- サブスクアクセス判定
has_active_access(p_user_id TEXT) → BOOLEAN

-- サブスク作成
create_user_subscription_record(p_user_id, p_email)
  → user_subscriptions

-- Stripe同期
update_subscription_from_stripe(...)
  → user_subscriptions
```

---

## 依存関係の更新

### Backend (Python)

| パッケージ | 変更 |
|-----------|------|
| `google-generativeai` | バージョン制約解除 |
| `google-cloud-aiplatform` | バージョン制約解除 |
| `google-cloud-storage` | `<3.0.0` 制約解除 |
| `numpy` | `<2.0.0` 制約解除 |

### Frontend (JavaScript/TypeScript)

| パッケージ | 旧 → 新 | 備考 |
|-----------|---------|------|
| `@clerk/nextjs` | 6.19.3 → 6.37.1 | |
| `@stripe/stripe-js` | 2.4.0 → 8.7.0 | MAJOR |
| `@supabase/ssr` | 0.5.2 → 0.8.0 | MAJOR |
| `stripe` | 18.0.0 → 20.3.0 | MAJOR |
| `react` | 19.2.1 → 19.2.4 | |
| `lucide-react` | 0.474.0 → 0.563.0 | |
| `framer-motion` | 12.16.0 → 12.29.2 | |
| `next-route-handler-pipe` | 1.0.5 → 2.0.0 | MAJOR |
| `@react-email/components` | 0.0.36 → 1.0.6 | MAJOR |
| `@react-email/tailwind` | 1.0.4 → 2.0.3 | MAJOR |

### 新規追加

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| `recharts` | 3.7.0 | 管理者ダッシュボードのチャート |
| `svix` | 1.84.1 | Webhook検証 |

---

## その他の改善

### UI/UX

1. **Favicon正方形化**: 横長ロゴ → slate-900背景の正方形アイコン
2. **フォント変更**: Montserrat → Noto Sans JP
3. **ルートリダイレクト**: LP廃止、`/` → 認証済み: `/blog/new`、未認証: `/auth`
4. **サイドバー整理**: WordPress連携を Settings に集約、不要リンク削除

### 技術的改善

1. **Supabase Realtime + ポーリングフォールバック**: 接続不安定時の自動切り替え
2. **JWT自動リフレッシュ**: Realtime接続時のトークン更新
3. **Framer Motion アニメーション**: 完了遷移、プログレスバー exit 等
4. **ChatMarkdown コンポーネント**: Reasoning summary の Markdown レンダリング

### バグ修正

1. **Stripe v18 period 移動**: `subscription.items.data[0]` から読み取るように修正
2. **ポーリング無限ループ**: `useRef` で依存配列から `history` を除外
3. **ページ初期スクロール**: `min-h-screen` 削除で超過解消
4. **組織メンバー使用量帰属**: `organization_members` フォールバック追加

---

## コミット一覧（主要なもの）

```
58a65c3 Revamp Admin Blog Usage Dashboard with Enhanced Cost Analysis and Filtering
771769e Enhance Reasoning Summary and Blog UI with Japanese Translation and Animation Improvements
19858a9 Enhance BlogProcessPage with Completion Detection and Animated UI
5425562 Add WebSearchTool to Blog AI Agent for Enhanced Research Capabilities
c28d1ee Implement WordPress connection via URL input method
f7ca080 Redesign Blog History page and optimize Activity Feed height
4f58ed6 Implement image upload functionality for Blog AI
4715741 Implement multi-tier plan management and enhance subscription handling
78b7ae2 Implement usage limits and enhance admin dashboard features
8d7dfe8 Update dependencies and refactor Stripe integration
8e6f05b Enhance subscription management with seat change functionality
34f1153 Refactor subscription management and upgrade process
b1f8a88 Update font configuration and enhance route handling
1ee012c Merge pull request #100 - Blog AI WordPress
```

---

*生成日時: 2026-02-03*
