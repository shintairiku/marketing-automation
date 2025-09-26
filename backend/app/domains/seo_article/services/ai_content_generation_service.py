# -*- coding: utf-8 -*-
"""
AIコンテンツ生成サービス

OpenAI Responses APIを使用して、ユーザー入力（画像、URL、テキスト）から
見出しブロック+テキストブロック、またはテキストブロックのみを生成するサービス
"""

import logging
import base64
import re
from typing import Dict, Any, List, Optional
from openai import OpenAI
from app.core.config import settings
# assemble_edit_knowledge will be imported dynamically to avoid circular imports

logger = logging.getLogger(__name__)


class AIContentGenerationService:
    """AIコンテンツ生成サービス"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.ai_content_generation_model
        self.reasoning_effort = settings.ai_content_generation_reasoning_effort
        self.enable_web_search = settings.ai_content_enable_web_search

    async def generate_content_blocks(
        self,
        input_data: Dict[str, Any],
        user_instruction: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ユーザー入力からコンテンツブロックを生成

        Args:
            input_data: {
                "type": "text" | "image" | "url",
                "content": str,  # テキスト内容またはURL
                "image_data": str,  # base64エンコードされた画像データ（type="image"の場合）
                "include_heading": bool  # 見出しを含めるかどうか
            }
            user_instruction: ユーザーからの追加指示

        Returns:
            {
                "success": bool,
                "blocks": [
                    {
                        "type": "heading" | "paragraph",
                        "level": int,  # headingの場合のみ（1-6）
                        "content": str
                    }
                ],
                "error": str  # エラーの場合のみ
            }
        """
        try:
            # 記事文脈情報を取得（記事IDが提供された場合）
            article_context = None
            if input_data.get("article_id") and user_id:
                try:
                    # Dynamic import to avoid circular dependency
                    from app.domains.seo_article.endpoints import assemble_edit_knowledge
                    article_context = await assemble_edit_knowledge(
                        input_data["article_id"],
                        user_id
                    )
                except Exception as e:
                    logger.warning(f"Failed to get article context: {str(e)}")

            # 入力を構築
            input_messages = self._build_input_messages(input_data, user_instruction)

            # ツール設定
            tools = []
            if self.enable_web_search:
                tools.append({"type": "web_search"})

            # レスポンス生成
            response = self.client.responses.create(
                model=self.model,
                input=input_messages,
                tools=tools if tools else None,
                reasoning={"effort": self.reasoning_effort} if self.model.startswith("gpt-5") else None,
                instructions=self._build_generation_instructions(input_data, article_context)
            )

            # レスポンスを解析
            content_blocks = self._parse_response(response)

            return {
                "success": True,
                "blocks": content_blocks
            }

        except Exception as e:
            logger.error(f"AI content generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _build_input_messages(
        self,
        input_data: Dict[str, Any],
        user_instruction: Optional[str]
    ) -> List[Dict[str, Any]]:
        """入力メッセージを構築"""
        messages = []

        # ユーザー指示をdeveloperメッセージとして追加
        if user_instruction:
            messages.append({
                "role": "developer",
                "content": [{
                    "type": "input_text",
                    "text": user_instruction
                }]
            })

        # メインの入力を構築
        input_type = input_data.get("type", "text")

        if input_type == "text":
            messages.append({
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": input_data.get("content", "")
                }]
            })

        elif input_type == "image":
            image_data = input_data.get("image_data")
            additional_text = input_data.get("content", "")

            content_parts = []
            if additional_text:
                content_parts.append({
                    "type": "input_text",
                    "text": additional_text
                })

            if image_data:
                # Detect image format from base64 data
                media_type = "image/jpeg"  # default
                if image_data.startswith("/9j/"):
                    media_type = "image/jpeg"
                elif image_data.startswith("iVBORw0KGgo"):
                    media_type = "image/png"
                elif image_data.startswith("R0lGOD"):
                    media_type = "image/gif"
                elif image_data.startswith("UklGR"):
                    media_type = "image/webp"

                content_parts.append({
                    "type": "input_image",
                    "image_url": f"data:{media_type};base64,{image_data}"
                })

            if not any(part.get("type") == "input_text" for part in content_parts):
                # Ensure at least one text instruction is sent with the image to satisfy API requirements
                content_parts.insert(0, {
                    "type": "input_text",
                    "text": "添付した画像の内容を読み取り、既存記事に自然に馴染む段落を生成してください。"
                })

            messages.append({
                "role": "user",
                "content": content_parts
            })

        elif input_type == "url":
            url = input_data.get("content", "")
            additional_text = input_data.get("additional_text", "")

            content = f"以下のURLの内容を分析してください: {url}"
            if additional_text:
                content += f"\n\n追加の情報: {additional_text}"

            messages.append({
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": content
                }]
            })

        return messages

    def _build_generation_instructions(self, input_data: Dict[str, Any], article_context: Optional[Dict[str, Any]] = None) -> str:
        """記事文脈を考慮した生成指示を構築"""
        include_heading = input_data.get("include_heading", False)
        insert_position = input_data.get("insert_position")
        try:
            insert_position = int(insert_position) if insert_position is not None else None
        except (ValueError, TypeError):
            insert_position = None
        article_html = input_data.get("article_html", "")

        # 基本プロンプト
        base_prompt = """あなたは高品質なSEOライティングと構造設計に長けたシニアライターです。既存記事の一部に新しいセクションを挿入し、全体構成を崩さず価値ある情報を追加します。

**重要な執筆原則（セクションライティングエージェントの標準に準拠）**
- 記事全体とスタイルガイドを厳密に踏襲する（語り口、フォーマット、禁止事項）
- 想定読者の課題に寄り添い、「結論ファースト → 補足説明 → 重要ポイント再確認」の流れで構成する
- 段落ごとに明確なメッセージと根拠を提示し、冗長な表現を避けて具体例や数値で支える
- SEO上重要なキーワード・関連語を自然に織り込む（不自然な詰め込みは禁止）
- 画像や引用が必要になる場合は文章内でその役割を説明し、既存方針に従う
- 生成物は人間編集者がそのまま貼り付けて利用できる、完成度の高いHTMLフラグメントとする
"""

        # 記事文脈情報の構築
        context_info = ""
        if article_context:
            context_info = self._build_article_context_info(article_context)

        # 既存記事情報
        article_info = ""
        if article_html:
            if insert_position is not None:
                article_info = f"""
--- 既存記事の内容（挿入位置マーキング済み） ---
{self._insert_marker(article_html, insert_position)}
"""
            else:
                article_info = f"""
--- 既存記事の内容 ---
{article_html}
"""

        # 出力形式指定
        output_format = self._build_output_format_instructions(include_heading)

        return f"""{base_prompt}

{context_info}

{article_info}

--- ユーザーリクエスト ---
以下のユーザー入力に基づいて、既存記事に適合するコンテンツを生成してください。
URLが含まれている場合は、Web検索を活用して最新情報を取得してください。

{output_format}

**【最重要】HTML出力について**
- 出力は挿入するHTMLフラグメントそのもののみ（説明文・JSON・コードフェンス・コメントは禁止）
- `<p>` や `<h2>`〜`<h4>` を中心に、既存記事で使用されているタグだけを用いる
- `<em>`（斜体）は使用禁止。強調は `<strong>` を使う
- 句読点・助詞・語尾まで既存記事と同じトーン・文体を徹底する
"""

    def _build_article_context_info(self, article_context: Dict[str, Any]) -> str:
        """記事文脈情報を構築"""
        context_parts: List[str] = []

        try:
            def add_section(title: str, lines: List[str]) -> None:
                filtered = [line for line in lines if line]
                if not filtered:
                    return
                if context_parts:
                    context_parts.append("")
                context_parts.append(f"=== {title} ===")
                context_parts.extend(filtered)

            # 企業情報
            company_lines: List[str] = []
            company = article_context.get("company")
            if company:
                company_lines.append(f"企業名: {company.get('name', '')}")
                if company.get('description'):
                    company_lines.append(f"企業概要: {company.get('description', '')}")
                if company.get('usp'):
                    company_lines.append(f"専門分野・USP: {company.get('usp', '')}")
                if company.get('brand_slogan'):
                    company_lines.append(f"ブランドスローガン: {company.get('brand_slogan', '')}")
                if company.get('target_area'):
                    company_lines.append(f"ターゲット地域: {company.get('target_area', '')}")
                if company.get('avoid_terms'):
                    company_lines.append(f"避けるべき表現: {company.get('avoid_terms', '')}")
                if company.get('website_url'):
                    company_lines.append(f"公式サイトURL: {company.get('website_url', '')}")

            for attr_key, label in [
                ("company_description", "会社概要"),
                ("company_usp", "会社USP"),
                ("company_avoid_terms", "会社 避けるべき表現"),
                ("company_style_guide", "会社 スタイルガイド"),
                ("company_target_area", "会社 ターゲット地域"),
                ("company_website_url", "会社 公式サイト"),
                ("company_brand_slogan", "会社 ブランドスローガン"),
                ("company_target_keywords", "会社 推奨キーワード"),
            ]:
                value = article_context.get(attr_key)
                if not value:
                    continue
                if isinstance(value, (list, tuple)):
                    formatted = ", ".join(str(v) for v in value if v)
                else:
                    formatted = str(value)
                company_lines.append(f"{label}: {formatted}")
            add_section("企業情報", company_lines)

            # スタイルガイド
            style_lines: List[str] = []
            style_template = article_context.get("style_template")
            if style_template and style_template.get("settings"):
                settings = style_template["settings"]
                for key, label in [
                    ("tone", "トーン・調子"),
                    ("writing_style", "文体"),
                    ("approach", "アプローチ"),
                    ("structure", "構成指針"),
                    ("vocabulary", "語彙・表現"),
                    ("special_instructions", "特別な指示"),
                ]:
                    if settings.get(key):
                        style_lines.append(f"{label}: {settings[key]}")

            style_template_settings = article_context.get("style_template_settings")
            if isinstance(style_template_settings, dict):
                for key, value in style_template_settings.items():
                    if value:
                        style_lines.append(f"{key}: {value}")

            if article_context.get("company_style_guide"):
                style_lines.append(f"会社スタイルガイド: {article_context['company_style_guide']}")
            add_section("スタイルガイド", style_lines)

            # キーワード情報
            keyword_strings: List[str] = []
            context_keywords = article_context.get("context_keywords", [])
            if context_keywords and isinstance(context_keywords, list):
                keyword_strings.extend(str(kw) for kw in context_keywords if kw)
            company_keywords = article_context.get("company_target_keywords")
            if isinstance(company_keywords, list):
                keyword_strings.extend(str(kw) for kw in company_keywords if kw)
            elif company_keywords:
                keyword_strings.append(str(company_keywords))
            add_section("キーワード情報", [f"対象キーワード: {', '.join(keyword_strings)}"] if keyword_strings else [])

            # テーマ情報
            theme_lines: List[str] = []
            theme = article_context.get("theme")
            if theme:
                if hasattr(theme, 'title'):
                    theme_lines.append(f"テーマ: {theme.title}")
                elif isinstance(theme, dict):
                    if theme.get('title'):
                        theme_lines.append(f"テーマ: {theme['title']}")
                    if theme.get('description'):
                        theme_lines.append(f"テーマ概要: {theme['description']}")
                    if theme.get('keywords'):
                        theme_lines.append(f"テーマキーワード: {', '.join(theme['keywords'])}")
            add_section("テーマ情報", theme_lines)

            # 想定読者
            persona_lines: List[str] = []
            for persona_candidate in [
                article_context.get("persona"),
                article_context.get("selected_detailed_persona"),
                article_context.get("custom_persona"),
            ]:
                if not persona_candidate:
                    continue
                if hasattr(persona_candidate, 'name') and hasattr(persona_candidate, 'description'):
                    if persona_candidate.name:
                        persona_lines.append(f"ペルソナ名: {persona_candidate.name}")
                    if persona_candidate.description:
                        persona_lines.append(f"読者像の詳細: {persona_candidate.description}")
                elif isinstance(persona_candidate, dict):
                    if persona_candidate.get('name'):
                        persona_lines.append(f"ペルソナ名: {persona_candidate['name']}")
                    if persona_candidate.get('description'):
                        persona_lines.append(f"読者像の詳細: {persona_candidate['description']}")
                    if persona_candidate.get('pain_points'):
                        persona_lines.append(f"読者の悩み: {persona_candidate['pain_points']}")
                    if persona_candidate.get('goals'):
                        persona_lines.append(f"読者の目的: {persona_candidate['goals']}")
            if article_context.get("persona_type"):
                persona_lines.append(f"ペルソナタイプ: {article_context['persona_type']}")
            add_section("想定読者", persona_lines)

            # 参考記事
            reference_lines: List[str] = []
            if article_context.get("company_popular_articles"):
                for item in article_context["company_popular_articles"]:
                    if isinstance(item, dict):
                        title = item.get('title') or item.get('name') or ""
                        url = item.get('url') or item.get('link') or ""
                        summary = item.get('summary') or item.get('description') or ""
                        reference_lines.append(
                            f"・{title} {f'({url})' if url else ''}\n  要約: {summary}".strip()
                        )
                    else:
                        reference_lines.append(f"・{str(item)}")
            add_section("参考となる既存記事", reference_lines)

        except Exception as e:
            logger.error(f"Error building article context info: {str(e)}")
            logger.exception("Full traceback:")
            return "=== コンテキスト情報取得エラー ==="

        return "\n".join(context_parts) if context_parts else ""

    def _build_output_format_instructions(self, include_heading: bool) -> str:
        """出力形式の指示を構築"""
        heading_guidance = "- 必要に応じて冒頭に適切なレベルの<h2>〜<h4>見出しを1つ配置し、直後に導入となる段落を置いてください。" if include_heading else "- 新たな見出しは作成せず、既存セクションの一部として自然につながる段落のみを生成してください。"

        return f"""
--- 出力要件 ---
- 生成するのは挿入用HTMLフラグメントのみで、コメントや余計な説明は一切出力しない
- 各段落は必ず `<p>...</p>` でラップし、文章の中で必要な装飾は `<strong>` や `<a>` など既存記事と揃えたタグを使用する
- 一文目は結論または要点から始め、以降に根拠・詳細・再確認を順序立てて展開する
- 例示・数値・手順など具体的な情報を盛り込み、読者の課題解決に直結させる
- 接続詞や指示語で前後セクションに滑らかにつなぐ
- 箇条書きが必要な場合でも `<ul>` `<ol>` は使用せず、文章で端的に整理する
- 日本語はですます調で統一し、専門用語には補足を添える
- {heading_guidance}
"""

    def _parse_response(self, response) -> List[Dict[str, Any]]:
        """レスポンスを解析してブロック形式に変換"""
        blocks = []

        try:
            html_fragment = (getattr(response, 'output_text', '') or '').strip()
            if not html_fragment:
                return []

            block_pattern = re.compile(r'(<(h[1-6]|p|div|blockquote)[^>]*>.*?</\2>)', re.IGNORECASE | re.DOTALL)

            for match in block_pattern.finditer(html_fragment):
                full_block = match.group(1)
                tag = match.group(2).lower()
                inner = re.sub(rf'^<\s*{tag}[^>]*>|</{tag}\s*>$', '', full_block, flags=re.IGNORECASE | re.DOTALL).strip()

                if tag.startswith('h') and tag[1].isdigit():
                    blocks.append({
                        'type': 'heading',
                        'level': int(tag[1]),
                        'content': inner
                    })
                else:
                    blocks.append({
                        'type': 'paragraph',
                        'content': inner
                    })

            if not blocks:
                blocks.append({
                    'type': 'paragraph',
                    'content': html_fragment
                })

        except Exception as e:
            logger.error(f"Response parsing failed: {str(e)}")
            blocks.append({
                'type': 'paragraph',
                'content': getattr(response, 'output_text', "コンテンツ生成に失敗しました")
            })

        return blocks

    def _insert_marker(self, article_html: str, insert_position: Optional[int]) -> str:
        """挿入位置にマーカーを挿入した記事HTMLを返す"""
        if not article_html or insert_position is None:
            return article_html

        block_pattern = re.compile(r'(<(?:h[1-6]|p|div|section|article|ul|ol|blockquote|pre|figure)[^>]*>.*?</(?:h[1-6]|p|div|section|article|ul|ol|blockquote|pre|figure)>|<img[^>]*?>)', re.IGNORECASE | re.DOTALL)
        matches = list(block_pattern.finditer(article_html))

        marker_html = "<div style=\"background:#f5f5f5; border:1px dashed #999; padding:12px; text-align:center; margin:12px 0;\"><strong>▼▼▼ ここに新しいコンテンツを挿入してください ▼▼▼</strong></div>"

        try:
            insert_index = max(0, int(insert_position))
        except (ValueError, TypeError):
            insert_index = len(matches)

        if not matches:
            return f"{article_html}{marker_html}"

        insert_index = min(insert_index, len(matches))

        if insert_index >= len(matches):
            insert_pos = matches[-1].end()
            return f"{article_html[:insert_pos]}{marker_html}{article_html[insert_pos:]}"

        insert_pos = matches[insert_index].start()
        return f"{article_html[:insert_pos]}{marker_html}{article_html[insert_pos:]}"

    async def generate_content_from_file(
        self,
        file_path: str,
        file_type: str,
        user_instruction: Optional[str] = None,
        include_heading: bool = False,
        user_id: Optional[str] = None,
        article_id: Optional[str] = None,
        insert_position: Optional[int] = None,
        article_html: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ファイルからコンテンツを生成

        Args:
            file_path: ファイルパス
            file_type: ファイルタイプ（image/jpeg, text/plain など）
            user_instruction: ユーザー指示
            include_heading: 見出しを含めるか

        Returns:
            generate_content_blocksと同じ形式
        """
        try:
            if file_type.startswith('image/'):
                # 画像ファイルの場合
                with open(file_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')

                input_data = {
                    "type": "image",
                    "image_data": image_data,
                    "content": user_instruction or "",  # ユーザー指示をcontentに設定
                    "include_heading": include_heading,
                    "article_id": article_id,
                    "insert_position": insert_position,
                    "article_html": article_html
                }

            else:
                # テキストファイルの場合
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                input_data = {
                    "type": "text",
                    "content": content,
                    "include_heading": include_heading,
                    "article_id": article_id,
                    "insert_position": insert_position,
                    "article_html": article_html
                }

            return await self.generate_content_blocks(input_data, None, user_id)  # user_instructionは既にinput_dataに含まれている

        except Exception as e:
            logger.error(f"File content generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
