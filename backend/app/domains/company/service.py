# -*- coding: utf-8 -*-
"""
Company information service using Supabase client
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from openai import OpenAI
from fastapi import HTTPException, status

from app.common.database import supabase
from app.core.config import settings
from app.domains.company.schemas import (
    CompanyInfoCreate, 
    CompanyInfoUpdate, 
    CompanyInfoResponse, 
    CompanyInfoList,
    SetDefaultCompanyRequest,
    AutoCompanyDataRequest,
    AutoCompanyDataResponse
)

logger = logging.getLogger(__name__)

class CompanyService:
    """会社情報サービス（Supabase版）"""

    @staticmethod
    async def create_company(company_data: CompanyInfoCreate, user_id: str) -> CompanyInfoResponse:
        """会社情報を作成"""
        try:
            # 同じユーザーで既存の会社がある場合、新しい会社をデフォルトにする場合は他をデフォルトから外す
            if company_data.is_default:
                await CompanyService._unset_default_companies(user_id)
            
            # 初回作成の場合は自動的にデフォルトに設定
            existing_companies = supabase.from_("company_info").select("id").eq("user_id", user_id).execute()
            if len(existing_companies.data) == 0:
                company_data.is_default = True

            # 新しい会社情報を作成
            company_dict = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "name": company_data.name,
                "website_url": str(company_data.website_url),
                "description": company_data.description,
                "usp": company_data.usp,
                "target_persona": company_data.target_persona,
                "is_default": company_data.is_default,
                "brand_slogan": company_data.brand_slogan,
                "target_keywords": company_data.target_keywords,
                "industry_terms": company_data.industry_terms,
                "avoid_terms": company_data.avoid_terms,
                "popular_articles": company_data.popular_articles,
                "target_area": company_data.target_area,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            result = supabase.from_("company_info").insert(company_dict).execute()
            
            if result.data:
                logger.info(f"Company created successfully: {company_dict['id']} for user {user_id}")
                return CompanyInfoResponse(**result.data[0])
            else:
                raise Exception("Failed to create company")

        except Exception as e:
            logger.error(f"Failed to create company for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="会社情報の作成に失敗しました"
            )

    @staticmethod
    async def get_companies_by_user(user_id: str) -> CompanyInfoList:
        """ユーザーの会社情報一覧を取得"""
        try:
            result = supabase.from_("company_info")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("is_default", desc=True)\
                .order("created_at", desc=True)\
                .execute()

            companies = [CompanyInfoResponse(**company) for company in result.data]

            # デフォルト会社IDを取得
            default_company = next((c for c in companies if c.is_default), None)
            default_company_id = default_company.id if default_company else None

            return CompanyInfoList(
                companies=companies,
                total=len(companies),
                default_company_id=default_company_id
            )

        except Exception as e:
            logger.error(f"Failed to get companies for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="会社情報の取得に失敗しました"
            )

    @staticmethod
    async def get_company_by_id(company_id: str, user_id: str) -> CompanyInfoResponse:
        """特定の会社情報を取得"""
        try:
            result = supabase.from_("company_info")\
                .select("*")\
                .eq("id", company_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="指定された会社情報が見つかりません"
                )

            return CompanyInfoResponse(**result.data)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get company {company_id} for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="会社情報の取得に失敗しました"
            )

    @staticmethod
    async def get_default_company(user_id: str) -> Optional[CompanyInfoResponse]:
        """デフォルト会社情報を取得"""
        try:
            result = supabase.from_("company_info")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("is_default", True)\
                .limit(1)\
                .execute()

            if not result.data:
                return None

            return CompanyInfoResponse(**result.data[0])

        except Exception as e:
            logger.error(f"Failed to get default company for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="デフォルト会社情報の取得に失敗しました"
            )

    @staticmethod
    async def update_company(company_id: str, company_data: CompanyInfoUpdate, user_id: str) -> CompanyInfoResponse:
        """会社情報を更新"""
        try:
            # 会社が存在するかチェック
            existing = supabase.from_("company_info")\
                .select("*")\
                .eq("id", company_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            if not existing.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="指定された会社情報が見つかりません"
                )

            # デフォルト設定が変更される場合
            if company_data.is_default is not None and company_data.is_default != existing.data.get('is_default'):
                if company_data.is_default:
                    # 他の会社のデフォルトを外す
                    await CompanyService._unset_default_companies(user_id)

            # 更新データを準備
            update_data = company_data.dict(exclude_unset=True)
            if 'website_url' in update_data and update_data['website_url']:
                update_data['website_url'] = str(update_data['website_url'])
            
            update_data['updated_at'] = datetime.utcnow().isoformat()

            # 更新実行
            result = supabase.from_("company_info")\
                .update(update_data)\
                .eq("id", company_id)\
                .eq("user_id", user_id)\
                .execute()

            if result.data:
                logger.info(f"Company updated successfully: {company_id} for user {user_id}")
                return CompanyInfoResponse(**result.data[0])
            else:
                raise Exception("Failed to update company")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update company {company_id} for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="会社情報の更新に失敗しました"
            )

    @staticmethod
    async def delete_company(company_id: str, user_id: str) -> bool:
        """会社情報を削除"""
        try:
            # 会社が存在するかチェック
            existing = supabase.from_("company_info")\
                .select("*")\
                .eq("id", company_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            if not existing.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="指定された会社情報が見つかりません"
                )

            # デフォルト会社で他に会社がある場合は削除を拒否
            if existing.data.get('is_default'):
                other_companies = supabase.from_("company_info")\
                    .select("id")\
                    .eq("user_id", user_id)\
                    .neq("id", company_id)\
                    .execute()
                
                if len(other_companies.data) > 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="デフォルト会社は削除できません。先に他の会社をデフォルトに設定してください。"
                    )

            # 削除実行
            supabase.from_("company_info")\
                .delete()\
                .eq("id", company_id)\
                .eq("user_id", user_id)\
                .execute()

            logger.info(f"Company deleted successfully: {company_id} for user {user_id}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete company {company_id} for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="会社情報の削除に失敗しました"
            )

    @staticmethod
    async def set_default_company(request: SetDefaultCompanyRequest, user_id: str) -> CompanyInfoResponse:
        """デフォルト会社を設定"""
        try:
            # 会社が存在するかチェック
            existing = supabase.from_("company_info")\
                .select("*")\
                .eq("id", request.company_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            if not existing.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="指定された会社情報が見つかりません"
                )

            # 他の会社のデフォルトを外す
            await CompanyService._unset_default_companies(user_id)

            # 指定された会社をデフォルトに設定
            result = supabase.from_("company_info")\
                .update({"is_default": True, "updated_at": datetime.utcnow().isoformat()})\
                .eq("id", request.company_id)\
                .eq("user_id", user_id)\
                .execute()

            if result.data:
                logger.info(f"Default company set successfully: {request.company_id} for user {user_id}")
                return CompanyInfoResponse(**result.data[0])
            else:
                raise Exception("Failed to set default company")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to set default company {request.company_id} for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="デフォルト会社の設定に失敗しました"
            )

    @staticmethod
    async def _unset_default_companies(user_id: str):
        """ユーザーの全会社のデフォルト設定を外す"""
        try:
            supabase.from_("company_info")\
                .update({"is_default": False, "updated_at": datetime.utcnow().isoformat()})\
                .eq("user_id", user_id)\
                .eq("is_default", True)\
                .execute()
        except Exception as e:
            logger.error(f"Failed to unset default companies for user {user_id}: {e}")
            raise
    @staticmethod
    async def auto_generate_company_data(request: AutoCompanyDataRequest, user_id: str) -> AutoCompanyDataResponse:
        """会社情報の自動生成"""
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
                "description": "- description: 会社概要、事業内容、実際の活動などをを分析して詳細に説明",
                "usp": "- usp: 競合他社と差別化できる独自の強みを分析して具体的に説明",
                "target_persona": "- target_persona: 年齢、性別、職業、収入、興味関心、課題など対象となる具体的な人物像を分析して詳細に記載",
                "brand_slogan": "- brand_slogan: 指定ドメイン内からブランドスローガンやキャッチフレーズを抽出。見つからない場合はnullを返す",
                "target_keywords": "- target_keywords: 指定ドメイン内の記事やブログ、コラムなどを分析して、記事に含めたい、含めるべきキーワードをカンマ区切りで記載",
                "industry_terms": "- industry_terms: この業界でよく使われる専門用語をカンマ区切りで記載",
                "avoid_terms": "- avoid_terms: 記事に含めたくない、ふくめるべきではない表現をカンマ区切りで記載",
                "popular_articles": "- popular_articles: ドメイン内の記事やブログを分析して、過去の人気記事を（タイトル URL）の形式で記載",
                "target_area": "- target_area: サービス提供エリアや対象地域を具体的に記載"
            }

            fields_block = "\n".join(
                FIELD_TEXTS[f] for f in request.fields if f in FIELD_TEXTS
            )

            prompt = f"""
