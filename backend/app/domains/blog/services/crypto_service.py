# -*- coding: utf-8 -*-
"""
Blog AI Domain - Crypto Service

WordPress MCP認証情報の暗号化/復号化サービス（AES-256-GCM）
"""

import base64
import json
import logging
import os
from typing import Any, Dict

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

logger = logging.getLogger(__name__)

# GCM推奨ナンスサイズ
NONCE_SIZE = 12


class CryptoService:
    """
    AES-256-GCMによる暗号化サービス

    WordPress MCP連携の認証情報を安全に保存するために使用。
    """

    def __init__(self, encryption_key: str | None = None):
        """
        Args:
            encryption_key: Base64エンコードされた32バイトの暗号化キー
                           指定しない場合は環境変数から取得
        """
        key_b64 = encryption_key or settings.credential_encryption_key
        if not key_b64:
            raise ValueError(
                "暗号化キーが設定されていません。"
                "CREDENTIAL_ENCRYPTION_KEY環境変数を設定してください。"
            )

        try:
            self._key = base64.b64decode(key_b64)
            if len(self._key) != 32:
                raise ValueError(
                    f"暗号化キーは32バイトである必要があります（現在: {len(self._key)}バイト）"
                )
            self._aesgcm = AESGCM(self._key)
        except Exception as e:
            logger.error(f"暗号化キーの初期化に失敗: {e}")
            raise

    def encrypt(self, data: Dict[str, Any]) -> str:
        """
        データを暗号化してBase64文字列を返す

        Args:
            data: 暗号化するデータ（辞書）

        Returns:
            Base64エンコードされた暗号文（nonce + ciphertext）
        """
        try:
            nonce = os.urandom(NONCE_SIZE)
            plaintext = json.dumps(data).encode("utf-8")
            ciphertext = self._aesgcm.encrypt(nonce, plaintext, None)

            # nonce + ciphertext をBase64エンコード
            encrypted = base64.b64encode(nonce + ciphertext).decode("utf-8")
            return encrypted

        except Exception as e:
            logger.error(f"暗号化に失敗: {e}")
            raise

    def decrypt(self, encrypted: str) -> Dict[str, Any]:
        """
        Base64文字列を復号化してデータを返す

        Args:
            encrypted: Base64エンコードされた暗号文

        Returns:
            復号化されたデータ（辞書）
        """
        try:
            data = base64.b64decode(encrypted)
            nonce = data[:NONCE_SIZE]
            ciphertext = data[NONCE_SIZE:]

            plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
            return json.loads(plaintext.decode("utf-8"))

        except Exception as e:
            logger.error(f"復号化に失敗: {e}")
            raise

    def encrypt_credentials(
        self,
        access_token: str,
        api_key: str,
        api_secret: str,
    ) -> str:
        """
        WordPress MCP認証情報を暗号化

        Args:
            access_token: Bearer認証用トークン
            api_key: Basic認証用APIキー
            api_secret: Basic認証用APIシークレット

        Returns:
            暗号化された認証情報（Base64文字列）
        """
        credentials = {
            "access_token": access_token,
            "api_key": api_key,
            "api_secret": api_secret,
        }
        return self.encrypt(credentials)

    def decrypt_credentials(self, encrypted: str) -> Dict[str, str]:
        """
        WordPress MCP認証情報を復号化

        Args:
            encrypted: 暗号化された認証情報

        Returns:
            復号化された認証情報
            {
                "access_token": str,
                "api_key": str,
                "api_secret": str,
            }
        """
        return self.decrypt(encrypted)


# シングルトンインスタンス
_crypto_service: CryptoService | None = None


def get_crypto_service() -> CryptoService:
    """CryptoServiceのシングルトンインスタンスを取得"""
    global _crypto_service
    if _crypto_service is None:
        _crypto_service = CryptoService()
    return _crypto_service
