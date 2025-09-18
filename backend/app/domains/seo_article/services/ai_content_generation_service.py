# -*- coding: utf-8 -*-
"""
AIコンテンツ生成サービス

OpenAI Responses APIを使用して、ユーザー入力（画像、URL、テキスト）から
見出しブロック+テキストブロック、またはテキストブロックのみを生成するサービス
"""

import logging
import base64
from typing import Dict, Any, List, Optional, Union
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
        article_html = input_data.get("article_html", "")

        # 基本プロンプト
        base_prompt = """あなたは高品質なSEO記事を執筆するプロのライターです。
既存記事の特定位置に追加するコンテンツを、記事全体の流れと整合性を保ちながら生成します。

**重要な執筆方針:**
- 既存記事の文脈、トーン、スタイルに合わせる
- 読者にとって価値のある、読みやすく実用的な内容をHTML形式で執筆
- 記事全体の構造と論理的な流れを維持する
"""

        # 記事文脈情報の構築
        context_info = ""
        if article_context:
            context_info = self._build_article_context_info(article_context)

        # 既存記事情報
        article_info = ""
        if article_html:
            article_info = f"""
--- 既存記事の内容 ---
{article_html[:3000]}{'...(省略)' if len(article_html) > 3000 else ''}
"""

        # 挿入位置情報
        position_info = ""
        if insert_position is not None:
            position_info = f"""
--- 挿入位置情報 ---
あなたは記事の**ブロック位置 {insert_position}** に新しいコンテンツを挿入するタスクを担当します。
この位置は既存記事の文脈上、適切で自然な内容である必要があります。
"""

        # 出力形式指定
        output_format = self._build_output_format_instructions(include_heading)

        return f"""{base_prompt}

{context_info}

{article_info}

{position_info}

--- ユーザーリクエスト ---
以下のユーザー入力に基づいて、既存記事に適合するコンテンツを生成してください。
URLが含まれている場合は、Web検索を活用して最新情報を取得してください。

{output_format}

**【最重要】HTML出力について**
- 出力は必ずHTML形式で、`<h2>`, `<h3>`, `<p>` などの適切なHTMLタグを使用
- `<em>` タグ（斜体）は使用禁止 - 代わりに `<strong>` や通常テキストを使用
- JSONやマークダウン形式は絶対に使用しない
- 既存記事のHTMLスタイルに合わせる
"""

    def _build_article_context_info(self, article_context: Dict[str, Any]) -> str:
        """記事文脈情報を構築"""
        context_parts = []

        try:
            # 企業情報
            company = article_context.get("company")
            if company:
                context_parts.append("=== 企業情報 ===")
                context_parts.append(f"企業名: {company.get('name', '')}")
                if company.get('usp'):
                    context_parts.append(f"専門分野: {company.get('usp', '')[:100]}...")
                if company.get('avoid_terms'):
                    context_parts.append(f"避けるべき表現: {company.get('avoid_terms', '')}")

            # スタイルガイド
            style_template = article_context.get("style_template")
            if style_template and style_template.get("settings"):
                settings = style_template["settings"]
                context_parts.append("\n=== スタイルガイド ===")
                if settings.get("tone"):
                    context_parts.append(f"トーン・調子: {settings['tone']}")
                if settings.get("writing_style"):
                    context_parts.append(f"文体: {settings['writing_style']}")

            # SERP分析とキーワード情報
            context_keywords = article_context.get("context_keywords", [])
            if context_keywords and isinstance(context_keywords, list):
                context_parts.append(f"\n=== キーワード情報 ===")
                # Ensure all items are strings
                keyword_strings = [str(kw) for kw in context_keywords[:5] if kw]
                if keyword_strings:
                    context_parts.append(f"対象キーワード: {', '.join(keyword_strings)}")

            # テーマ・ペルソナ情報
            theme = article_context.get("theme")
            persona = article_context.get("persona")
            if theme:
                context_parts.append(f"\n=== テーマ情報 ===")
                # Handle both dict and object types
                theme_title = ""
                if hasattr(theme, 'title'):
                    theme_title = theme.title
                elif isinstance(theme, dict):
                    theme_title = theme.get('title', '')
                context_parts.append(f"テーマ: {theme_title}")
            if persona:
                context_parts.append(f"\n=== 想定読者 ===")
                # Handle both dict and object types
                persona_name = ""
                persona_desc = ""
                if hasattr(persona, 'name') and hasattr(persona, 'description'):
                    persona_name = persona.name or ""
                    persona_desc = persona.description or ""
                elif isinstance(persona, dict):
                    persona_name = persona.get('name', '')
                    persona_desc = persona.get('description', '')
                context_parts.append(f"ペルソナ: {persona_name} - {persona_desc[:100]}...")

        except Exception as e:
            logger.error(f"Error building article context info: {str(e)}")
            logger.exception("Full traceback:")
            return "=== コンテキスト情報取得エラー ==="

        return "\n".join(context_parts) if context_parts else ""

    def _build_output_format_instructions(self, include_heading: bool) -> str:
        """出力形式の指示を構築"""
        if include_heading:
            return """
--- 出力形式 ---
見出し付きコンテンツを生成する場合:

HEADING_LEVEL: [2-6] (H1は記事タイトル用なので避ける)
HEADING_TEXT: [見出しテキスト]
PARAGRAPH_TEXT: [HTMLタグを含む段落コンテンツ]

要件:
- 見出しは既存記事の構造に適した階層レベルを選択
- 段落は詳細で情報豊富な内容
- HTMLタグを適切に使用（<p>, <strong>, <ul>, <li> など）
"""
        else:
            return """
--- 出力形式 ---
段落コンテンツのみを生成する場合:

PARAGRAPH_TEXT: [HTMLタグを含む段落コンテンツ]

要件:
- 情報豊富で読みやすい段落テキスト
- HTMLタグを適切に使用（<p>, <strong>, <ul>, <li> など）
- 既存記事の文脈に自然に溶け込む内容
"""

    def _parse_response(self, response) -> List[Dict[str, Any]]:
        """レスポンスを解析してブロック形式に変換"""
        blocks = []

        try:
            # output_textから内容を取得
            text_content = response.output_text

            # 出力形式に従って解析
            lines = text_content.strip().split('\n')

            current_block = {}

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith('HEADING_LEVEL:'):
                    current_block['type'] = 'heading'
                    level_str = line.replace('HEADING_LEVEL:', '').strip()
                    try:
                        current_block['level'] = int(level_str)
                    except ValueError:
                        current_block['level'] = 2  # デフォルトH2

                elif line.startswith('HEADING_TEXT:'):
                    heading_text = line.replace('HEADING_TEXT:', '').strip()
                    current_block['content'] = heading_text
                    blocks.append(current_block.copy())
                    current_block = {}

                elif line.startswith('PARAGRAPH_TEXT:'):
                    paragraph_text = line.replace('PARAGRAPH_TEXT:', '').strip()
                    blocks.append({
                        'type': 'paragraph',
                        'content': paragraph_text
                    })

            # フォールバック: 構造化された出力が見つからない場合
            if not blocks and text_content:
                blocks.append({
                    'type': 'paragraph',
                    'content': text_content
                })

        except Exception as e:
            logger.error(f"Response parsing failed: {str(e)}")
            # フォールバック
            blocks.append({
                'type': 'paragraph',
                'content': response.output_text if hasattr(response, 'output_text') else "コンテンツ生成に失敗しました"
            })

        return blocks

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
