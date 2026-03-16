# -*- coding: utf-8 -*-
"""
Admin MFA (TOTP) service

TOTP の生成・検証・バックアップコード管理を行う。
秘密鍵は CryptoService (AES-256-GCM) で暗号化して DB に保存する。
"""
import hashlib
import hmac
import logging
import secrets
import string
from datetime import datetime, timezone

import pyotp
from fastapi import HTTPException, status

from app.common.database import supabase
from app.core.config import settings
from app.domains.admin.mfa.schemas import (
    TotpResetResponse,
    TotpSetupInitResponse,
    TotpStatusResponse,
    TotpVerifyResponse,
)
from app.domains.blog.services.crypto_service import CryptoService

logger = logging.getLogger(__name__)

# Rate limiting constants
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

# Backup code constants
BACKUP_CODE_COUNT = 10
BACKUP_CODE_LENGTH = 8
BACKUP_CODE_CHARS = string.ascii_uppercase + string.digits


def _generate_backup_codes() -> tuple[list[str], list[dict]]:
    """
    バックアップコード生成。

    Returns:
        tuple of (plain_codes, hashed_entries)
        plain_codes: ユーザーに表示する平文コード
        hashed_entries: DB 保存用のハッシュ済みエントリ
    """
    plain_codes: list[str] = []
    hashed_entries: list[dict] = []

    for _ in range(BACKUP_CODE_COUNT):
        code = "".join(secrets.choice(BACKUP_CODE_CHARS) for _ in range(BACKUP_CODE_LENGTH))
        salt = secrets.token_hex(16)
        code_hash = hashlib.sha256((code + salt).encode()).hexdigest()
        plain_codes.append(code)
        hashed_entries.append({
            "hash": code_hash,
            "salt": salt,
            "used_at": None,
        })

    return plain_codes, hashed_entries


def _verify_backup_code(code: str, entries: list[dict]) -> tuple[bool, list[dict]]:
    """
    バックアップコードを検証し、使用済みとしてマーク。

    Returns:
        tuple of (is_valid, updated_entries)
    """
    for entry in entries:
        if entry.get("used_at") is not None:
            continue
        expected_hash = hashlib.sha256((code.upper() + entry["salt"]).encode()).hexdigest()
        if hmac.compare_digest(expected_hash, entry["hash"]):
            entry["used_at"] = datetime.now(timezone.utc).isoformat()
            return True, entries
    return False, entries


