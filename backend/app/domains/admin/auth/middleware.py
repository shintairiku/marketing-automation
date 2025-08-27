# -*- coding: utf-8 -*-
from typing import List, Optional
import logging
import re

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.domains.admin.auth.clerk_validator import (
    ClerkOrganizationValidator,
    AdminUser,
)
from app.domains.admin.auth.exceptions import (
    InvalidJWTTokenError,
    OrganizationMembershipRequiredError,
    InsufficientPermissionsError,
)


logger = logging.getLogger(__name__)


class AdminAuthMiddleware(BaseHTTPMiddleware):
    """
    /admin 配下などの保護されたパスに対して、Clerk の管理者認証を行うミドルウェア。

    - Authorization: Bearer <JWT> を検証
    - 管理者組織所属 + ロール（owner/admin）を確認
    - 成功時は request.state.admin_user に AdminUser を格納
    - 失敗時は 401/403/500 を返却
    """

    def __init__(
        self,
        app,
        protected_prefixes: Optional[List[str]] = None,
        protected_regexes: Optional[List[str]] = None,
        audit_log: bool = True,
    ):
        super().__init__(app)
        self.protected_prefixes = protected_prefixes or ["/admin"]
        self._protected_regexes = [re.compile(p) for p in (protected_regexes or [])]
        self.audit_log = audit_log
        self.validator = ClerkOrganizationValidator()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        should_protect = any(path.startswith(prefix) for prefix in self.protected_prefixes)
        if not should_protect and self._protected_regexes:
            should_protect = any(r.match(path) for r in self._protected_regexes)

        if should_protect:
            auth_header = request.headers.get("authorization")
            if not auth_header:
                return JSONResponse(status_code=401, content={"detail": "Admin authorization header required"})

            token = auth_header[7:] if auth_header.lower().startswith("bearer ") else auth_header

            try:
                admin_user: AdminUser = self.validator.validate_token_and_extract_admin_user(token)
                request.state.admin_user = admin_user

                if self.audit_log:
                    logger.info(
                        f"[ADMIN_AUDIT] user={admin_user.user_id} method={request.method} path={path}"
                    )

            except InvalidJWTTokenError as e:
                return JSONResponse(status_code=401, content={"detail": f"Invalid admin token: {e.message}"})
            except OrganizationMembershipRequiredError:
                return JSONResponse(status_code=403, content={"detail": "Admin organization membership required"})
            except InsufficientPermissionsError as e:
                return JSONResponse(status_code=403, content={"detail": e.message})
            except Exception as e:
                logger.exception("[ADMIN_AUTH] Unexpected error in middleware")
                return JSONResponse(status_code=500, content={"detail": "Admin authentication system error"})

        return await call_next(request)


