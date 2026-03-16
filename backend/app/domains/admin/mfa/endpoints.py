# -*- coding: utf-8 -*-
"""
Admin MFA (TOTP) API endpoints
"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.common.admin_auth import get_admin_user_from_token
from app.domains.admin.mfa.schemas import (
    TotpResetResponse,
    TotpSetupConfirmRequest,
    TotpSetupInitResponse,
    TotpStatusResponse,
    TotpVerifyRequest,
    TotpVerifyResponse,
)
from app.domains.admin.mfa.service import mfa_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/mfa", tags=["Admin MFA"])


@router.get("/status", response_model=TotpStatusResponse)
async def get_mfa_status(
    admin_user: dict = Depends(get_admin_user_from_token),
):
    """現在のユーザーの TOTP 設定状態を取得"""
    user_id = admin_user["user_id"]
    return mfa_service.get_status(user_id)


@router.post("/setup/init", response_model=TotpSetupInitResponse)
async def setup_init(
    admin_user: dict = Depends(get_admin_user_from_token),
):
    """
    TOTP セットアップを開始。
    QR コード用の provisioning URI とバックアップコードを返す。
    """
    user_id = admin_user["user_id"]
    email = admin_user.get("email", f"{user_id}@admin")
    return mfa_service.setup_init(user_id, email)


@router.post("/setup/confirm")
async def setup_confirm(
    request: TotpSetupConfirmRequest,
    admin_user: dict = Depends(get_admin_user_from_token),
):
    """
    TOTP セットアップを確認。
    認証アプリに表示されたコードを検証して設定を完了する。
    """
    user_id = admin_user["user_id"]
    mfa_service.setup_confirm(user_id, request.code)
    return {"success": True, "message": "二段階認証の設定が完了しました"}


@router.post("/verify", response_model=TotpVerifyResponse)
async def verify_totp(
    request: TotpVerifyRequest,
    admin_user: dict = Depends(get_admin_user_from_token),
):
    """
    TOTP コードまたはバックアップコードを検証。
    """
    user_id = admin_user["user_id"]
    return mfa_service.verify(user_id, request.code)


@router.post("/reset/{target_user_id}", response_model=TotpResetResponse)
async def reset_totp(
    target_user_id: str,
    admin_user: dict = Depends(get_admin_user_from_token),
):
    """
    指定ユーザーの TOTP をリセット（管理者専用）。
    """
    admin_user_id = admin_user["user_id"]
    if admin_user_id == target_user_id:
        raise HTTPException(
            status_code=400,
            detail="自分自身の TOTP はこのエンドポイントからリセットできません。",
        )
    return mfa_service.reset(admin_user_id, target_user_id)
