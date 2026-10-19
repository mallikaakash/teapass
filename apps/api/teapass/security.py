import base64
import hashlib
from datetime import UTC, datetime

import jwt
import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import HTTPException

from teapass.config import Settings
from teapass.models import Actor
from teapass.schemas import Command


def canonical(value: dict) -> bytes:
    return rfc8785.dumps(value)


def digest(value: dict) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def command_bytes(command: Command) -> bytes:
    return b"TEAPASS_OPERATION_V1\x00" + canonical(command.model_dump(mode="json"))


def verify_command(command: Command, signature: str, actor: Actor, settings: Settings):
    if (
        command.actor_id != actor.id
        or command.org_id != actor.org_id
        or command.deployment_id != settings.deployment_id
    ):
        raise HTTPException(403, "COMMAND_AUTHORITY_MISMATCH")
    if (command.occurred_at - datetime.now(UTC)).total_seconds() > 300:
        raise HTTPException(422, "EVENT_TIME_IN_FUTURE")
    try:
        Ed25519PublicKey.from_public_bytes(actor.signing_public_key).verify(
            base64.b64decode(signature, validate=True), command_bytes(command)
        )
    except (InvalidSignature, ValueError):
        raise HTTPException(403, "INVALID_ACTOR_SIGNATURE") from None


class TokenVerifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.jwks = jwt.PyJWKClient(
            settings.oidc_jwks_url, cache_jwk_set=True, lifespan=60, timeout=5
        )

    def subject(self, token: str) -> str:
        try:
            key = self.settings.jwt_public_key or self.jwks.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.settings.oidc_audience,
                issuer=self.settings.oidc_issuer,
                options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            )
            # No roles/orgs from bearer claims are trusted; enrollment is authoritative.
            if (
                not isinstance(claims["sub"], str)
                or not claims["sub"]
                or type(claims["exp"]) is not int
                or type(claims["iat"]) is not int
                or not 0 < claims["exp"] - claims["iat"] <= self.settings.token_max_lifetime_seconds
            ):
                raise jwt.InvalidTokenError()
            return claims["sub"]
        except jwt.PyJWKClientConnectionError:
            raise HTTPException(503, "IDENTITY_PROVIDER_UNAVAILABLE") from None
        except (jwt.PyJWTError, ValueError, TypeError):
            raise HTTPException(
                401, "INVALID_ACCESS_TOKEN", headers={"WWW-Authenticate": "Bearer"}
            ) from None


def batch_reference(deployment_id: str, batch_id) -> str:
    return hashlib.sha256(
        b"TEAPASS_BATCH_V1\x00"
        + deployment_id.encode("utf-8")
        + b"\x00"
        + str(batch_id).encode("ascii")
    ).hexdigest()
