# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.common.auth import get_current_user_id_from_token as get_current_user_id
from app.common.admin_auth import get_admin_user_email_from_token
from app.infrastructure.clerk_client import clerk_client
from app.domains.contact.schemas import (
    ContactInquiryCreate,
    ContactInquiryResponse,
    ContactInquiryList,
    ContactInquiryStatusUpdate,
)
from app.domains.contact.service import ContactService

router = APIRouter()


def _extract_user_info(user_data: dict) -> tuple[str, Optional[str]]:
    """Clerkユーザーデータからemail, nameを抽出"""
    email = ""
    email_addresses = user_data.get("email_addresses", [])
    if email_addresses:
        primary_id = user_data.get("primary_email_address_id")
        for addr in email_addresses:
            if addr.get("id") == primary_id:
                email = addr.get("email_address", "")
                break
        if not email:
            email = email_addresses[0].get("email_address", "")

    first = user_data.get("first_name") or ""
    last = user_data.get("last_name") or ""
    name = f"{first} {last}".strip() or None
    return email, name


@router.post("/", response_model=ContactInquiryResponse, status_code=201)
async def create_inquiry(
    data: ContactInquiryCreate,
    current_user_id: str = Depends(get_current_user_id),
):
    """お問い合わせを送信"""
    user_data = clerk_client.get_user(current_user_id)
    user_email, user_name = _extract_user_info(user_data or {})

    return await ContactService.create_inquiry(
        data=data,
        user_id=current_user_id,
        user_email=user_email,
        user_name=user_name,
    )


@router.get("/my", response_model=ContactInquiryList)
async def get_my_inquiries(
    current_user_id: str = Depends(get_current_user_id),
):
    """自分のお問い合わせ履歴を取得"""
    return await ContactService.get_user_inquiries(current_user_id)


# --- Admin endpoints ---

@router.get("/admin", response_model=ContactInquiryList)
async def get_all_inquiries(
    status: Optional[str] = Query(None, description="ステータスフィルタ"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _admin_email: str = Depends(get_admin_user_email_from_token),
):
    """お問い合わせ一覧を取得（管理者用）"""
    return await ContactService.get_inquiries(
        status_filter=status,
        limit=limit,
        offset=offset,
    )


@router.get("/admin/{inquiry_id}", response_model=ContactInquiryResponse)
async def get_inquiry_detail(
    inquiry_id: str,
    _admin_email: str = Depends(get_admin_user_email_from_token),
):
    """お問い合わせ詳細を取得（管理者用）"""
    return await ContactService.get_inquiry_by_id(inquiry_id)


@router.patch("/admin/{inquiry_id}/status", response_model=ContactInquiryResponse)
async def update_inquiry_status(
    inquiry_id: str,
    data: ContactInquiryStatusUpdate,
    _admin_email: str = Depends(get_admin_user_email_from_token),
):
    """お問い合わせステータスを更新（管理者用）"""
    return await ContactService.update_inquiry_status(inquiry_id, data)
