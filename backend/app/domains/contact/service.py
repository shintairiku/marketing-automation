# -*- coding: utf-8 -*-
"""
Contact inquiry service
"""
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

import resend
from fastapi import HTTPException, status

from app.common.database import supabase
from app.core.config import settings
from app.domains.contact.schemas import (
    ContactInquiryCreate,
    ContactInquiryListResponse,
    ContactInquiryResponse,
    UpdateInquiryStatusRequest,
)

logger = logging.getLogger(__name__)

# Category display names
CATEGORY_LABELS = {
    "general": "一般的なお問い合わせ",
    "bug_report": "不具合の報告",
    "feature_request": "機能リクエスト",
    "billing": "請求・お支払い",
    "account": "アカウント関連",
    "other": "その他",
}


class ContactService:
    """お問い合わせサービス"""

    @staticmethod
    async def create_inquiry(
        data: ContactInquiryCreate, user_id: str
    ) -> ContactInquiryResponse:
        """お問い合わせを作成し、通知メールを送信"""
        try:
            inquiry_dict = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "name": data.name,
                "email": data.email,
                "category": data.category.value,
                "subject": data.subject,
                "message": data.message,
                "status": "new",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            result = (
                supabase.from_("contact_inquiries").insert(inquiry_dict).execute()
            )

            if not result.data:
                raise Exception("Failed to insert inquiry")

            inquiry = ContactInquiryResponse(**result.data[0])

            # Send notification email in background (don't block the response)
            asyncio.create_task(_send_notification_email(inquiry))

            logger.info(
                f"Contact inquiry created: {inquiry.id} by user {user_id}"
            )
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
    async def get_user_inquiries(user_id: str) -> ContactInquiryListResponse:
        """ユーザー自身のお問い合わせ一覧を取得"""
        try:
            result = (
                supabase.from_("contact_inquiries")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )

            inquiries = [ContactInquiryResponse(**r) for r in result.data]
            return ContactInquiryListResponse(
                inquiries=inquiries, total=len(inquiries)
            )

        except Exception as e:
            logger.error(f"Failed to get inquiries for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="お問い合わせの取得に失敗しました",
            )

    @staticmethod
    async def get_all_inquiries(
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ContactInquiryListResponse:
        """全お問い合わせ一覧を取得（管理者用）"""
        try:
            # Get total count
            count_query = supabase.from_("contact_inquiries").select(
                "id", count="exact"
            )
            if status_filter:
                count_query = count_query.eq("status", status_filter)
            count_result = count_query.execute()
            total = count_result.count if count_result.count is not None else 0

            # Get paginated data
            query = (
                supabase.from_("contact_inquiries")
                .select("*")
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
            )
            if status_filter:
                query = query.eq("status", status_filter)

            result = query.execute()
            inquiries = [ContactInquiryResponse(**r) for r in result.data]

            return ContactInquiryListResponse(inquiries=inquiries, total=total)

        except Exception as e:
            logger.error(f"Failed to get all inquiries: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="お問い合わせの取得に失敗しました",
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
        inquiry_id: str, data: UpdateInquiryStatusRequest
    ) -> ContactInquiryResponse:
        """お問い合わせステータスを更新（管理者用）"""
        try:
            update_data: dict = {
                "status": data.status.value,
                "updated_at": datetime.utcnow().isoformat(),
            }
            if data.admin_note is not None:
                update_data["admin_note"] = data.admin_note

            result = (
                supabase.from_("contact_inquiries")
                .update(update_data)
                .eq("id", inquiry_id)
                .execute()
            )

            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="お問い合わせが見つかりません",
                )

            logger.info(
                f"Inquiry {inquiry_id} status updated to {data.status.value}"
            )
            return ContactInquiryResponse(**result.data[0])

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Failed to update inquiry {inquiry_id}: {e}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="お問い合わせの更新に失敗しました",
            )


