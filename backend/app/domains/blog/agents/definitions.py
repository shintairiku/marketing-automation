# -*- coding: utf-8 -*-
"""
Blog AI Domain - Agent Definitions

OpenAI Agents SDKを使用したブログ記事生成エージェントの定義
単一エージェント（最小設計）
"""

import logging
from typing import Callable, Awaitable

from agents import Agent, RunContextWrapper

from app.domains.blog.context import BlogContext
from app.domains.blog.agents.tools import (
    get_wordpress_article,
    analyze_site_style,
    upload_media_to_wordpress,
    create_draft_post,
    request_additional_info,
    get_available_images,
)

logger = logging.getLogger(__name__)


# =====================================================
# エージェントプロンプト
# =====================================================

BLOG_WRITER_SYSTEM_PROMPT = """あなたはWordPressブログ記事作成のエキスパートです。
ユーザーが「作りたい記事」の概要と「参考記事URL」を提供するので、
過去記事のトンマナ・スタイル・ブロック構造を参考にしながら、新しい記事を作成します。

## あなたの役割

1. **参考記事の分析**: 提供されたURLからWordPress記事を取得し、構造・スタイル・トーンを分析
2. **サイトスタイルの把握**: 過去記事を分析して、サイト全体のトンマナを理解
3. **情報収集**: 記事作成に必要な追加情報があればユーザーに質問
4. **記事生成**: 参考記事のスタイルを踏襲し、Gutenbergブロック形式で新しい記事を執筆
5. **下書き作成**: WordPressに下書きとして保存

## 重要なルール

- **下書きのみ作成**: 公開（publish）ではなく、必ず下書き（draft）で保存
- **スタイル踏襲**: 参考記事のトーン、文体、ブロック構造を可能な限り再現
- **Gutenbergブロック形式**: WordPress Gutenberg形式で記事を作成
- **画像活用**: ユーザーがアップロードした画像があれば、適切に記事内で使用

## Gutenbergブロック形式の例

```html
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">見出し</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>本文テキスト...</p>
<!-- /wp:paragraph -->

<!-- wp:image {"id":123} -->
<figure class="wp-block-image"><img src="..." alt=""/></figure>
<!-- /wp:image -->

<!-- wp:list -->
<ul>
<li>リスト項目1</li>
<li>リスト項目2</li>
</ul>
<!-- /wp:list -->
```

## 作業フロー

1. まず `get_wordpress_article` で参考記事を取得・分析
2. 必要に応じて `analyze_site_style` でサイト全体のスタイルを把握
3. 追加情報が必要な場合は `request_additional_info` でユーザーに質問
4. 画像がある場合は `get_available_images` で確認し、`upload_media_to_wordpress` でWordPressにアップロード
5. 最後に `create_draft_post` で下書き記事を作成

## 注意事項

- ユーザーの入力を尊重しつつ、SEOとユーザビリティを意識した記事を作成
- 参考記事と全く同じ内容にならないよう、オリジナリティを保つ
- エラーが発生した場合は、ユーザーに分かりやすく状況を説明
"""


async def create_blog_writer_instructions(
    ctx: RunContextWrapper[BlogContext],
    agent: Agent[BlogContext],
) -> str:
    """動的にプロンプトを生成"""
    base_prompt = BLOG_WRITER_SYSTEM_PROMPT

    # ユーザー入力をプロンプトに追加
    user_context = f"""

## 今回のタスク

**ユーザーのリクエスト:**
{ctx.context.user_prompt}
"""

    if ctx.context.reference_url:
        user_context += f"""

**参考記事URL:**
{ctx.context.reference_url}
"""

    # アップロード画像がある場合
    if ctx.context.uploaded_images:
        images_info = "\n".join([
            f"- {img.filename}" + (f" (WordPress ID: {img.wp_media_id})" if img.wp_media_id else "")
            for img in ctx.context.uploaded_images
        ])
        user_context += f"""

**ユーザーがアップロードした画像:**
{images_info}
"""

    # ユーザーの回答がある場合
    if ctx.context.user_answers:
        answers_info = "\n".join([
            f"- {k}: {v}" for k, v in ctx.context.user_answers.items()
        ])
        user_context += f"""

**ユーザーからの追加情報:**
{answers_info}
"""

    return base_prompt + user_context


# =====================================================
# エージェント定義
# =====================================================

blog_writer_agent = Agent[BlogContext](
    name="blog_writer",
    instructions=create_blog_writer_instructions,
    tools=[
        get_wordpress_article,
        analyze_site_style,
        upload_media_to_wordpress,
        create_draft_post,
        request_additional_info,
        get_available_images,
    ],
    # モデルは生成サービスで指定（gpt-5.2）
)
