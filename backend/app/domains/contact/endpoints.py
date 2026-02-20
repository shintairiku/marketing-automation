# -*- coding: utf-8 -*-
from typing import Optional

from fastapi import APIRouter, Depends, status

from app.common.admin_auth import get_admin_user_email_from_token
from app.common.auth import get_current_user_id_from_token as get_current_user_id

from .schemas import (
    ContactInquiryCreate,
    ContactInquiryListResponse,
    ContactInquiryResponse,
    UpdateInquiryStatusRequest,
)
from .service import ContactService

router = APIRouter()


# --- User endpoints ---


@router.post(
    "/",
    response_model=ContactInquiryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_inquiry(
    data: ContactInquiryCreate,
    current_user_id: str = Depends(get_current_user_id),
):
    """お問い合わせを送信"""
    return await ContactService.create_inquiry(data, current_user_id)


@router.get("/mine", response_model=ContactInquiryListResponse)
async def get_my_inquiries(
    current_user_id: str = Depends(get_current_user_id),
):
    """自分のお問い合わせ一覧を取得"""
    return await ContactService.get_user_inquiries(current_user_id)


# --- Admin endpoints ---


@router.get("/admin/list", response_model=ContactInquiryListResponse)
async def get_all_inquiries(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    _admin_email: str = Depends(get_admin_user_email_from_token),
):
    """全お問い合わせ一覧を取得（管理者用）"""
    return await ContactService.get_all_inquiries(status_filter, limit, offset)


@router.get("/admin/{inquiry_id}", response_model=ContactInquiryResponse)
async def get_inquiry_detail(
    inquiry_id: str,
    _admin_email: str = Depends(get_admin_user_email_from_token),
):
    """お問い合わせ詳細を取得（管理者用）"""
    return await ContactService.get_inquiry_by_id(inquiry_id)


@router.patch(
    "/admin/{inquiry_id}/status", response_model=ContactInquiryResponse
)
async def update_inquiry_status(
    inquiry_id: str,
    data: UpdateInquiryStatusRequest,
    _admin_email: str = Depends(get_admin_user_email_from_token),
):
    """お問い合わせステータスを更新（管理者用）"""
    return await ContactService.update_inquiry_status(inquiry_id, data)
