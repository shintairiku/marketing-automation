import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from main import app
from app.domains.company.schemas import CompanyInfoResponse, CompanyInfoList, CompanyInfoCreate
from app.common.auth import get_current_user_id_from_token

client = TestClient(app)

# テストで使うユーザーIDを定義
test_user_id = "test-user-123"

@pytest.mark.asyncio
async def test_create_company_success():
    """
    会社作成APIが正常に動作するかをテスト
    """
    app.dependency_overrides[get_current_user_id_from_token] = lambda: test_user_id

    from app.domains.company.service import CompanyService

    # Service層の create_company をモック化
    with patch.object(CompanyService, "create_company", new_callable=AsyncMock) as mock_create_company:
        mock_create_company.return_value = CompanyInfoResponse(
            id="c1",
            name="New Test Company",
            is_default=False,
            user_id=test_user_id,
            website_url="http://example.com",
            description="New company description",
            usp="New USP",
            target_persona="New Persona",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        request_data = {
            "name": "New Test Company",
            "website_url": "http://example.com",
            "description": "New company description",
            "usp": "New USP",
            "target_persona": "New Persona"
        }

        response = client.post("/companies/", json=request_data)

        assert response.status_code == 201
        response_data = response.json()
        assert response_data["name"] == "New Test Company"
        assert response_data["website_url"] == "http://example.com/"
        assert response_data["user_id"] == test_user_id

        mock_create_company.assert_awaited_once_with(
            CompanyInfoCreate(**request_data),
            test_user_id
        )

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_create_company_invalid_data():
    """
    不正なデータで会社作成APIを呼び出した場合に 422 が返ることをテスト
    """
    app.dependency_overrides[get_current_user_id_from_token] = lambda: test_user_id

    # nameフィールドが欠落した不正なリクエストデータ
    invalid_request_data = {
        "website_url": "http://invalid.com",
        "description": "Invalid data description",
        "usp": "Invalid USP",
        "target_persona": "Invalid Persona"
    }

    response = client.post("/companies/", json=invalid_request_data)

    assert response.status_code == 422
    response_data = response.json()
    assert "detail" in response_data
    assert response_data["detail"][0]["loc"] == ["body", "name"]
    assert response_data["detail"][0]["msg"] == "Field required"

    app.dependency_overrides.clear()

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

@pytest.mark.asyncio
async def test_get_companies_by_user_empty_list():
    """
    会社情報が一件もない場合に、空のリストが返ることをテスト
    """
    app.dependency_overrides[get_current_user_id_from_token] = lambda: test_user_id
    
    from app.domains.company.service import CompanyService
    from app.domains.company.schemas import CompanyInfoList

    # Service層の get_companies_by_user をモック化して空のリストを返す
    with patch.object(CompanyService, "get_companies_by_user", new_callable=AsyncMock) as mock_get_companies:
        mock_get_companies.return_value = CompanyInfoList(companies=[], total=0)
        
        response = client.get("/companies/")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["companies"] == []
        assert response_data["total"] == 0
        
        mock_get_companies.assert_awaited_once_with(test_user_id)
        
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_get_default_company_success():
    """
    デフォルト会社取得APIが正常に動作するかをテスト
    """
    app.dependency_overrides[get_current_user_id_from_token] = lambda: test_user_id

    from app.domains.company.service import CompanyService
    from app.domains.company.schemas import CompanyInfoResponse

    # Service層の get_default_company をモック化して、有効なレスポンスを返す
    with patch.object(CompanyService, "get_default_company", new_callable=AsyncMock) as mock_get_default_company:
        mock_get_default_company.return_value = CompanyInfoResponse(
            id="c_default",
            name="Default Test Company",
            is_default=True,
            user_id=test_user_id,
            website_url="http://default.com",
            description="Default company description",
            usp="Default USP",
            target_persona="Default Persona",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        response = client.get("/companies/default")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == "c_default"
        assert response_data["name"] == "Default Test Company"
        assert response_data["is_default"] is True
        assert response_data["user_id"] == test_user_id
        
        mock_get_default_company.assert_awaited_once_with(test_user_id)

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_get_default_company_not_found():
    """
    デフォルト会社が設定されていない場合に 404 が返ることをテスト
    """
    app.dependency_overrides[get_current_user_id_from_token] = lambda: test_user_id

    from app.domains.company.service import CompanyService

    # Service層の get_default_company をモック化して None を返す
    with patch.object(CompanyService, "get_default_company", new_callable=AsyncMock) as mock_get_default_company:
        mock_get_default_company.return_value = None

        response = client.get("/companies/default")

        assert response.status_code == 404
        assert response.json()["detail"] == "デフォルト会社が設定されていません"

        mock_get_default_company.assert_awaited_once_with(test_user_id)

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_get_company_success():
    """
    特定の会社情報取得APIが正常に動作するかをテスト
    """
    app.dependency_overrides[get_current_user_id_from_token] = lambda: test_user_id
    
    from app.domains.company.service import CompanyService
    from app.domains.company.schemas import CompanyInfoResponse

    company_id = "c123"

    with patch.object(CompanyService, "get_company_by_id", new_callable=AsyncMock) as mock_get_company_by_id:
        mock_get_company_by_id.return_value = CompanyInfoResponse(
            id=company_id,
            name="Specific Test Company",
            is_default=False,
            user_id=test_user_id,
            website_url="http://specific.com",
            description="Specific company description",
            usp="Specific USP",
            target_persona="Specific Persona",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        response = client.get(f"/companies/{company_id}")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == company_id
        assert response_data["name"] == "Specific Test Company"
        
        mock_get_company_by_id.assert_awaited_once_with(company_id, test_user_id)

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_get_company_not_found():
    """
    存在しない会社IDで情報を取得しようとした場合に 404 が返ることをテスト
    """
    app.dependency_overrides[get_current_user_id_from_token] = lambda: test_user_id
    
    from app.domains.company.service import CompanyService

    non_existent_company_id = "non-existent-id"

    # Service層の get_company_by_id をモック化して None を返す
    with patch.object(CompanyService, "get_company_by_id", new_callable=AsyncMock) as mock_get_company_by_id:
        mock_get_company_by_id.return_value = None

        response = client.get(f"/companies/{non_existent_company_id}")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "会社情報が見つかりません"
        
        mock_get_company_by_id.assert_awaited_once_with(non_existent_company_id, test_user_id)
        
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_company_success():
    """
    会社更新APIが正常に動作するかをテスト
    """
    app.dependency_overrides[get_current_user_id_from_token] = lambda: test_user_id

    from app.domains.company.service import CompanyService
    from app.domains.company.schemas import CompanyInfoUpdate, CompanyInfoResponse

    company_id = "c-update-123"
    update_data = {
        "name": "Updated Company Name",
        "description": "Updated company description",
    }
    
    # Service層の update_company をモック化
    with patch.object(CompanyService, "update_company", new_callable=AsyncMock) as mock_update_company:
        mock_update_company.return_value = CompanyInfoResponse(
            id=company_id,
            name="Updated Company Name",
            is_default=False,
            user_id=test_user_id,
            website_url="http://original.com",
            description="Updated company description",
            usp="Original USP",
            target_persona="Original Persona",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z" # 更新された日時を表現
        )

        response = client.put(f"/companies/{company_id}", json=update_data)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == company_id
        assert response_data["name"] == "Updated Company Name"
        assert response_data["description"] == "Updated company description"

        mock_update_company.assert_awaited_once_with(
            company_id,
            CompanyInfoUpdate(**update_data),
            test_user_id
        )

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_company_not_found():
    """
    存在しない会社IDで情報を更新しようとした場合に 404 が返ることをテスト
    """
    app.dependency_overrides[get_current_user_id_from_token] = lambda: test_user_id

    from app.domains.company.service import CompanyService
    from app.domains.company.schemas import CompanyInfoUpdate

    non_existent_company_id = "non-existent-id"
    update_data = {
        "name": "Updated Company Name",
        "description": "Updated company description",
    }
    
    # Service層の update_company をモック化して None を返す
    with patch.object(CompanyService, "update_company", new_callable=AsyncMock) as mock_update_company:
        mock_update_company.return_value = None

        response = client.put(f"/companies/{non_existent_company_id}", json=update_data)
        
        assert response.status_code == 404
        assert response.json()["detail"] == "会社情報が見つかりません"
        
        mock_update_company.assert_awaited_once_with(
            non_existent_company_id,
            CompanyInfoUpdate(**update_data),
            test_user_id
        )

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_delete_company_success():
    """
    会社削除APIが正常に動作し、204 No Content を返すことをテスト
    """
    app.dependency_overrides[get_current_user_id_from_token] = lambda: test_user_id

    from app.domains.company.service import CompanyService
    from app.domains.company.schemas import CompanyInfoResponse

    company_id_to_delete = "c-delete-123"

    # Service層の delete_company をモック化し、削除されたオブジェクトを返す
    with patch.object(CompanyService, "delete_company", new_callable=AsyncMock) as mock_delete_company:
        mock_delete_company.return_value = CompanyInfoResponse(
            id=company_id_to_delete,
            name="Deleted Company",
            is_default=False,
            user_id=test_user_id,
            website_url="http://deleted.com",
            description="Deleted company description",
            usp="Deleted USP",
            target_persona="Deleted Persona",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        response = client.delete(f"/companies/{company_id_to_delete}")

        # ステータスコードが 204 であることを検証
        assert response.status_code == 204
        # レスポンスボディが空であることを検証
        assert not response.content

        # Serviceメソッドが正しい引数で一度だけ呼ばれたことを確認
        mock_delete_company.assert_awaited_once_with(company_id_to_delete, test_user_id)

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_delete_company_not_found():
    """
    存在しない会社IDで情報を削除しようとした場合に 404 が返ることをテスト
    """
    app.dependency_overrides[get_current_user_id_from_token] = lambda: test_user_id

    from app.domains.company.service import CompanyService

    non_existent_company_id = "non-existent-id"

    # Service層の delete_company をモック化し、None を返す
    with patch.object(CompanyService, "delete_company", new_callable=AsyncMock) as mock_delete_company:
        mock_delete_company.return_value = None

        response = client.delete(f"/companies/{non_existent_company_id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "会社情報が見つかりません"
        
        mock_delete_company.assert_awaited_once_with(non_existent_company_id, test_user_id)

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_set_default_company_success():
    """
    デフォルト会社設定APIが正常に動作するかをテスト
    """
    app.dependency_overrides[get_current_user_id_from_token] = lambda: test_user_id

    from app.domains.company.service import CompanyService
    from app.domains.company.schemas import SetDefaultCompanyRequest, CompanyInfoResponse

    company_id_to_set_default = "c-default-123"
    request_data = {"company_id": company_id_to_set_default}

    # Service層の set_default_company をモック化
    with patch.object(CompanyService, "set_default_company", new_callable=AsyncMock) as mock_set_default_company:
        mock_set_default_company.return_value = CompanyInfoResponse(
            id=company_id_to_set_default,
            name="New Default Company",
            is_default=True,
            user_id=test_user_id,
            website_url="http://new-default.com",
            description="New default description",
            usp="New default USP",
            target_persona="New default Persona",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z"
        )

        response = client.post("/companies/set-default", json=request_data)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == company_id_to_set_default
        assert response_data["is_default"] is True
        
        mock_set_default_company.assert_awaited_once_with(
            SetDefaultCompanyRequest(**request_data),
            test_user_id
        )
    
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_set_default_company_not_found():
    """
    存在しない会社IDをデフォルトに設定しようとした場合に 404 が返ることをテスト
    """
    app.dependency_overrides[get_current_user_id_from_token] = lambda: test_user_id

    from app.domains.company.service import CompanyService
    from app.domains.company.schemas import SetDefaultCompanyRequest

    non_existent_company_id = "non-existent-id"
    request_data = {"company_id": non_existent_company_id}
    
    # Service層の set_default_company をモック化して None を返す
    with patch.object(CompanyService, "set_default_company", new_callable=AsyncMock) as mock_set_default_company:
        mock_set_default_company.return_value = None

        response = client.post("/companies/set-default", json=request_data)

        assert response.status_code == 404
        assert response.json()["detail"] == "会社情報が見つかりません"
        
        mock_set_default_company.assert_awaited_once_with(
            SetDefaultCompanyRequest(**request_data),
            test_user_id
        )

    app.dependency_overrides.clear()