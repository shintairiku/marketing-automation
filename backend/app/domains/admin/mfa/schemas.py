# -*- coding: utf-8 -*-
"""
Admin MFA (TOTP) schemas
"""
from pydantic import BaseModel


class TotpSetupInitResponse(BaseModel):
    secret_uri: str
    backup_codes: list[str]


class TotpSetupConfirmRequest(BaseModel):
    code: str


class TotpVerifyRequest(BaseModel):
    code: str


class TotpVerifyResponse(BaseModel):
    success: bool
    message: str


class TotpStatusResponse(BaseModel):
    is_setup: bool
    is_confirmed: bool
    backup_codes_remaining: int


class TotpResetResponse(BaseModel):
    success: bool
    message: str
