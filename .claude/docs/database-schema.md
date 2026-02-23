# Database Tables (Supabase PostgreSQL)

## Core Tables
| Table | 概要 |
|-------|------|
| `users` | ユーザー情報 (RLS: 自身のみ参照/更新) |
| `organizations` | 組織 (id, name, owner_user_id, billing_user_id, stripe_customer_id) |
| `organization_members` | 組織メンバー (role: owner/admin/member) |
| `organization_invitations` | 組織招待 (email, token, status, expires_at) |
| `user_subscriptions` | 個人サブスクリプション (upgraded_to_org_id でチーム移行追跡) |
| `organization_subscriptions` | チームサブスクリプション (Stripe subscription ID = PK) |

## SEO Article Tables
| Table | 概要 |
|-------|------|
| `articles` | 記事本体 (user_id, title, content, status, generation_process_id) |
| `generated_articles_state` | 記事生成の状態管理 (Supabase Realtime対応) |
| `article_generation_flows` | 生成フロー定義 |
| `article_versions` | 記事バージョン履歴 |
| `article_contexts` | 生成コンテキスト (persona, theme, SERP, keywords) |
| `step_snapshots` | ステップスナップショット (チェックポイント復旧用) |
| `article_edit_versions` | AI編集バージョン |
| `article_agent_chat_sessions` | エージェントチャットセッション |

## Company & Style Tables
| Table | 概要 |
|-------|------|
| `company_info` | 会社情報 (name, usp, avoid_terms, target_area, is_default) |
| `style_guide_templates` | 文体テンプレート (tone, formality, sentence_length, heading/list/number_style) |

## Image Tables
| Table | 概要 |
|-------|------|
| `images` | 生成/アップロード画像 (gcs_url, image_type, alt_text, storage_type) |
| `image_placeholders` | 画像プレースホルダ (description_jp, prompt_en, status) |

## Blog Tables
| Table | 概要 |
|-------|------|
| `wordpress_sites` | WordPress接続サイト (site_url, mcp_endpoint, encrypted_credentials) |
| `blog_generation_state` | ブログ生成の状態管理 |
| `blog_agent_trace_events` | エージェント詳細トレースイベント |

## Usage & Plan Tables
| Table | 概要 |
|-------|------|
| `plan_tiers` | プラン定義マスタ (id, name, stripe_price_id, monthly_article_limit, addon_unit_amount, price_amount) |
| `usage_tracking` | 利用量追跡 (user_id, organization_id, billing_period, articles_generated, articles_limit, addon_articles_limit, admin_granted_articles) |
| `usage_logs` | 使用量監査ログ (usage_tracking_id, user_id, generation_process_id) |

## Contact Tables
| Table | 概要 |
|-------|------|
| `contact_inquiries` | お問い合わせ (user_id, category, subject, message, status, admin_note) |

## System Tables
| Table | 概要 |
|-------|------|
| `agent_log_sessions` | エージェントログセッション |
| `agent_execution_logs` | エージェント実行ログ |
| `llm_call_logs` | LLM呼び出しログ |
| `tool_call_logs` | ツール呼び出しログ |
