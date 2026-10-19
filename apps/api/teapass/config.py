from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TEAPASS_", env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://teapass:local-only@localhost:55432/teapass"
    # Bind signatures to one deployment, preventing cross-environment command replay.
    deployment_id: str = Field(default="teapass-local", min_length=1, max_length=100)
    oidc_issuer: str = "http://localhost:8080/realms/teapass"
    oidc_audience: str = "teapass-api"
    oidc_jwks_url: str = "http://localhost:8080/realms/teapass/protocol/openid-connect/certs"
    jwt_public_key: str | None = None  # Test-only, no shared-secret auth or development bypass.
    token_max_lifetime_seconds: int = Field(default=900, ge=60, le=3600)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    midnight_network: Literal["undeployed", "preview", "preprod", "mainnet"] = "undeployed"
    midnight_verifier_url: str | None = None
    midnight_indexer_url: str = "http://127.0.0.1:8088/api/v4/graphql"
    midnight_node_url: str = "http://127.0.0.1:9944"
    midnight_contract_address: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    max_request_bytes: int = Field(default=131072, ge=1024, le=1048576)

    @model_validator(mode="after")
    def validate_security(self):
        if not self.database_url.startswith("postgresql+psycopg://"):
            raise ValueError("PostgreSQL with psycopg is required")
        if self.jwt_public_key and self.environment != "test":
            raise ValueError(
                "Static verification keys are restricted to tests; configure OIDC JWKS"
            )
        if self.environment == "production":
            if self.midnight_contract_address and (
                self.midnight_network == "undeployed"
                or not self.midnight_indexer_url.startswith("https://")
                or not self.midnight_node_url.startswith("https://")
            ):
                raise ValueError(
                    "Production chain reconciliation requires HTTPS and a public network"
                )
            if self.deployment_id == "teapass-local":
                raise ValueError("Production requires a unique deployment_id")
            if not all(
                url.startswith("https://")
                for url in [self.oidc_issuer, self.oidc_jwks_url, *self.cors_origins]
            ):
                raise ValueError("Production identity and CORS origins require HTTPS")
            if "*" in self.cors_origins or "local-only" in self.database_url:
                raise ValueError("Production requires explicit origins and database credentials")
        return self
