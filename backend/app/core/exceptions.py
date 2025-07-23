# -*- coding: utf-8 -*-
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import traceback

# Agents SDKの例外もインポートしておく
from agents import AgentsException, MaxTurnsExceeded, ModelBehaviorError, UserError

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """FastAPIのリクエストバリデーションエラーハンドラ"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )

async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Pydanticのバリデーションエラーハンドラ"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

async def agents_exception_handler(request: Request, exc: AgentsException):
    """Agents SDKの共通例外ハンドラ"""
    # エラーの種類に応じてステータスコードやメッセージを調整可能
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = f"Agent processing error: {type(exc).__name__} - {str(exc)}"

    if isinstance(exc, MaxTurnsExceeded):
        status_code = status.HTTP_400_BAD_REQUEST
        detail = f"Processing exceeded maximum turns: {str(exc)}"
    elif isinstance(exc, ModelBehaviorError):
        status_code = status.HTTP_502_BAD_GATEWAY
        detail = f"Model behavior error: {str(exc)}"
    elif isinstance(exc, UserError):
        status_code = status.HTTP_400_BAD_REQUEST # SDK利用側のエラー
        detail = f"Configuration or usage error: {str(exc)}"

    print(f"Error during agent processing: {detail}") # ログ出力
    print(traceback.format_exc())

    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """その他の予期せぬ例外ハンドラ"""
    print(f"Unhandled exception occurred: {type(exc).__name__} - {str(exc)}")
    print(traceback.format_exc()) # スタックトレースをログに出力
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"An unexpected internal server error occurred: {type(exc).__name__}"},
    )

# 例外ハンドラを登録するための辞書
exception_handlers = {
    RequestValidationError: validation_exception_handler,
    ValidationError: pydantic_validation_exception_handler, # Pydantic単体のエラーも捕捉
    AgentsException: agents_exception_handler, # Agents SDKの基底例外
    Exception: generic_exception_handler, # その他の全ての例外
}

