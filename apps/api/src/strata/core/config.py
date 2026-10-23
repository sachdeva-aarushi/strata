from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "STRATA"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Database: defaults to local SQLite for rapid testing & zero-setup local runs,
    # but seamlessly switches to Supabase/PostgreSQL when DATABASE_URL is set.
    DATABASE_URL: str = "sqlite:///./strata.db"
    DATABASE_CONNECT_TIMEOUT: int = 10

    # Supabase Credentials & Configuration
    SUPABASE_URL: Optional[str] = None
    SUPABASE_PUBLISHABLE_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_DB_PASSWORD: Optional[str] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: Optional[str]) -> str:
        if not v or not str(v).strip():
            return "sqlite:///./strata.db"
        val = str(v).strip()
        # Normalizes postgres:// to postgresql:// for SQLAlchemy compatibility
        if val.startswith("postgres://"):
            val = "postgresql://" + val[len("postgres://"):]

        # Handle unencoded '@' characters inside passwords (e.g. postgres:pass@word@host:5432/db)
        if val.startswith("postgresql://") and val.count("@") > 1:
            try:
                from urllib.parse import quote_plus
                scheme_prefix = "postgresql://"
                rest = val[len(scheme_prefix):]
                # The last '@' reliably separates userinfo from host
                userinfo, host_and_rest = rest.rsplit("@", 1)
                if ":" in userinfo:
                    username, password = userinfo.split(":", 1)
                    val = f"{scheme_prefix}{username}:{quote_plus(password)}@{host_and_rest}"
            except Exception:
                pass

        return val

    @field_validator("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_DB_PASSWORD", mode="before")
    @classmethod
    def clean_string_settings(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            cleaned = v.strip()
            return cleaned if cleaned else None
        return v

    @property
    def effective_database_url(self) -> str:
        """Returns the active database URL, auto-constructing Supabase URL if credentials provided."""
        # If DATABASE_URL is explicitly set to PostgreSQL/non-sqlite, use it directly
        if self.DATABASE_URL and not self.DATABASE_URL.startswith("sqlite"):
            return self.DATABASE_URL
        # If SUPABASE_URL and SUPABASE_DB_PASSWORD are provided, derive direct Supabase connection URL
        if self.SUPABASE_URL and self.SUPABASE_DB_PASSWORD:
            from urllib.parse import quote_plus, urlparse
            parsed = urlparse(self.SUPABASE_URL)
            host_parts = parsed.netloc.split(".")
            if host_parts:
                project_ref = host_parts[0]
                encoded_pw = quote_plus(self.SUPABASE_DB_PASSWORD)
                return f"postgresql://postgres:{encoded_pw}@db.{project_ref}.supabase.co:5432/postgres"
        return self.DATABASE_URL

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v  # type: ignore
        raise ValueError(v)

    # Security & Auth
    JWT_SECRET: str = "change-this-in-production-to-a-secure-random-secret-key-32-bytes"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Testing / Mock Settings
    MOCK_AUTH_ENABLED: bool = True

    # ProofPath qualification service (owned by the qualification team)
    PROOFPATH_BASE_URL: str = "http://localhost:8001"
    PROOFPATH_TIMEOUT_SECONDS: float = 5.0
    # When True, ProofPath outages/timeouts/bad payloads return a clearly marked mock result
    # instead of an error. Intended for offline development and tests only.
    PROOFPATH_MOCK_FALLBACK: bool = False

    # -------------------------------------------------------------------------
    # LLM Provider (advisory role: synthesis and explanation only)
    # -------------------------------------------------------------------------
    # Supported values: "openai", "azure_openai"
    # When unset or empty the FakeLLMProvider is used (no external calls).
    LLM_PROVIDER: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: Optional[str] = None
    # Optional override for Azure OpenAI or self-hosted endpoints
    LLM_BASE_URL: Optional[str] = None
    LLM_TIMEOUT_SECONDS: float = 20.0

    @field_validator(
        "LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL", "LLM_BASE_URL",
        mode="before",
    )
    @classmethod
    def clean_optional_string(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            cleaned = v.strip()
            return cleaned if cleaned else None
        return v

    @property
    def llm_configured(self) -> bool:
        """True when a real LLM provider is configured and has a non-empty API key."""
        return bool(self.LLM_PROVIDER and self.LLM_API_KEY)

    # -------------------------------------------------------------------------
    # TinyFish — web search and page-fetch provider
    # -------------------------------------------------------------------------
    # Obtain a key from https://agent.tinyfish.ai/api-keys
    TINYFISH_API_KEY: Optional[str] = None
    TINYFISH_TIMEOUT_SECONDS: float = 15.0
    TINYFISH_MAX_SEARCH_RESULTS: int = 5

    @field_validator("TINYFISH_API_KEY", mode="before")
    @classmethod
    def clean_tinyfish_key(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            cleaned = v.strip()
            return cleaned if cleaned else None
        return v

    @property
    def tinyfish_configured(self) -> bool:
        """True when a TinyFish API key is available."""
        return bool(self.TINYFISH_API_KEY)


settings = Settings()
