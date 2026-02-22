# Backend API Endpoints

## SEO Article (`/articles`)
| Method | Path | 概要 |
|--------|------|------|
| GET | `/articles/` | 記事一覧 (ページネーション・フィルタ) |
| GET | `/articles/{article_id}` | 記事詳細 |
| PATCH | `/articles/{article_id}` | 記事更新 (title, content, keywords, status) |
| PATCH | `/articles/{article_id}/status` | 公開ステータス更新 |
| POST | `/articles/{article_id}/ai-edit` | AIブロック編集 |
| POST | `/articles/generation/start` | 記事生成開始 |
| GET | `/articles/generation/{process_id}` | 生成状態取得 |
| POST | `/articles/generation/{process_id}/resume` | 生成再開 |
| POST | `/articles/generation/{process_id}/user-input` | ユーザー入力送信 |
| POST | `/articles/generation/{process_id}/pause` | 生成一時停止 |
| DELETE | `/articles/generation/{process_id}` | 生成キャンセル |
| GET | `/articles/generation/{process_id}/events` | 生成イベント取得 |
| GET | `/articles/all-processes` | 全プロセス一覧 |
| GET | `/articles/recoverable-processes` | 復旧可能プロセス |
| GET | `/articles/generation/{process_id}/realtime-info` | リアルタイム情報 |
| GET | `/articles/generation/{process_id}/snapshots` | スナップショット一覧 |
| POST | `/articles/flows/` | フロー作成 |
| GET | `/articles/flows/` | フロー一覧 |
| GET | `/articles/flows/{flow_id}` | フロー詳細 |
| PUT | `/articles/flows/{flow_id}` | フロー更新 |
| DELETE | `/articles/flows/{flow_id}` | フロー削除 |
| POST | `/articles/flows/{flow_id}/execute` | フロー実行 |
| GET | `/articles/flows/templates/` | フローテンプレート一覧 |
| POST | `/articles/flows/templates/{template_id}/copy` | テンプレートコピー |
| POST | `/articles/ai-content-generation` | AIコンテンツ生成 (Responses API) |
| POST | `/articles/ai-content-generation/upload` | ユーザーコンテンツアップロード処理 |

## Blog AI (`/blog`)
| Method | Path | 概要 |
|--------|------|------|
| POST | `/blog/connect/wordpress/url` | 接続URL方式でWordPress登録 |
| POST | `/blog/connect/wordpress` | WordPressサイト登録 (MCP callback) |
| POST | `/blog/sites/register` | コードによるWordPress手動登録 |
| DELETE | `/blog/sites/{site_id}` | サイト解除 |
| PATCH | `/blog/sites/{site_id}/organization` | サイト組織変更 |
| GET | `/blog/sites` | 接続サイト一覧 |
| GET | `/blog/sites/{site_id}` | サイト詳細 |
| POST | `/blog/sites/{site_id}/test-connection` | 接続テスト |
| POST | `/blog/generation/start` | ブログ生成開始 (multipart/form-data) |
| GET | `/blog/generation/{process_id}` | 生成状態取得 |
| POST | `/blog/generation/{process_id}/user-input` | ユーザー入力 |
| POST | `/blog/generation/{process_id}/pause` | 生成一時停止 |
| DELETE | `/blog/generation/{process_id}` | 生成キャンセル |
| POST | `/blog/ai-questions` | AI質問生成 |
| POST | `/blog/user-answers` | 回答送信→生成開始 |
| GET | `/blog/generation-history` | 生成履歴 |
| POST | `/blog/upload-image` | 画像アップロード |

## Organization (`/organizations`)
| Method | Path | 概要 |
|--------|------|------|
| POST | `/organizations/` | 組織作成 (ユーザーがowner) |
| GET | `/organizations/` | ユーザーの組織一覧 |
| GET | `/organizations/{id}` | 組織詳細 |
| PUT | `/organizations/{id}` | 組織更新 (owner/adminのみ) |
| DELETE | `/organizations/{id}` | 組織削除 (ownerのみ) |
| GET | `/organizations/{id}/members` | メンバー一覧 |
| PUT | `/organizations/{id}/members/{uid}/role` | ロール変更 |
| DELETE | `/organizations/{id}/members/{uid}` | メンバー削除 |
| POST | `/organizations/{id}/invitations` | 招待送信 (メールベース) |
| GET | `/organizations/invitations` | 受信招待一覧 |
| POST | `/organizations/invitations/respond` | 招待承諾/辞退 |
| GET | `/organizations/{id}/subscription` | サブスクリプション情報 |

