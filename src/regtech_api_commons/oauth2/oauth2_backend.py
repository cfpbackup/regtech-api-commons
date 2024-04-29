import logging
from typing import Coroutine, Any, Dict, List, Tuple
from fastapi import HTTPException
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    BaseUser,
    UnauthenticatedUser,
)
from fastapi.security import OAuth2AuthorizationCodeBearer
from starlette.requests import HTTPConnection

from regtech_api_commons.models.auth import AuthenticatedUser

from regtech_api_commons.oauth2.oauth2_admin import OAuth2Admin

log = logging.getLogger(__name__)


class BearerTokenAuthBackend(AuthenticationBackend):
    def __init__(self, token_bearer: OAuth2AuthorizationCodeBearer, oauth2_admin: OAuth2Admin) -> None:
        self.token_bearer = token_bearer
        self.oauth2_admin = oauth2_admin

    async def authenticate(self, conn: HTTPConnection) -> Coroutine[Any, Any, Tuple[AuthCredentials, BaseUser] | None]:
        try:
            log.error(f"Connection to OAuth2_backend {conn.url}")
            try:
                token = await self.token_bearer(conn)
            except HTTPException:
                return
            if not token:
                return AuthCredentials("unauthenticated"), UnauthenticatedUser()
            claims = self.oauth2_admin.get_claims(token)
            if claims is not None:
                auths = (
                    self.extract_nested(claims, "resource_access", "realm-management", "roles")
                    + self.extract_nested(claims, "resource_access", "account", "roles")
                    + ["authenticated"]
                )
                return AuthCredentials(auths), AuthenticatedUser.from_claim(claims)
        except HTTPException as e:
            log.error("failed to get claims", e, exc_info=True, stack_info=True)
        return AuthCredentials("unauthenticated"), UnauthenticatedUser()

    def extract_nested(self, data: Dict[str, Any], *keys: str) -> List[str]:
        _ele = data
        try:
            for key in keys:
                _ele = _ele[key]
            return _ele
        except KeyError:
            return []