class AdminMfaService:
    """Admin MFA (TOTP) サービス"""

    def __init__(self):
        self.db = supabase
        self.crypto = CryptoService()

    def get_status(self, user_id: str) -> TotpStatusResponse:
        """ユーザーの TOTP 設定状態を取得"""
        result = (
            self.db.table("admin_totp_secrets")
            .select("is_confirmed, backup_codes")
            .eq("user_id", user_id)
            .execute()
        )

        if not result.data:
            return TotpStatusResponse(
                is_setup=False,
                is_confirmed=False,
                backup_codes_remaining=0,
            )

        row = result.data[0]
        backup_codes = row.get("backup_codes", [])
        remaining = sum(1 for c in backup_codes if c.get("used_at") is None)

        return TotpStatusResponse(
            is_setup=True,
            is_confirmed=row["is_confirmed"],
            backup_codes_remaining=remaining,
        )

    def setup_init(self, user_id: str, email: str) -> TotpSetupInitResponse:
        """
        TOTP セットアップを開始。QR コード用の provisioning URI と
        バックアップコードを返す。

        既存の未確認レコードがあれば上書きする。
        """
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(
            name=email,
            issuer_name=settings.admin_mfa_issuer_name,
        )

        encrypted_secret = self.crypto.encrypt({"totp_secret": secret})
        plain_codes, hashed_entries = _generate_backup_codes()

        # Upsert: 未確認なら上書き、確認済みなら上書きしない
        existing = (
            self.db.table("admin_totp_secrets")
            .select("is_confirmed")
            .eq("user_id", user_id)
            .execute()
        )

        if existing.data and existing.data[0]["is_confirmed"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="TOTP は既に設定済みです。リセットしてから再設定してください。",
            )

        now = datetime.now(timezone.utc).isoformat()

        if existing.data:
            self.db.table("admin_totp_secrets").update({
                "encrypted_secret": encrypted_secret,
                "is_confirmed": False,
                "backup_codes": hashed_entries,
                "failed_attempts": 0,
                "locked_until": None,
                "last_failed_at": None,
                "updated_at": now,
            }).eq("user_id", user_id).execute()
        else:
            self.db.table("admin_totp_secrets").insert({
                "user_id": user_id,
                "encrypted_secret": encrypted_secret,
                "is_confirmed": False,
                "backup_codes": hashed_entries,
                "created_at": now,
                "updated_at": now,
            }).execute()

        logger.info(f"[MFA] TOTP setup initiated for user: {user_id}")

        return TotpSetupInitResponse(
            secret_uri=uri,
            backup_codes=plain_codes,
        )

    def setup_confirm(self, user_id: str, code: str) -> bool:
        """
        TOTP セットアップを確認。
        ユーザーが正しい TOTP コードを入力したら is_confirmed=True にする。
        """
        row = self._get_totp_row(user_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TOTP セットアップが見つかりません。先にセットアップを開始してください。",
            )

        if row["is_confirmed"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="TOTP は既に確認済みです。",
            )

        secret = self._decrypt_secret(row["encrypted_secret"])
        totp = pyotp.TOTP(secret)

        if not totp.verify(code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="コードが正しくありません。認証アプリに表示されている最新のコードを入力してください。",
            )

        now = datetime.now(timezone.utc).isoformat()
        self.db.table("admin_totp_secrets").update({
            "is_confirmed": True,
            "last_verified_at": now,
            "updated_at": now,
        }).eq("user_id", user_id).execute()

        logger.info(f"[MFA] TOTP setup confirmed for user: {user_id}")
        return True

    def verify(self, user_id: str, code: str) -> TotpVerifyResponse:
        """
        TOTP コードまたはバックアップコードを検証。
        レートリミット付き。
        """
        row = self._get_totp_row(user_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TOTP が設定されていません。",
            )

        if not row["is_confirmed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TOTP セットアップが完了していません。",
            )

        # ロックアウトチェック
        self._check_lockout(row)

        # TOTP コード検証
        secret = self._decrypt_secret(row["encrypted_secret"])
        totp = pyotp.TOTP(secret)

        if totp.verify(code, valid_window=1):
            self._reset_failed_attempts(user_id)
            logger.info(f"[MFA] TOTP verified for user: {user_id}")
            return TotpVerifyResponse(success=True, message="認証成功")

        # バックアップコード検証
        backup_codes = row.get("backup_codes", [])
        is_valid, updated_codes = _verify_backup_code(code, backup_codes)

        if is_valid:
            now = datetime.now(timezone.utc).isoformat()
            self.db.table("admin_totp_secrets").update({
                "backup_codes": updated_codes,
                "failed_attempts": 0,
                "locked_until": None,
                "last_verified_at": now,
                "updated_at": now,
            }).eq("user_id", user_id).execute()
            logger.info(f"[MFA] Backup code used for user: {user_id}")
            return TotpVerifyResponse(success=True, message="バックアップコードで認証成功")

        # 失敗
        self._record_failed_attempt(user_id, row)
        remaining = MAX_FAILED_ATTEMPTS - (row.get("failed_attempts", 0) + 1)
        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"認証に{MAX_FAILED_ATTEMPTS}回失敗しました。{LOCKOUT_MINUTES}分間ロックされます。",
            )

        return TotpVerifyResponse(
            success=False,
            message=f"コードが正しくありません（残り{max(remaining, 0)}回）",
        )

    def reset(self, admin_user_id: str, target_user_id: str) -> TotpResetResponse:
        """管理者がユーザーの TOTP をリセット"""
        result = (
            self.db.table("admin_totp_secrets")
            .select("id")
            .eq("user_id", target_user_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="対象ユーザーの TOTP 設定が見つかりません。",
            )

        self.db.table("admin_totp_secrets").delete().eq(
            "user_id", target_user_id
        ).execute()

        logger.info(
            f"[MFA] TOTP reset for user {target_user_id} by admin {admin_user_id}"
        )
        return TotpResetResponse(
            success=True,
            message=f"ユーザー {target_user_id} の二段階認証をリセットしました。",
        )

    # ---- internal helpers ----

    def _get_totp_row(self, user_id: str) -> dict | None:
        result = (
            self.db.table("admin_totp_secrets")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def _decrypt_secret(self, encrypted_secret: str) -> str:
        data = self.crypto.decrypt(encrypted_secret)
        return data["totp_secret"]

    def _check_lockout(self, row: dict) -> None:
        locked_until = row.get("locked_until")
        if locked_until:
            if isinstance(locked_until, str):
                locked_dt = datetime.fromisoformat(locked_until.replace("Z", "+00:00"))
            else:
                locked_dt = locked_until
            if locked_dt > datetime.now(timezone.utc):
                remaining_secs = int((locked_dt - datetime.now(timezone.utc)).total_seconds())
                remaining_mins = max(1, remaining_secs // 60)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"アカウントがロックされています。約{remaining_mins}分後に再試行してください。",
                )

    def _record_failed_attempt(self, user_id: str, row: dict) -> None:
        failed = row.get("failed_attempts", 0) + 1
        now = datetime.now(timezone.utc)
        update_data: dict = {
            "failed_attempts": failed,
            "last_failed_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        if failed >= MAX_FAILED_ATTEMPTS:
            from datetime import timedelta

            update_data["locked_until"] = (
                now + timedelta(minutes=LOCKOUT_MINUTES)
            ).isoformat()
            logger.warning(f"[MFA] User {user_id} locked out after {failed} failed attempts")

        self.db.table("admin_totp_secrets").update(update_data).eq(
            "user_id", user_id
        ).execute()

    def _reset_failed_attempts(self, user_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.db.table("admin_totp_secrets").update({
            "failed_attempts": 0,
            "locked_until": None,
            "last_verified_at": now,
            "updated_at": now,
        }).eq("user_id", user_id).execute()


# Singleton
mfa_service = AdminMfaService()
