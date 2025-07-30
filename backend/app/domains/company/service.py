# -*- coding: utf-8 -*-
"""
Company information service using Supabase client
"""
from typing import Optional
from fastapi import HTTPException, status
import logging
from datetime import datetime
import uuid

from app.common.database import supabase
from app.domains.company.schemas import (
    CompanyInfoCreate, 
    CompanyInfoUpdate, 
    CompanyInfoResponse, 
    CompanyInfoList,
    SetDefaultCompanyRequest
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