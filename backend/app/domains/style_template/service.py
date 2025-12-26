# -*- coding: utf-8 -*-
import json
import logging
from urllib.parse import urlparse

from fastapi import HTTPException, status
from openai import OpenAI

from app.core.config import settings
from app.domains.style_template.schemas import AutoStyleTemplateRequest, AutoStyleTemplateResponse

logger = logging.getLogger(__name__)


class StyleTemplateService:
    """スタイルテンプレート用のサービス層"""

    @staticmethod
    async def auto_generate_style_template(
        request: AutoStyleTemplateRequest,
        user_id: str,
    ) -> AutoStyleTemplateResponse:
        try:
            fields = [field for field in request.fields if field]
            requested_fields = ", ".join(fields) if fields else "all"
            host = urlparse(str(request.website_url)).netloc.split(":")[0].strip().lower()
            allowed_domains = []
            if host:
                allowed_domains.append(host)
                if host.startswith("www."):
                    allowed_domains.append(host[4:])

            FIELD_TEXTS = {
                "tone": "- tone: 文章のトーンや調子（丁寧/親しみやすい/フォーマル等）を具体的に記載",
                "style": "- style: 文体（ですます調/だ・である調など）を明示",
                "approach": "- approach: 読者へのアプローチ方針（寄り添う/論理的/説得的など）を記載",
                "vocabulary": "- vocabulary: 語彙や表現の方針（専門用語の扱い、言い回し）を記載",
                "structure": "- structure: 記事構成の指針（見出し構成、流れ）を記載",
                "special_instructions": "- special_instructions: 特別な指示（禁止事項や必須要素など）を記載",
            }

            fields_block = "\n".join(
                FIELD_TEXTS[f] for f in request.fields if f in FIELD_TEXTS
            )

            prompt = f"""
あなたは文章スタイル設計の専門家です。
目的は、過去の記事やブログ、コラムを分析して、記事作成に役立つスタイルテンプレートを作成することです。
指定URLの記事やブログ、コラムを分析し、以下のスタイル設定の項目を補完してください。
以下以外の項目はnullで返してください。

{fields_block}

ルール:
- 対象フィールドのみ出力すること（未指定フィールドは必ずnull）。
- 根拠が不十分な場合は推測せずnullにする。
- トーン/文体/方針は日本語で具体的に記載し、誇張表現は避ける。
- 制限ドメイン内を分析して詳細な情報を返すこと。
""".strip()

            client = OpenAI(api_key=settings.openai_api_key)

            tool_spec = {"type": "web_search"}
            if allowed_domains:
                tool_spec["filters"] = {"allowed_domains": allowed_domains}

            schema = AutoStyleTemplateResponse.model_json_schema()
            if "additionalProperties" not in schema:
                schema["additionalProperties"] = False
            if "properties" in schema:
                schema["required"] = list(schema["properties"].keys())

            response = client.responses.create(
                model=settings.research_model,
                input=prompt,
                instructions=(
                    "必ず web_search ツールを1回以上使い、"
                    "取得した根拠に基づいて AutoStyleTemplateResponse に準拠したJSONのみを出力してください。"
                    "余分なciteturn2view0turn1view0などは削除してください。"
                ),
                tools=[tool_spec],
                tool_choice="required",
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "auto_style_template",
                        "strict": True,
                        "schema": schema,
                    }
                },
            )

            output_text = getattr(response, "output_text", None) or ""
            if not output_text:
                raise ValueError("Empty response from OpenAI Responses API")
            try:
                payload = json.loads(output_text)
            except json.JSONDecodeError as exc:
                logger.error(f"Failed to parse JSON output: {output_text}")
                raise ValueError("Model returned non-JSON output") from exc

            return AutoStyleTemplateResponse(**payload)

        except Exception as e:
            logger.error(f"Failed to auto-generate style template for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="スタイルテンプレートの自動入力に失敗しました"
            )
