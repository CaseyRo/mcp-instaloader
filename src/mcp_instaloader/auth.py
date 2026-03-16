"""Authentication for the MCP server.

Supports two authentication modes simultaneously via MultiAuth:

1. **Keycloak JWT** (for OAuth clients authenticated via Keycloak):
   Validates JWT tokens issued by a Keycloak realm using the realm's
   JWKS endpoint for key discovery and rotation.

2. **Bearer token** (for Claude Code, n8n, and other direct clients):
   Simple static API key validation via Authorization: Bearer <key>.

Authentication is optional — only enabled when KEYCLOAK_ISSUER is set.
This keeps local development frictionless while securing production deployments.
"""

import hmac
import logging

from fastmcp.server.auth import (
    AccessToken,
    JWTVerifier,
    MultiAuth,
    TokenVerifier,
)

logger = logging.getLogger(__name__)


class BearerTokenVerifier(TokenVerifier):
    """Validates incoming requests against a static API key.

    Uses constant-time comparison to prevent timing attacks.
    """

    def __init__(self, api_key: str):
        super().__init__()
        self._api_key = api_key

    async def verify_token(self, token: str) -> AccessToken | None:
        if not hmac.compare_digest(token, self._api_key):
            logger.warning("Rejected request with invalid API key")
            return None

        return AccessToken(
            token=token,
            client_id="mcp-instaloader-bearer",
            scopes=["all"],
        )


def build_auth(
    *,
    keycloak_issuer: str,
    keycloak_audience: str = "mcp-instaloader",
    api_key: str | None = None,
) -> MultiAuth:
    """Build a MultiAuth provider combining Keycloak JWT + optional Bearer token.

    Args:
        keycloak_issuer: Keycloak realm issuer URL
            (e.g. https://auth.cdit-works.de/realms/cdit-mcp).
        keycloak_audience: Expected JWT audience claim.
        api_key: Optional static API key for bearer token auth.

    Returns:
        MultiAuth instance ready to pass to FastMCP(auth=...).
    """
    # Keycloak exposes JWKS at {issuer}/protocol/openid-connect/certs
    jwks_uri = f"{keycloak_issuer.rstrip('/')}/protocol/openid-connect/certs"

    jwt_verifier = JWTVerifier(
        jwks_uri=jwks_uri,
        issuer=keycloak_issuer,
        audience=keycloak_audience,
    )

    verifiers: list[TokenVerifier] = []
    if api_key:
        verifiers.append(BearerTokenVerifier(api_key))

    return MultiAuth(server=jwt_verifier, verifiers=verifiers)
