# -*- coding: utf-8 -*-
"""
Test suite for backend/app/common/auth.py
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import jwt
from app.common.auth import get_current_user_id_from_token, get_current_user_id_from_header

# --- 定数 ---
# Clerkから取得される一般的なユーザーID
MOCK_USER_ID = "user_clerk_2mY7gX0v6QZlP1oK3wJ8hT" 
# ダミーのJWT（実際の値は重要ではない）
DUMMY_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

# ----------------------------------------------------
# FastAPI Dependency (get_current_user_id_from_token) のテスト
# ----------------------------------------------------

# jwt.decodeの返り値をモック化するフィクスチャを定義
@pytest.fixture
def mock_jwt_decode():
    """jwt.decodeをパッチし、モックオブジェクトを返す"""
    with patch("app.common.auth.jwt.decode") as mock_decode:
        yield mock_decode

# モックの認証ヘッダーオブジェクトを作成するヘルパー関数
def create_mock_auth_credentials(token: str) -> HTTPAuthorizationCredentials:
    """HTTPAuthorizationCredentialsオブジェクトを模擬する"""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

def test_token_success_with_sub(mock_jwt_decode):
    """
    [正常系: subフィールド]
    JWTの 'sub' フィールドからユーザーIDが正常に抽出されること
    """
    # ユーザーIDを含むデコード結果を設定
    mock_jwt_decode.return_value = {"sub": MOCK_USER_ID}
    auth_credentials = create_mock_auth_credentials(DUMMY_TOKEN)
    
    user_id = get_current_user_id_from_token(auth_credentials)
    
    assert user_id == MOCK_USER_ID
    mock_jwt_decode.assert_called_once()


def test_token_success_with_alternative_field(mock_jwt_decode):
    """
    [正常系: 代替フィールド]
    JWTの 'sub' が欠落しており、代替フィールドからユーザーIDが抽出されること
    """
    # 'sub' はないが 'user_id' があるデコード結果を設定
    mock_jwt_decode.return_value = {"not_sub": "value", "user_id": MOCK_USER_ID}
    auth_credentials = create_mock_auth_credentials(DUMMY_TOKEN)
    
    user_id = get_current_user_id_from_token(auth_credentials)
    
    assert user_id == MOCK_USER_ID
    mock_jwt_decode.assert_called_once()


def test_token_fail_no_authorization_header():
    """
    [異常系: ヘッダーなし]
    Authorization ヘッダー (credentials) が渡されない場合に 401 HTTPException が発生すること
    """
    with pytest.raises(HTTPException) as excinfo:
        # Noneを渡すことでヘッダーがない状態を模擬
        get_current_user_id_from_token(None)
    
    assert excinfo.value.status_code == 401
    assert "Authorization header required" in excinfo.value.detail


def test_token_fail_invalid_token(mock_jwt_decode):
    """
    [異常系: 不正なトークン]
    JWTのデコードに失敗した場合 (InvalidTokenError) に 401 HTTPException が発生すること
    """
    # jwt.decodeがInvalidTokenErrorを発生するように設定
    mock_jwt_decode.side_effect = MagicMock(side_effect=jwt.InvalidTokenError("Invalid format"))
    auth_credentials = create_mock_auth_credentials("invalid-token-string")
    
    with pytest.raises(HTTPException) as excinfo:
        get_current_user_id_from_token(auth_credentials)
        
    assert excinfo.value.status_code == 401
    assert "Invalid JWT token" in excinfo.value.detail


def test_token_fail_no_user_id(mock_jwt_decode):
    """
    [異常系: IDなし]
    JWTが有効でも、ユーザーIDを含むフィールドがすべて欠落している場合に 401 HTTPException が発生すること
    """
    # ユーザーIDフィールドが全くないデコード結果を設定
    mock_jwt_decode.return_value = {"iss": "clerk", "aud": "audience"}
    auth_credentials = create_mock_auth_credentials(DUMMY_TOKEN)
    
    with pytest.raises(HTTPException) as excinfo:
        get_current_user_id_from_token(auth_credentials)
        
    assert excinfo.value.status_code == 401
    assert "no user ID found" in excinfo.value.detail


# ----------------------------------------------------
# WebSocket Utility (get_current_user_id_from_header) のテスト
# ----------------------------------------------------

def test_header_success_with_bearer(mock_jwt_decode):
    """
    [正常系: Bearerあり]
    "Bearer " プレフィックスを付けて渡された場合に、ユーザーIDが正常に返されること
    """
    mock_jwt_decode.return_value = {"sub": MOCK_USER_ID}
    
    # "Bearer " を含む文字列を渡す
    user_id = get_current_user_id_from_header(f"Bearer {DUMMY_TOKEN}")
    
    assert user_id == MOCK_USER_ID
    mock_jwt_decode.assert_called_once()


def test_header_success_without_bearer(mock_jwt_decode):
    """
    [正常系: Bearerなし]
    "Bearer " プレフィックスなしで渡された場合に、ユーザーIDが正常に返されること
    """
    mock_jwt_decode.return_value = {"sub": MOCK_USER_ID}
    
    # トークン文字列のみを渡す
    user_id = get_current_user_id_from_header(DUMMY_TOKEN)
    
    assert user_id == MOCK_USER_ID
    mock_jwt_decode.assert_called_once()

def test_header_fail_no_authorization_string():
    """
    [異常系: 文字列なし]
    authorization 文字列が None または空の場合に ValueError が発生すること
    """
    with pytest.raises(ValueError) as excinfo:
        get_current_user_id_from_header(None)
    
    assert "Authorization header required" in str(excinfo.value)
    
    with pytest.raises(ValueError) as excinfo:
        get_current_user_id_from_header("")
        
    assert "Authorization header required" in str(excinfo.value)


def test_header_fail_invalid_token_format(mock_jwt_decode):
    """
    [異常系: 不正な形式]
    トークンデコードに失敗した場合に ValueError が発生すること
    """
    mock_jwt_decode.side_effect = MagicMock(side_effect=jwt.InvalidTokenError)
    
    with pytest.raises(ValueError) as excinfo:
        get_current_user_id_from_header("Bearer invalid-jwt")
        
    assert "Authentication error" in str(excinfo.value)

def test_header_fail_no_user_id_in_token(mock_jwt_decode):
    """
    [異常系: IDなし]
    トークン内にユーザーIDを示すフィールドがない場合に ValueError が発生すること
    """
    mock_jwt_decode.return_value = {"iss": "clerk", "aud": "audience"}
    
    with pytest.raises(ValueError) as excinfo:
        get_current_user_id_from_header(f"Bearer {DUMMY_TOKEN}")
        
    assert "no user ID found" in str(excinfo.value)