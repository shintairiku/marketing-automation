# tests/test_company_endpoints.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from main import app
from app.domains.company.schemas import CompanyInfoResponse, CompanyInfoList
from app.common.auth import get_current_user_id_from_token

client = TestClient(app)

# テストで使うユーザーIDを定義
test_user_id = "test-user-123"

@pytest.mark.asyncio
async def test_get_companies_by_user_success():
    """
    ユーザーの会社情報一覧取得APIが正常に動作するかをテスト
    """
    app.dependency_overrides[get_current_user_id_from_token] = lambda: test_user_id

    with patch('app.domains.company.service.CompanyService.get_companies_by_user', new_callable=AsyncMock) as mock_get_companies:
        mock_get_companies.return_value = CompanyInfoList(
            companies=[
                CompanyInfoResponse(
                    id="c1",
                    name="Test Company 1",
                    is_default=False,
                    user_id=test_user_id,
                    website_url="http://example1.com",
                    description="Test description 1",
                    usp="Test USP 1",
                    target_persona="Test Persona 1",
                    created_at="2024-01-01T00:00:00Z",
                    updated_at="2024-01-01T00:00:00Z"
                ),
                CompanyInfoResponse(
                    id="c2",
                    name="Test Company 2",
                    is_default=True,
                    user_id=test_user_id,
                    website_url="http://example2.com",
                    description="Test description 2",
                    usp="Test USP 2",
                    target_persona="Test Persona 2",
                    created_at="2024-01-02T00:00:00Z",
                    updated_at="2024-01-02T00:00:00Z"
                )
            ],
            total=2
        )

        response = client.get("/companies/")
        
        assert response.status_code == 200
        assert len(response.json()['companies']) == 2
        assert response.json()['companies'][0]["name"] == "Test Company 1"
        assert response.json()['total'] == 2
        
        mock_get_companies.assert_awaited_once_with(test_user_id)
        
    app.dependency_overrides.clear()