def _build_email_html(inquiry: ContactInquiryResponse) -> str:
    """Build HTML email body"""
    category_label = CATEGORY_LABELS.get(inquiry.category, inquiry.category)
    return f"""
<div style="font-family: 'Noto Sans JP', sans-serif; max-width: 600px; margin: 0 auto;">
  <div style="background: #E5581C; color: white; padding: 16px 24px; border-radius: 8px 8px 0 0;">
    <h2 style="margin: 0; font-size: 18px;">BlogAI - 新しいお問い合わせ</h2>
  </div>
  <div style="border: 1px solid #e5e7eb; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">
    <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px;">
      <tr>
        <td style="padding: 8px 0; color: #6b7280; width: 100px;">送信者</td>
        <td style="padding: 8px 0; font-weight: 500;">{inquiry.name} ({inquiry.email})</td>
      </tr>
      <tr>
        <td style="padding: 8px 0; color: #6b7280;">カテゴリ</td>
        <td style="padding: 8px 0;">{category_label}</td>
      </tr>
      <tr>
        <td style="padding: 8px 0; color: #6b7280;">件名</td>
        <td style="padding: 8px 0; font-weight: 500;">{inquiry.subject}</td>
      </tr>
      <tr>
        <td style="padding: 8px 0; color: #6b7280;">ユーザーID</td>
        <td style="padding: 8px 0; font-size: 12px; color: #9ca3af;">{inquiry.user_id}</td>
      </tr>
    </table>
    <div style="background: #f9fafb; border-radius: 8px; padding: 16px; white-space: pre-wrap;">{inquiry.message}</div>
  </div>
</div>
"""


def _build_email_text(inquiry: ContactInquiryResponse) -> str:
    """Build plain text email body"""
    category_label = CATEGORY_LABELS.get(inquiry.category, inquiry.category)
    return f"""新しいお問い合わせが届きました。

送信者: {inquiry.name} ({inquiry.email})
カテゴリ: {category_label}
件名: {inquiry.subject}
ユーザーID: {inquiry.user_id}
送信日時: {inquiry.created_at}

--- お問い合わせ内容 ---
{inquiry.message}
"""


async def _send_notification_email(inquiry: ContactInquiryResponse) -> None:
    """Send notification email using Resend (preferred) or SMTP fallback"""
    notification_email = settings.contact_notification_email
    if not notification_email:
        logger.info("Email notification skipped: CONTACT_NOTIFICATION_EMAIL not set")
        return

    html_body = _build_email_html(inquiry)
    text_body = _build_email_text(inquiry)
    subject = f"[BlogAI] お問い合わせ: {inquiry.subject}"

    # Try Resend first
    if settings.resend_api_key:
        try:
            resend.api_key = settings.resend_api_key
            params: resend.Emails.SendParams = {
                "from": settings.resend_from_email,
                "to": [notification_email],
                "subject": subject,
                "html": html_body,
                "text": text_body,
                "reply_to": inquiry.email,
            }
            result = await asyncio.to_thread(resend.Emails.send, params)
            logger.info(
                f"Notification email sent via Resend for inquiry {inquiry.id}: {result}"
            )
            return
        except Exception as e:
            logger.error(f"Failed to send email via Resend: {e}")
            # Fall through to SMTP if configured
            if not settings.smtp_host:
                return

    # SMTP fallback
    if settings.smtp_host:
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            smtp_from = settings.smtp_from_email or settings.smtp_user

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_from
            msg["To"] = notification_email
            msg["Reply-To"] = inquiry.email
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            def _send():
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                    server.starttls()
                    if settings.smtp_user and settings.smtp_password:
                        server.login(settings.smtp_user, settings.smtp_password)
                    server.sendmail(smtp_from, [notification_email], msg.as_string())

            await asyncio.to_thread(_send)
            logger.info(f"Notification email sent via SMTP for inquiry {inquiry.id}")
            return
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            return

    logger.info("Email notification skipped: neither Resend nor SMTP configured")
