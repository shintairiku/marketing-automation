"""
Test suite for backend/app/domains/company/service.py
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from datetime import datetime, timezone
import uuid

from app.domains.company.service import CompanyService
from app.domains.company.schemas import (
    CompanyInfoCreate,
    CompanyInfoUpdate,
    CompanyInfoResponse,
    CompanyInfoList,
    SetDefaultCompanyRequest,
    TargetPersona
)

@pytest.fixture
def mock_supabase():
    with patch('app.domains.company.service.supabase') as mock_supabase:
        yield mock_supabase

@pytest.fixture
def sample_company_data():
    return CompanyInfoCreate(
        name="テスト株式会社",
        website_url="https://test.com",
        description="テスト事業内容",
        usp="テストの強み",
        target_persona=TargetPersona.SMALL_BUSINESS_OWNER.value,
        brand_slogan="テストスローガン",
        target_keywords="テスト,キーワード",
        industry_terms="業界用語",
        avoid_terms="NGワード",
        popular_articles="人気記事",
        target_area="東京",
        is_default=True
    )

@pytest.fixture
def sample_user_id():
    return "test_user_123"

@pytest.fixture
def sample_company_id():
    return str(uuid.uuid4())

@pytest.mark.asyncio
async def test_create_company_success(mock_supabase, sample_company_data, sample_user_id):
    """会社作成の成功テスト"""
    # モック設定
    mock_supabase.from_.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    mock_supabase.from_.return_value.insert.return_value.execute.return_value.data = [{
        "id": "test_id",
        "user_id": sample_user_id,
        "name": sample_company_data.name,
        "website_url": str(sample_company_data.website_url),
        "description": sample_company_data.description,
        "usp": sample_company_data.usp,
        "target_persona": sample_company_data.target_persona,
        "is_default": True,
        "brand_slogan": sample_company_data.brand_slogan,
        "target_keywords": sample_company_data.target_keywords,
        "industry_terms": sample_company_data.industry_terms,
        "avoid_terms": sample_company_data.avoid_terms,
        "popular_articles": sample_company_data.popular_articles,
        "target_area": sample_company_data.target_area,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }]
    
    result = await CompanyService.create_company(sample_company_data, sample_user_id)
    
    assert isinstance(result, CompanyInfoResponse)
    assert result.name == sample_company_data.name
    assert result.user_id == sample_user_id
    assert result.is_default is True

@pytest.mark.asyncio
async def test_create_company_first_company_auto_default(mock_supabase, sample_company_data, sample_user_id):
    """初回作成時の自動デフォルト設定テスト"""
    # 既存会社なし（初回作成）
    mock_supabase.from_.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    mock_supabase.from_.return_value.insert.return_value.execute.return_value.data = [{
        "id": "test_id",
        "user_id": sample_user_id,
        "name": sample_company_data.name,
        "website_url": str(sample_company_data.website_url),
        "description": sample_company_data.description,
        "usp": sample_company_data.usp,
        "target_persona": sample_company_data.target_persona,
        "is_default": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }]
    
    # is_defaultをFalseに設定しても、初回作成時は自動的にTrueになる
    sample_company_data.is_default = False
    result = await CompanyService.create_company(sample_company_data, sample_user_id)
    
    assert result.is_default is True

@pytest.mark.asyncio
async def test_create_company_database_error(mock_supabase, sample_company_data, sample_user_id):
    """データベースエラー時のテスト"""
    mock_supabase.from_.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    mock_supabase.from_.return_value.insert.return_value.execute.return_value.data = None
    
    with pytest.raises(HTTPException) as exc_info:
        await CompanyService.create_company(sample_company_data, sample_user_id)
    
    assert exc_info.value.status_code == 500
    assert "会社情報の作成に失敗しました" in exc_info.value.detail

@pytest.mark.asyncio
async def test_get_companies_by_user_success(mock_supabase, sample_user_id):
    """ユーザーの会社一覧取得の成功テスト"""
    mock_data = [
        {
            "id": "company1",
            "user_id": sample_user_id,
            "name": "会社1",
            "website_url": "https://company1.com",
            "description": "会社1の説明",
            "usp": "会社1の強み",
            "target_persona": "中小企業の経営者",
            "is_default": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "company2",
            "user_id": sample_user_id,
            "name": "会社2",
            "website_url": "https://company2.com",
            "description": "会社2の説明",
            "usp": "会社2の強み",
            "target_persona": "大企業の担当者",
            "is_default": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    mock_supabase.from_.return_value.select.return_value.eq.return_value.order.return_value.order.return_value.execute.return_value.data = mock_data
    
    result = await CompanyService.get_companies_by_user(sample_user_id)
    
    assert isinstance(result, CompanyInfoList)
    assert len(result.companies) == 2
    assert result.total == 2
    assert result.default_company_id == "company1"

@pytest.mark.asyncio
async def test_get_company_by_id_success(mock_supabase, sample_company_id, sample_user_id):
    """特定の会社取得の成功テスト"""
    mock_data = {
        "id": sample_company_id,
        "user_id": sample_user_id,
        "name": "テスト会社",
        "website_url": "https://test.com",
        "description": "テスト説明",
        "usp": "テスト強み",
        "target_persona": "中小企業の経営者",
        "is_default": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    mock_supabase.from_.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_data
    
    result = await CompanyService.get_company_by_id(sample_company_id, sample_user_id)
    
    assert isinstance(result, CompanyInfoResponse)
    assert result.id == sample_company_id
    assert result.user_id == sample_user_id

@pytest.mark.asyncio
async def test_get_company_by_id_not_found(mock_supabase, sample_company_id, sample_user_id):
    """存在しない会社取得のテスト"""
    mock_supabase.from_.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = None
    
    with pytest.raises(HTTPException) as exc_info:
        await CompanyService.get_company_by_id(sample_company_id, sample_user_id)
    
    assert exc_info.value.status_code == 404
    assert "指定された会社情報が見つかりません" in exc_info.value.detail

@pytest.mark.asyncio
async def test_get_default_company_success(mock_supabase, sample_user_id):
    """デフォルト会社取得の成功テスト"""
    mock_data = {
        "id": "default_company",
        "user_id": sample_user_id,
        "name": "デフォルト会社",
        "website_url": "https://default.com",
        "description": "デフォルト説明",
        "usp": "デフォルト強み",
        "target_persona": "中小企業の経営者",
        "is_default": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    mock_supabase.from_.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [mock_data]
    
    result = await CompanyService.get_default_company(sample_user_id)
    
    assert isinstance(result, CompanyInfoResponse)
    assert result.is_default is True

@pytest.mark.asyncio
async def test_get_default_company_not_found(mock_supabase, sample_user_id):
    """デフォルト会社が存在しない場合のテスト"""
    mock_supabase.from_.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    
    result = await CompanyService.get_default_company(sample_user_id)
    
    assert result is None

@pytest.mark.asyncio
async def test_update_company_success(mock_supabase, sample_company_id, sample_user_id):
    """会社更新の成功テスト"""
    existing_data = {
        "id": sample_company_id,
        "user_id": sample_user_id,
        "name": "旧会社名",
        "website_url": "https://old.com",
        "description": "旧説明",
        "usp": "旧強み",
        "target_persona": "中小企業の経営者",
        "is_default": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    updated_data = {
        "id": sample_company_id,
        "user_id": sample_user_id,
        "name": "新会社名",
        "website_url": "https://new.com",
        "description": "新説明",
        "usp": "新強み",
        "target_persona": "大企業の担当者",
        "is_default": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    mock_supabase.from_.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = existing_data
    mock_supabase.from_.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [updated_data]
    
    update_data = CompanyInfoUpdate(
        name="新会社名",
        website_url="https://new.com",
        description="新説明",
        usp="新強み",
        target_persona="大企業の担当者",
        is_default=True
    )
    
    result = await CompanyService.update_company(sample_company_id, update_data, sample_user_id)
    
    assert isinstance(result, CompanyInfoResponse)
    assert result.name == "新会社名"
    assert result.is_default is True

@pytest.mark.asyncio
async def test_update_company_not_found(mock_supabase, sample_company_id, sample_user_id):
    """存在しない会社の更新テスト"""
    mock_supabase.from_.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = None
    
    update_data = CompanyInfoUpdate(name="新会社名")
    
    with pytest.raises(HTTPException) as exc_info:
        await CompanyService.update_company(sample_company_id, update_data, sample_user_id)
    
    assert exc_info.value.status_code == 404
    assert "指定された会社情報が見つかりません" in exc_info.value.detail

@pytest.mark.asyncio
async def test_delete_company_success(mock_supabase, sample_company_id, sample_user_id):
    """会社削除の成功テスト"""
    existing_data = {
        "id": sample_company_id,
        "user_id": sample_user_id,
        "name": "削除対象会社",
        "is_default": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    mock_supabase.from_.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = existing_data
    mock_supabase.from_.return_value.select.return_value.eq.return_value.neq.return_value.execute.return_value.data = []
    mock_supabase.from_.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
    
    result = await CompanyService.delete_company(sample_company_id, sample_user_id)
    
    assert result is True

@pytest.mark.asyncio
async def test_delete_company_not_found(mock_supabase, sample_company_id, sample_user_id):
    """存在しない会社の削除テスト"""
    mock_supabase.from_.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = None
    
    with pytest.raises(HTTPException) as exc_info:
        await CompanyService.delete_company(sample_company_id, sample_user_id)
    
    assert exc_info.value.status_code == 404
    assert "指定された会社情報が見つかりません" in exc_info.value.detail

@pytest.mark.asyncio
async def test_delete_default_company_with_others(mock_supabase, sample_company_id, sample_user_id):
    """デフォルト会社で他に会社がある場合の削除拒否テスト"""
    existing_data = {
        "id": sample_company_id,
        "user_id": sample_user_id,
        "name": "デフォルト会社",
        "is_default": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    other_companies = [{"id": "other_company"}]
    
    mock_supabase.from_.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = existing_data
    mock_supabase.from_.return_value.select.return_value.eq.return_value.neq.return_value.execute.return_value.data = other_companies
    
    with pytest.raises(HTTPException) as exc_info:
        await CompanyService.delete_company(sample_company_id, sample_user_id)
    
    assert exc_info.value.status_code == 400
    assert "デフォルト会社は削除できません" in exc_info.value.detail

@pytest.mark.asyncio
async def test_set_default_company_success(mock_supabase, sample_company_id, sample_user_id):
    """デフォルト会社設定の成功テスト"""
    existing_data = {
        "id": sample_company_id,
        "user_id": sample_user_id,
        "name": "設定対象会社",
        "website_url": "https://test.com",
        "description": "テスト説明",
        "usp": "テスト強み",
        "target_persona": "中小企業の経営者",
        "is_default": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    updated_data = existing_data.copy()
    updated_data["is_default"] = True
    
    mock_supabase.from_.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = existing_data
    mock_supabase.from_.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [updated_data]
    
    request = SetDefaultCompanyRequest(company_id=sample_company_id)
    result = await CompanyService.set_default_company(request, sample_user_id)
    
    assert isinstance(result, CompanyInfoResponse)
    assert result.is_default is True

@pytest.mark.asyncio
async def test_set_default_company_not_found(mock_supabase, sample_company_id, sample_user_id):
    """存在しない会社のデフォルト設定テスト"""
    mock_supabase.from_.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = None
    
    request = SetDefaultCompanyRequest(company_id=sample_company_id)
    
    with pytest.raises(HTTPException) as exc_info:
        await CompanyService.set_default_company(request, sample_user_id)
    
    assert exc_info.value.status_code == 404
    assert "指定された会社情報が見つかりません" in exc_info.value.detail

@pytest.mark.asyncio
async def test_unset_default_companies_success(mock_supabase, sample_user_id):
    """デフォルト会社設定解除の成功テスト"""
    mock_supabase.from_.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
    
    await CompanyService._unset_default_companies(sample_user_id)
    
    # モックが正しく呼び出されたことを確認
    mock_supabase.from_.assert_called_with("company_info")
    mock_supabase.from_.return_value.update.assert_called_once()