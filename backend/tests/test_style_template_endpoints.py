# -*- coding: utf-8 -*-
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from main import app
from app.common.auth import get_current_user_id_from_token

client = TestClient(app)

# Dummy data and mocks
TEST_USER_ID = "test-user-id"
TEST_ORG_ID = "test-org-id"
TEST_ADMIN_ID = "test-admin-id"
TEST_MEMBER_ID = "test-member-id"
TEST_OTHER_USER_ID = "other-user-id"

# Mock the dependency
app.dependency_overrides[get_current_user_id_from_token] = lambda: TEST_USER_ID

@pytest.fixture
def mock_supabase():
    with patch("app.domains.style_template.endpoints.supabase") as mock_supabase:
        yield mock_supabase

@pytest.fixture(autouse=True)
def mock_auth():
    app.dependency_overrides[get_current_user_id_from_token] = lambda: TEST_USER_ID
    yield
    app.dependency_overrides.clear()

# --- GET /style-templates/ ---
def test_get_style_templates_success(mock_supabase):
    mock_data = [
        {"id": "2", "user_id": TEST_USER_ID, "organization_id": None, "name": "Template 2", "description": None, "template_type": "custom", "settings": {}, "is_active": True, "is_default": True, "created_at": "2023-01-02T00:00:00Z", "updated_at": "2023-01-02T00:00:00Z"},
        {"id": "1", "user_id": TEST_USER_ID, "organization_id": None, "name": "Template 1", "description": None, "template_type": "custom", "settings": {}, "is_active": True, "is_default": False, "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z"}
    ]
    # Correctly mock the chained calls
    mock_execute_result = MagicMock()
    mock_execute_result.data = mock_data
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.order.return_value.execute.return_value = mock_execute_result
    
    response = client.get("/style-templates/")
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["is_default"] == True # is_default is ordered first
    assert response.json()[0]["id"] == "2"

def test_get_style_templates_no_results(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.order.return_value.execute.return_value.data = []
    
    response = client.get("/style-templates/")
    assert response.status_code == 200
    assert response.json() == []

# --- GET /style-templates/{template_id} ---
def test_get_style_template_by_id_success(mock_supabase):
    mock_data = [{"id": "123", "user_id": TEST_USER_ID, "organization_id": None, "name": "Template A", "description": None, "template_type": "custom", "settings": {}, "is_active": True, "is_default": False, "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_data

    response = client.get("/style-templates/123")
    assert response.status_code == 200
    assert response.json()["id"] == "123"

def test_get_style_template_by_id_not_found(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    response = client.get("/style-templates/999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_get_style_template_by_id_access_denied(mock_supabase):
    # Template belongs to another user
    mock_template_data = [{"id": "456", "user_id": TEST_OTHER_USER_ID, "organization_id": None, "name": "Template B", "description": None, "template_type": "custom", "settings": {}, "is_active": True, "is_default": False, "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_template_data
    
    response = client.get("/style-templates/456")
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]

# --- POST /style-templates/ ---
def test_create_style_template_success(mock_supabase):
    mock_template_data = {"name": "New Template", "settings": {"font_size": 12}}
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
        "id": "new-uuid", "user_id": TEST_USER_ID, "organization_id": None, "name": "New Template", "description": None, "template_type": "custom", "settings": {}, "is_active": True, "is_default": False, "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z"
    }]

    response = client.post("/style-templates/", json=mock_template_data)
    assert response.status_code == 200
    assert response.json()["name"] == "New Template"
    assert mock_supabase.table.return_value.insert.call_args[0][0]["user_id"] == TEST_USER_ID

def test_create_style_template_org_insufficient_perms(mock_supabase):
    mock_template_data = {"name": "Org Template", "organization_id": TEST_ORG_ID}
    # Mocking user is a regular member
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{"role": "member"}]

    response = client.post("/style-templates/", json=mock_template_data)
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]

def test_create_style_template_org_admin_success(mock_supabase):
    mock_template_data = {"name": "Org Template", "organization_id": TEST_ORG_ID}
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{"role": "admin"}]
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
        "id": "new-uuid", "user_id": TEST_USER_ID, "organization_id": TEST_ORG_ID, "name": "Org Template", "description": None, "template_type": "custom", "settings": {}, "is_active": True, "is_default": False, "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z"
    }]

    response = client.post("/style-templates/", json=mock_template_data)
    assert response.status_code == 200
    assert response.json()["organization_id"] == TEST_ORG_ID

