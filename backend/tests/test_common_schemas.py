# -*- coding: utf-8 -*-
"""
Test suite for backend/app/common/schemas.py (Pydantic Models and Enums)
"""
import pytest
from pydantic import ValidationError, BaseModel
from app.common.schemas import (
    UserInputType, 
    UserInputRequestPayload, 
    ErrorPayload, 
    WebSocketMessage, 
    ServerEventMessage, 
    ClientResponseMessage,
    BasePayload # payload_to_dictのテストに使用
)

# ----------------------------------------------------
# 1. Enumのテスト: UserInputType
# ----------------------------------------------------

def test_user_input_type_enum_values():
    """
    UserInputTypeのEnumが意図した値を保持していることを確認する
    """
    expected_values = {
        "SELECT_PERSONA": "select_persona",
        "SELECT_THEME": "select_theme",
        "APPROVE_PLAN": "approve_plan",
        "APPROVE_OUTLINE": "approve_outline",
        "REGENERATE": "regenerate",
        "EDIT_AND_PROCEED": "edit_and_proceed",
        "EDIT_PERSONA": "edit_persona",
        "EDIT_THEME": "edit_theme",
        "EDIT_PLAN": "edit_plan",
        "EDIT_OUTLINE": "edit_outline",
        "EDIT_GENERIC": "edit_generic",
    }
    
    for name, value in expected_values.items():
        assert getattr(UserInputType, name).value == value

# ----------------------------------------------------
# 2. BasePayloadを継承したモデルのテスト
# ----------------------------------------------------

def test_user_input_request_payload_success():
    """
    UserInputRequestPayload が正常なデータで初期化できることを確認する
    """
    data = {
        "request_type": UserInputType.SELECT_PERSONA.value,
        "data": {"available_personas": ["p1", "p2"]}
    }
    
    payload = UserInputRequestPayload(**data)
    
    assert payload.request_type == UserInputType.SELECT_PERSONA
    assert isinstance(payload.data, dict)
    assert payload.data["available_personas"] == ["p1", "p2"]

def test_user_input_request_payload_fail_invalid_type():
    """
    UserInputRequestPayload が不正な request_type で初期化できないことを確認する
    """
    data = {
        "request_type": "invalid_type",
        "data": {}
    }
    
    with pytest.raises(ValidationError):
        UserInputRequestPayload(**data)

def test_error_payload_success():
    """
    ErrorPayload が正常なデータで初期化できることを確認する
    """
    data = {
        "step": "OUTLINE_GENERATION",
        "error_message": "OpenAI API connection failed."
    }
    
    payload = ErrorPayload(**data)
    
    assert payload.step == "OUTLINE_GENERATION"
    assert "failed" in payload.error_message

def test_error_payload_fail_missing_field():
    """
    ErrorPayload の必須フィールドが欠落している場合に検証エラーになることを確認する
    """
    # error_messageが欠落
    data = {"step": "PLANNING"}
    
    with pytest.raises(ValidationError):
        ErrorPayload(**data)

# ----------------------------------------------------
# 3. WebSocketMessageとValidatorのテスト
# ----------------------------------------------------

def test_websocket_message_payload_validator_model_to_dict():
    """
    WebSocketMessageのバリデータが、payloadがPydanticモデルの場合にdictに変換することを確認する
    """
    # BasePayloadを継承したダミーモデル
    class DummyPayload(BasePayload):
        value: str = "test"
        number: int = 123
        
    data = {
        "type": "server_event",
        "payload": DummyPayload(value="actual_value")
    }
    
    # WebSocketMessageの初期化時に、payload_to_dictバリデータが実行される
    msg = WebSocketMessage(**data)
    
    # payloadが dict に変換されていることを確認
    assert isinstance(msg.payload, dict)
    assert msg.payload['value'] == "actual_value"
    assert msg.payload['number'] == 123 # デフォルト値も含まれている

def test_websocket_message_payload_validator_dict_stays_dict():
    """
    WebSocketMessageのバリデータが、payloadが既にdictの場合にそのまま保持することを確認する
    """
    dict_payload = {"status": "processing", "progress": 50}
    data = {
        "type": "server_event",
        "payload": dict_payload
    }
    
    msg = WebSocketMessage(**data)
    
    assert msg.payload == dict_payload
    assert isinstance(msg.payload, dict)


def test_server_event_message_success():
    """
    ServerEventMessage が正常なデータで初期化できることを確認する
    """
    data = {
        "type": "server_event",
        "payload": {"status": "done", "result": "article_id_123"}
    }
    msg = ServerEventMessage(**data)
    
    assert msg.type == "server_event"
    assert msg.payload["status"] == "done"

def test_client_response_message_success():
    """
    ClientResponseMessage が正常なデータで初期化できることを確認する
    """
    data = {
        "type": "client_response",
        "response_type": UserInputType.SELECT_PERSONA.value,
        "payload": {"selected_persona_id": 42}
    }
    msg = ClientResponseMessage(**data)
    
    assert msg.type == "client_response"
    assert msg.response_type == UserInputType.SELECT_PERSONA
    assert msg.payload["selected_persona_id"] == 42
    
def test_client_response_message_fail_missing_response_type():
    """
    ClientResponseMessage の必須フィールドが欠落している場合に検証エラーになることを確認する
    """
    data = {
        "type": "client_response",
        "payload": {}
        # response_type が欠落
    }
    
    with pytest.raises(ValidationError):
        ClientResponseMessage(**data)