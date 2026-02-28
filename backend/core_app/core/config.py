from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "FusionEMS Core"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    @field_validator("debug", mode="before")
    @classmethod
    def _coerce_debug(cls, v: object) -> bool:
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes")
        return bool(v)

    database_url: str = Field(default="")
    api_base_url: str = Field(default="https://api.fusionemsquantum.com")

    system_tenant_id: str = Field(
        default="",
        description=(
            "Deterministic UUID for system-level events (webhook receipts, etc.) "
            "that have no user tenant. Must be set in all environments."
        ),
    )

    jwt_secret_key: str = Field(default="")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=60)

    redis_url: str = Field(default="")
    s3_bucket_docs: str = Field(default="")
    s3_bucket_exports: str = Field(default="")

    # Integrations (injected from Secrets Manager via ECS task definition env vars)
    openai_api_key: str = Field(default="")
    stripe_secret_key: str = Field(default="")
    stripe_webhook_secret: str = Field(default="")
    telnyx_api_key: str = Field(default="")
    telnyx_from_number: str = Field(default="")
    telnyx_messaging_profile_id: str = Field(default="")
    officeally_sftp_host: str = Field(default="")
    officeally_sftp_port: int = Field(default=22)
    officeally_sftp_username: str = Field(default="")
    officeally_sftp_password: str = Field(default="")
    officeally_sftp_remote_dir: str = Field(default="/")
    lob_api_key: str = Field(default="")
    lob_webhook_secret: str = Field(default="")
    ses_from_email: str = Field(default="noreply@fusionemsquantum.com")

    # Microsoft Graph (application permissions - client credentials flow)
    graph_tenant_id: str = Field(default="", description="Azure AD tenant ID")
    graph_client_id: str = Field(default="", description="Entra app client ID")
    graph_client_secret: str = Field(default="", description="Entra app client secret (from Secrets Manager)")
    graph_founder_email: str = Field(default="", description="Founder mailbox UPN - used for all Graph calls")

    # Microsoft Entra user login (authorization code flow)
    microsoft_redirect_uri: str = Field(
        default="https://api.fusionemsquantum.com/api/v1/auth/microsoft/callback",
        description="Canonical redirect URI registered in Entra app registration",
    )
    microsoft_post_login_url: str = Field(
        default="https://app.fusionemsquantum.com/dashboard",
        description="Frontend URL to redirect to after successful Microsoft login",
    )

    ses_configuration_set: str = Field(default="")
    aws_region: str = Field(default="")

    # Telnyx webhook verification + IVR
    telnyx_public_key: str = Field(default="", description="Base64-encoded Ed25519 public key from Telnyx portal")
    telnyx_webhook_tolerance_seconds: int = Field(default=300)
    ivr_audio_base_url: str = Field(default="", description="S3 or CDN base URL for pre-generated IVR WAV prompts")
    s3_bucket_audio: str = Field(default="")
    fax_classify_queue_url: str = Field(default="")

    # Cognito (AWS-native identity)
    auth_mode: str = Field(default="local", description="local|cognito")
    cognito_region: str = Field(default="")
    cognito_user_pool_id: str = Field(default="")
    cognito_app_client_id: str = Field(default="")
    cognito_issuer: str = Field(default="")

    # OPA (optional policy engine)
    opa_url: str = Field(default="", description="OPA HTTP endpoint, e.g. http://opa:8181")
    opa_policy_path: str = Field(default="v1/data/fusionems/allow")

    # SQS queues (Lambda workers)
    lob_events_queue_url: str = Field(default="")
    stripe_events_queue_url: str = Field(default="")
    neris_pack_import_queue_url: str = Field(default="")
    neris_pack_compile_queue_url: str = Field(default="")
    neris_export_queue_url: str = Field(default="")

    # DynamoDB tables (Lambda workers) - no default; must be explicitly set per environment
    statements_table: str = Field(default="")
    lob_events_table: str = Field(default="")
    stripe_events_table: str = Field(default="")
    tenants_table: str = Field(default="")

    # GitHub integration (Founder Copilot)
    github_token: str = Field(default="", description="GitHub PAT or Actions token for workflow dispatch")
    github_owner: str = Field(default="", description="GitHub org or username")
    github_repo: str = Field(default="FusionEMS-Core", description="GitHub repository name")

    # Observability
    otel_enabled: bool = Field(default=True)
    otel_service_name: str = Field(default="fusionems-core-backend")
    otel_exporter_otlp_endpoint: str = Field(default="")
    metrics_enabled: bool = Field(default=True)

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        env = self.environment.lower()
        if env in ("production", "prod", "staging"):
            _REQUIRED: list[tuple[str, str]] = [
                ("database_url",                    "DATABASE_URL"),
                ("jwt_secret_key",                  "JWT_SECRET_KEY"),
                ("stripe_secret_key",               "STRIPE_SECRET_KEY"),
                ("stripe_webhook_secret",           "STRIPE_WEBHOOK_SECRET"),
                ("lob_api_key",                     "LOB_API_KEY"),
                ("lob_webhook_secret",              "LOB_WEBHOOK_SECRET"),
                ("telnyx_api_key",                  "TELNYX_API_KEY"),
                ("telnyx_from_number",              "TELNYX_FROM_NUMBER"),
                ("telnyx_public_key",               "TELNYX_PUBLIC_KEY"),
                ("ivr_audio_base_url",              "IVR_AUDIO_BASE_URL"),
                ("fax_classify_queue_url",          "FAX_CLASSIFY_QUEUE_URL"),
                ("aws_region",                      "AWS_REGION"),
                ("system_tenant_id",                "SYSTEM_TENANT_ID"),
                ("lob_events_queue_url",            "LOB_EVENTS_QUEUE_URL"),
                ("stripe_events_queue_url",         "STRIPE_EVENTS_QUEUE_URL"),
                ("neris_pack_import_queue_url",      "NERIS_PACK_IMPORT_QUEUE_URL"),
                ("neris_pack_compile_queue_url",     "NERIS_PACK_COMPILE_QUEUE_URL"),
                ("neris_export_queue_url",           "NERIS_EXPORT_QUEUE_URL"),
                ("statements_table",                "STATEMENTS_TABLE"),
                ("lob_events_table",                "LOB_EVENTS_TABLE"),
                ("stripe_events_table",             "STRIPE_EVENTS_TABLE"),
                ("tenants_table",                   "TENANTS_TABLE"),
                ("graph_tenant_id",                 "GRAPH_TENANT_ID"),
                ("graph_client_id",                 "GRAPH_CLIENT_ID"),
                ("graph_client_secret",             "GRAPH_CLIENT_SECRET"),
                ("graph_founder_email",             "GRAPH_FOUNDER_EMAIL"),
            ]
            missing = [
                env_name
                for attr, env_name in _REQUIRED
                if not getattr(self, attr, "")
            ]
            if missing:
                raise ValueError(
                    f"The following required environment variables are not set "
                    f"for environment '{env}': {', '.join(missing)}. "
                    "All secrets must be injected from AWS Secrets Manager via the ECS task definition."
                )
            if self.jwt_secret_key in ("change-me", "changeme", "secret"):
                raise ValueError(
                    "JWT_SECRET_KEY is set to a known insecure placeholder value. "
                    "Generate a cryptographically random key and inject it from Secrets Manager."
                )
            if self.auth_mode.lower() == "local":
                raise ValueError(
                    f"AUTH_MODE is 'local' in environment '{env}'. "
                    "Set AUTH_MODE=cognito for staging and production deployments."
                )
        return self

    @field_validator("graph_founder_email")
    @classmethod
    def _validate_graph_founder_email(cls, v: str) -> str:
        if v and "@" not in v:
            raise ValueError(
                f"GRAPH_FOUNDER_EMAIL must be a valid UPN (email address), got: {v!r}"
            )
        return v

    @field_validator("system_tenant_id")
    @classmethod
    def _validate_system_tenant_id(cls, v: str) -> str:
        if not v:
            return v
        import uuid as _uuid
        try:
            _uuid.UUID(v)
        except ValueError as exc:
            raise ValueError(
                f"SYSTEM_TENANT_ID must be a valid UUID, got: {v!r}"
            ) from exc
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