# --- PUT /style-templates/{template_id} ---
def test_update_style_template_success(mock_supabase):
    # Mock data with all required fields
    mock_existing = [{
        "id": "123", "user_id": TEST_USER_ID, "organization_id": None, "name": "Old Name", "description": "desc", "template_type": "custom", "settings": {}, "is_active": True, "is_default": False, "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z"
    }]
    mock_updated = [{
        "id": "123", "user_id": TEST_USER_ID, "organization_id": None, "name": "Updated Name", "description": "desc", "template_type": "custom", "settings": {}, "is_active": True, "is_default": False, "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z"
    }]

    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_existing
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = mock_updated

    update_data = {"name": "Updated Name"}
    response = client.put("/style-templates/123", json=update_data)

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"

def test_update_style_template_not_found(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    response = client.put("/style-templates/999", json={"name": "New Name"})
    assert response.status_code == 404

def test_update_style_template_access_denied(mock_supabase):
    # Template belongs to another user
    mock_existing = [{
        "id": "456", "user_id": TEST_OTHER_USER_ID, "organization_id": None, "name": "Old Name", "description": "desc", "template_type": "custom", "settings": {}, "is_active": True, "is_default": False, "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z"
    }]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_existing
    
    response = client.put("/style-templates/456", json={"name": "New Name"})
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]

def test_update_style_template_org_insufficient_perms(mock_supabase):
    # Template belongs to an organization, user is a member but not admin/owner
    mock_existing = [{
        "id": "789", "user_id": TEST_OTHER_USER_ID, "organization_id": TEST_ORG_ID, "name": "Old Org Name", "description": "desc", "template_type": "custom", "settings": {}, "is_active": True, "is_default": False, "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z"
    }]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_existing
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{"role": "member"}]
    
    response = client.put("/style-templates/789", json={"name": "New Name"})
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]

# --- DELETE /style-templates/{template_id} ---
def test_delete_style_template_success(mock_supabase):
    mock_existing = [{"id": "123", "user_id": TEST_USER_ID, "organization_id": None, "is_active": True, "name": "Template 1", "description": "desc", "template_type": "custom", "settings": {}, "is_default": False, "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_existing
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"is_active": False}]
    
    response = client.delete("/style-templates/123")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]
    # Verify soft delete
    mock_supabase.table.return_value.update.assert_called_with({"is_active": False})

def test_delete_style_template_not_found(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    response = client.delete("/style-templates/999")
    assert response.status_code == 404

def test_delete_style_template_access_denied(mock_supabase):
    mock_existing = [{"id": "456", "user_id": TEST_OTHER_USER_ID, "organization_id": None, "is_active": True, "name": "Template 2", "description": "desc", "template_type": "custom", "settings": {}, "is_default": False, "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_existing
    
    response = client.delete("/style-templates/456")
    assert response.status_code == 403

def test_delete_style_template_org_insufficient_perms(mock_supabase):
    mock_existing = [{"id": "789", "user_id": TEST_OTHER_USER_ID, "organization_id": TEST_ORG_ID, "is_active": True, "name": "Template 3", "description": "desc", "template_type": "custom", "settings": {}, "is_default": False, "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_existing
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{"role": "member"}]

    response = client.delete("/style-templates/789")
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]


# --- POST /style-templates/{template_id}/set-default ---
def test_set_default_template_success(mock_supabase):
    # Mock data with all required fields
    mock_existing = [{
        "id": "123", "user_id": TEST_USER_ID, "organization_id": None, "is_active": True, "is_default": False, "name": "T1", "description": "desc", "template_type": "custom", "settings": {}, "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z"
    }]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_existing
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"is_default": True}]
    
    response = client.post("/style-templates/123/set-default")
    assert response.status_code == 200
    assert "Default template updated successfully" in response.json()["message"]
    mock_supabase.table.return_value.update.assert_called_with({"is_default": True})

def test_set_default_template_not_found(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    response = client.post("/style-templates/999/set-default")
    assert response.status_code == 404