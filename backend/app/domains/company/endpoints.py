from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from .service import CompanyService
from .schemas import (
    CompanyInfoCreate, 
    CompanyInfoUpdate, 
    CompanyInfoResponse, 
    CompanyInfoList,
    SetDefaultCompanyRequest
)
from app.common.auth import get_current_user_id_from_token as get_current_user_id

router = APIRouter()

@router.post("/", response_model=CompanyInfoResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    company_data: CompanyInfoCreate,
    current_user_id: str = Depends(get_current_user_id)
):
    """会社情報を作成"""
    return await CompanyService.create_company(company_data, current_user_id)

@router.get("/", response_model=CompanyInfoList)
async def get_companies(
    current_user_id: str = Depends(get_current_user_id)
):
    """ユーザーの会社情報一覧を取得"""
    return await CompanyService.get_companies_by_user(current_user_id)

@router.get("/default", response_model=CompanyInfoResponse)
async def get_default_company(
    current_user_id: str = Depends(get_current_user_id)
):
    """デフォルト会社情報を取得"""
    company = await CompanyService.get_default_company(current_user_id)
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="デフォルト会社が設定されていません"
        )
    
    return company

@router.get("/{company_id}", response_model=CompanyInfoResponse)
async def get_company(
    company_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """特定の会社情報を取得"""
    return await CompanyService.get_company_by_id(company_id, current_user_id)

@router.put("/{company_id}", response_model=CompanyInfoResponse)
async def update_company(
    company_id: str,
    company_data: CompanyInfoUpdate,
    current_user_id: str = Depends(get_current_user_id)
):
    """会社情報を更新"""
    return await CompanyService.update_company(company_id, company_data, current_user_id)

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """会社情報を削除"""
    await CompanyService.delete_company(company_id, current_user_id)

@router.post("/set-default", response_model=CompanyInfoResponse)
async def set_default_company(
    request: SetDefaultCompanyRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """デフォルト会社を設定"""
    return await CompanyService.set_default_company(request, current_user_id)