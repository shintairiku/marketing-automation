# -*- coding: utf-8 -*-
"""
Contact inquiry service
"""
from typing import Optional
from fastapi import HTTPException, status
import logging
from datetime import datetime
import uuid
import httpx

from app.common.database import supabase
from app.core.config import settings
from app.domains.contact.schemas import (
    ContactInquiryCreate,
    ContactInquiryResponse,
    ContactInquiryList,
    ContactInquiryStatusUpdate,
)

logger = logging.getLogger(__name__)


# カテゴリの日本語表示名
CATEGORY_LABELS = {
    "general": "一般的なお問い合わせ",
    "bug_report": "不具合報告",
    "feature_request": "機能要望",
    "billing": "お支払いについて",
    "other": "その他",
}

# ステータスの日本語表示名
STATUS_LABELS = {
    "new": "新規",
    "in_progress": "対応中",
    "resolved": "解決済み",
    "closed": "クローズ",
}


class ContactService:
    """お問い合わせサービス"""

    @staticmethod
    async def create_inquiry(
        data: ContactInquiryCreate,
        user_id: str,
        user_email: str,
        user_name: Optional[str] = None,
    ) -> ContactInquiryResponse:
        """お問い合わせを作成し、通知メールを送信"""
        try:
            inquiry_dict = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "user_email": user_email,
                "user_name": user_name,
                "category": data.category.value,
                "subject": data.subject,
                "message": data.message,
                "status": "new",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            result = supabase.from_("contact_inquiries").insert(inquiry_dict).execute()

            if not result.data:
                raise Exception("Failed to insert inquiry")

            inquiry = ContactInquiryResponse(**result.data[0])
            logger.info(f"Contact inquiry created: {inquiry.id} by user {user_id}")

            # 通知メール送信（非同期、失敗してもお問い合わせ自体は成功）
            await ContactService._send_notification_email(inquiry)

            return inquiry

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create contact inquiry: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="お問い合わせの送信に失敗しました",
            )

    @staticmethod
    async def get_inquiries(
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ContactInquiryList:
        """お問い合わせ一覧を取得（管理者用）"""
        try:
            query = supabase.from_("contact_inquiries").select("*", count="exact")

            if status_filter:
                query = query.eq("status", status_filter)

            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            result = query.execute()

            inquiries = [ContactInquiryResponse(**row) for row in result.data]
            total = result.count if result.count is not None else len(inquiries)

            return ContactInquiryList(inquiries=inquiries, total=total)

        except Exception as e:
            logger.error(f"Failed to get contact inquiries: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="お問い合わせ一覧の取得に失敗しました",
            )

    @staticmethod
    async def get_inquiry_by_id(inquiry_id: str) -> ContactInquiryResponse:
        """お問い合わせ詳細を取得（管理者用）"""
        try:
            result = (
                supabase.from_("contact_inquiries")
                .select("*")
                .eq("id", inquiry_id)
                .single()
                .execute()
            )

            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="お問い合わせが見つかりません",
                )

            return ContactInquiryResponse(**result.data)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get inquiry {inquiry_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="お問い合わせの取得に失敗しました",
            )

    @staticmethod
    async def update_inquiry_status(
        inquiry_id: str,
        data: ContactInquiryStatusUpdate,
    ) -> ContactInquiryResponse:
        """お問い合わせステータスを更新（管理者用）"""
        try:
            update_dict: dict = {
                "status": data.status.value,
                "updated_at": datetime.utcnow().isoformat(),
            }
            if data.admin_notes is not None:
                update_dict["admin_notes"] = data.admin_notes

            result = (
                supabase.from_("contact_inquiries")
                .update(update_dict)
                .eq("id", inquiry_id)
                .execute()
            )

            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="お問い合わせが見つかりません",
                )

            logger.info(f"Inquiry {inquiry_id} status updated to {data.status.value}")
            return ContactInquiryResponse(**result.data[0])

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update inquiry {inquiry_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ステータスの更新に失敗しました",
            )

    @staticmethod
    async def get_user_inquiries(user_id: str) -> ContactInquiryList:
        """ユーザー自身のお問い合わせ一覧を取得"""
        try:
            result = (
                supabase.from_("contact_inquiries")
                .select("*", count="exact")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )

            inquiries = [ContactInquiryResponse(**row) for row in result.data]
            total = result.count if result.count is not None else len(inquiries)

            return ContactInquiryList(inquiries=inquiries, total=total)

        except Exception as e:
            logger.error(f"Failed to get inquiries for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="お問い合わせ履歴の取得に失敗しました",
            )

    @staticmethod
    async def _send_notification_email(inquiry: ContactInquiryResponse) -> None:
        """管理者への通知メールを送信"""
        resend_api_key = getattr(settings, "resend_api_key", "") or ""
        notification_email = getattr(settings, "contact_notification_email", "") or ""

        if not resend_api_key or not notification_email:
            logger.info("Email notification skipped: RESEND_API_KEY or CONTACT_NOTIFICATION_EMAIL not configured")
            return

        category_label = CATEGORY_LABELS.get(inquiry.category, inquiry.category)
        user_display = inquiry.user_name or inquiry.user_email

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {resend_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": f"BlogAI <noreply@{settings.resend_from_domain}>",
                        "to": [notification_email],
                        "subject": f"[お問い合わせ] {inquiry.subject}",
                        "html": (
                            f"<h2>新しいお問い合わせが届きました</h2>"
                            f"<table style='border-collapse:collapse;'>"
                            f"<tr><td style='padding:4px 12px 4px 0;font-weight:bold;'>カテゴリ</td><td>{category_label}</td></tr>"
                            f"<tr><td style='padding:4px 12px 4px 0;font-weight:bold;'>送信者</td><td>{user_display} ({inquiry.user_email})</td></tr>"
                            f"<tr><td style='padding:4px 12px 4px 0;font-weight:bold;'>件名</td><td>{inquiry.subject}</td></tr>"
                            f"</table>"
                            f"<hr style='margin:16px 0;'>"
                            f"<div style='white-space:pre-wrap;'>{inquiry.message}</div>"
                            f"<hr style='margin:16px 0;'>"
                            f"<p style='color:#888;font-size:12px;'>管理画面で確認: {settings.frontend_url}/admin/inquiries</p>"
                        ),
                    },
                )
                if resp.status_code in (200, 201):
                    logger.info(f"Notification email sent for inquiry {inquiry.id}")
                else:
                    logger.warning(
                        f"Failed to send notification email: {resp.status_code} {resp.text}"
                    )
        except Exception as e:
            logger.warning(f"Failed to send notification email for inquiry {inquiry.id}: {e}")