## Company (`/companies`)
| Method | Path | 概要 |
|--------|------|------|
| POST | `/companies/` | 会社情報作成 |
| GET | `/companies/` | 会社情報一覧 |
| GET | `/companies/default` | デフォルト会社 |
| GET | `/companies/{id}` | 会社詳細 |
| PUT | `/companies/{id}` | 会社更新 |
| DELETE | `/companies/{id}` | 会社削除 |
| POST | `/companies/set-default` | デフォルト設定 |

## Style Template (`/style-templates`)
| Method | Path | 概要 |
|--------|------|------|
| GET | `/style-templates/` | テンプレート一覧 |
| GET | `/style-templates/{id}` | テンプレート詳細 |
| POST | `/style-templates/` | テンプレート作成 |
| PUT | `/style-templates/{id}` | テンプレート更新 |
| DELETE | `/style-templates/{id}` | テンプレート削除 (論理削除) |
| POST | `/style-templates/{id}/set-default` | デフォルト設定 |

## Image Generation (`/images`)
| Method | Path | 概要 |
|--------|------|------|
| POST | `/images/generate` | Imagen-4画像生成 |
| POST | `/images/generate-and-link` | 生成+プレースホルダリンク |
| POST | `/images/generate-from-placeholder` | プレースホルダから生成 |
| POST | `/images/upload` | GCSアップロード |
| POST | `/images/replace-placeholder` | プレースホルダ置換 |
| POST | `/images/restore-placeholder` | プレースホルダ復元 |
| GET | `/images/serve/{filename}` | ローカル画像配信 |
| GET | `/images/article-images/{article_id}` | 記事画像一覧 |
| GET | `/images/placeholder-history/{article_id}/{placeholder_id}` | プレースホルダ履歴 |

## Admin (`/admin`)
| Method | Path | 概要 |
|--------|------|------|
| GET | `/admin/users` | 全ユーザー一覧 (@shintairiku.jp限定) |
| GET | `/admin/users/{user_id}` | ユーザー詳細 |
| PATCH | `/admin/users/{user_id}/privilege` | 特権フラグ変更 |
| PATCH | `/admin/users/{user_id}/subscription` | サブスクリプション変更 |
| POST | `/admin/users/{user_id}/grant-articles` | 記事付与 |
| GET | `/admin/stats/overview` | ダッシュボードKPI統計 |
| GET | `/admin/stats/generation-trend` | 記事生成日別推移 |
| GET | `/admin/stats/subscription-distribution` | プラン別ユーザー分布 |
| GET | `/admin/activity/recent` | 直近アクティビティ |
| GET | `/admin/usage/users` | ユーザー別使用量一覧 |
| GET | `/admin/usage/blog` | Blog AI プロセス別Usage一覧 |
| GET | `/admin/usage/blog/{process_id}/trace` | プロセス詳細トレース |
| GET | `/admin/plan-tiers` | 全ティア一覧 |
| POST | `/admin/plan-tiers` | 新規ティア作成 |
| PATCH | `/admin/plan-tiers/{tier_id}` | ティア更新 |
| DELETE | `/admin/plan-tiers/{tier_id}` | ティア削除 |
| POST | `/admin/plan-tiers/{tier_id}/apply` | 全アクティブユーザーに即時反映 |

## Contact (`/contact`)
| Method | Path | 概要 |
|--------|------|------|
| POST | `/contact/` | お問い合わせ送信 |
| GET | `/contact/mine` | 自分のお問い合わせ一覧 |
| GET | `/contact/admin/list` | 管理者用全お問い合わせ一覧 |
| GET | `/contact/admin/{id}` | お問い合わせ詳細 |
| PATCH | `/contact/admin/{id}/status` | ステータス更新 |

## Usage (`/usage`)
| Method | Path | 概要 |
|--------|------|------|
| GET | `/usage/current` | 現在のユーザー使用量 |
| GET | `/usage/admin/stats` | 管理者用使用量統計 |
| GET | `/usage/admin/users` | 管理者用ユーザー別使用量 |

## Health
| Method | Path | 概要 |
|--------|------|------|
| GET | `/` | APIルート (稼働確認) |
| GET | `/health` | ヘルスチェック |