あなたは企業情報の調査・要約に長けたリサーチャーです。
指定URLの内容を確認し、以下の会社情報の項目を補完してください。
以下以外の項目はnullで返してください。

{fields_block}


ルール:
- 対象フィールドのみ出力すること（未指定フィールドは必ずnull）。
- 根拠が不十分な場合は推測せずnullにする。
- 会社概要/USP/ペルソナは日本語で詳細に記載し、誇張表現は避ける。
- キーワードや用語はカンマ区切りの文字列で返す。
- 制限ドメイン内を分析して詳細な情報を返すこと。
""".strip()

            client = OpenAI(api_key=settings.openai_api_key)
            tool_spec = {"type": "web_search"}
            if allowed_domains:
                tool_spec["filters"] = {"allowed_domains": allowed_domains}

            schema = AutoCompanyDataResponse.model_json_schema()
            if "additionalProperties" not in schema:
                schema["additionalProperties"] = False
            if "properties" in schema:
                schema["required"] = list(schema["properties"].keys())

            response = client.responses.create(
                model=settings.research_model,
                input=prompt,
                instructions=(
                    "必ず web_search ツールを1回以上使い、"
                    "取得した根拠に基づいて AutoCompanyDataResponse に準拠したJSONのみを出力してください。"
                    "余分なciteturn2view0turn1view0などは削除してください。"
                ),
                tools=[tool_spec],
                tool_choice="required",
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "auto_company_data",
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

            return AutoCompanyDataResponse(**payload)

        except Exception as e:
            logger.error(f"Failed to auto-generate company data for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="会社情報の自動生成に失敗しました"
            )
