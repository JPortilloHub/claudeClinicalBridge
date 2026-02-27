"""
Configuration management using Pydantic Settings.

Provides type-safe, environment-aware configuration for the Clinical Bridge application.
All settings are loaded from environment variables or .env file.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = "development"

    # Anthropic Claude API
    anthropic_api_key: str = Field(..., description="Anthropic API key for Claude")
    claude_model: str = Field(
        default="claude-opus-4-6",
        description="Claude model to use",
    )

    # Epic FHIR Sandbox
    epic_client_id: str = Field(default="", description="Epic FHIR client ID")
    epic_client_secret: str = Field(default="", description="Epic FHIR client secret")
    epic_fhir_base_url: str = Field(
        default="https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4",
        description="Epic FHIR base URL",
    )
    epic_auth_url: str = Field(
        default="https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token",
        description="Epic OAuth token endpoint",
    )
    epic_private_key_path: str = Field(
        default="",
        description="Path to JWT private key for Epic backend services auth",
    )

    # Oracle Health (Cerner) Sandbox
    oracle_client_id: str = Field(default="", description="Oracle Health client ID")
    oracle_client_secret: str = Field(default="", description="Oracle Health client secret")
    oracle_fhir_base_url: str = Field(
        default="https://fhir-ehr-code.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d",
        description="Oracle Health FHIR base URL",
    )
    oracle_auth_url: str = Field(
        default="https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d/protocols/oauth2/profiles/smart-v1/token",  # noqa: E501
        description="Oracle Health OAuth token endpoint",
    )
    oracle_private_key_path: str = Field(
        default="",
        description="Path to JWT private key for Oracle Health backend services auth",
    )

    # Vector Database (Qdrant)
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant server URL",
    )
    qdrant_api_key: str | None = Field(
        default=None,
        description="Qdrant API key (optional for local)",
    )
    qdrant_collection_icd10: str = Field(
        default="icd10_codes",
        description="Qdrant collection name for ICD-10 codes",
    )
    qdrant_collection_cpt: str = Field(
        default="cpt_codes",
        description="Qdrant collection name for CPT codes",
    )

    # Embeddings Model
    embeddings_model: str = Field(
        default="dmis-lab/biobert-base-cased-v1.2",
        description="Sentence transformer model for embeddings",
    )
    embeddings_dimension: int = Field(
        default=768,
        description="Embedding vector dimension",
    )
    embeddings_batch_size: int = Field(
        default=32,
        description="Batch size for embedding generation",
    )
    embeddings_cache_dir: str = Field(
        default="./models",
        description="Directory to cache embedding models",
    )

    # Database (Payer Policies)
    database_url: str = Field(
        default="sqlite:///./data/policies.db",
        description="Database URL for payer policies",
    )

    # PostgreSQL (Workflow Persistence)
    postgres_host: str = Field(
        default="localhost",
        description="PostgreSQL host",
    )
    postgres_port: int = Field(
        default=5433,
        description="PostgreSQL port",
    )
    postgres_user: str = Field(
        default="clinical_user",
        description="PostgreSQL user",
    )
    postgres_password: str = Field(
        default="clinical_password_change_in_production",
        description="PostgreSQL password",
    )
    postgres_db: str = Field(
        default="clinical_bridge",
        description="PostgreSQL database name",
    )

    # Redis (Future Caching)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis server URL for caching",
    )
    redis_enabled: bool = Field(
        default=False,
        description="Enable Redis caching",
    )

    # Security and Encryption
    encryption_key_path: str = Field(
        default="./config/encryption.key",
        description="Path to encryption key file",
    )
    secret_key: str = Field(
        default="change_this_to_random_secret_key_min_32_chars",
        min_length=32,
        description="Secret key for JWT and session management",
    )

    # HIPAA Compliance
    audit_log_path: str = Field(
        default="./logs/audit.log",
        description="Path to HIPAA audit log file",
    )
    audit_log_retention_days: int = Field(
        default=2555,  # 7 years
        description="Audit log retention period in days (HIPAA requires 7 years)",
    )
    phi_redaction_enabled: bool = Field(
        default=True,
        description="Enable PHI redaction in logs",
    )
    phi_redaction_method: Literal["mask", "hash", "remove"] = Field(
        default="mask",
        description="PHI redaction method",
    )

    # Evaluation
    evaluation_mode: bool = Field(
        default=False,
        description="Enable evaluation mode",
    )
    golden_dataset_path: str = Field(
        default="tests/evaluation/test_cases/golden_dataset.json",
        description="Path to golden dataset for evaluation",
    )
    evaluation_output_dir: str = Field(
        default="./evaluation_results",
        description="Directory for evaluation results",
    )

    # MCP Servers
    mcp_server_host: str = Field(
        default="localhost",
        description="MCP server host",
    )
    mcp_server_port_epic: int = Field(
        default=8001,
        description="Epic FHIR MCP server port",
    )
    mcp_server_port_oracle: int = Field(
        default=8002,
        description="Oracle Health MCP server port",
    )
    mcp_server_port_knowledge: int = Field(
        default=8003,
        description="Medical Knowledge MCP server port",
    )
    mcp_server_port_policy: int = Field(
        default=8004,
        description="Payer Policy MCP server port",
    )

    # Agent Configuration
    agent_timeout_seconds: int = Field(
        default=120,
        description="Agent execution timeout in seconds",
    )
    agent_max_retries: int = Field(
        default=3,
        description="Maximum number of retries for agent operations",
    )
    agent_latency_target_seconds: int = Field(
        default=30,
        description="Target latency for end-to-end workflow in seconds",
    )
    agent_max_tokens: int = Field(
        default=16384,
        description="Maximum tokens for agent LLM responses",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    log_format: Literal["json", "text"] = Field(
        default="json",
        description="Log output format",
    )
    log_file_path: str = Field(
        default="./logs/application.log",
        description="Application log file path",
    )
    log_file_max_bytes: int = Field(
        default=10485760,  # 10MB
        description="Maximum log file size in bytes before rotation",
    )
    log_file_backup_count: int = Field(
        default=5,
        description="Number of backup log files to keep",
    )

    # FastAPI (Future Web API)
    api_host: str = Field(
        default="0.0.0.0",  # nosec B104 - configurable via API_HOST env var
        description="API server host",
    )
    api_port: int = Field(
        default=8000,
        description="API server port",
    )
    api_reload: bool = Field(
        default=True,
        description="Enable auto-reload for development",
    )
    api_workers: int = Field(
        default=1,
        description="Number of API worker processes",
    )

    # Development Settings
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    testing: bool = Field(
        default=False,
        description="Enable testing mode",
    )
    mock_fhir_enabled: bool = Field(
        default=False,
        description="Use mock FHIR data instead of real sandbox",
    )

    # Feature Flags
    enable_clinical_doc_agent: bool = Field(
        default=True,
        description="Enable Clinical Documentation Agent",
    )
    enable_medical_coding_agent: bool = Field(
        default=True,
        description="Enable Medical Coding Agent",
    )
    enable_compliance_agent: bool = Field(
        default=True,
        description="Enable Compliance Agent",
    )
    enable_prior_auth_agent: bool = Field(
        default=True,
        description="Enable Prior Authorization Agent",
    )
    enable_qa_agent: bool = Field(
        default=True,
        description="Enable Quality Assurance Agent",
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting."""
        if v not in ["development", "staging", "production"]:
            raise ValueError(
                f"Invalid environment: {v}. Must be 'development', 'staging', or 'production'"
            )
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key is strong enough."""
        if len(v) < 32:
            raise ValueError("secret_key must be at least 32 characters long")
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Validate production-specific requirements."""
        if self.environment == "production":
            # Fail if using default secret key in production
            if self.secret_key == "change_this_to_random_secret_key_min_32_chars":  # nosec B105 - detecting use of default placeholder, not a real password
                raise ValueError(
                    "Cannot use default secret_key in production environment! "
                    "Set a secure SECRET_KEY in your .env file."
                )
        elif self.secret_key == "change_this_to_random_secret_key_min_32_chars":  # nosec B105 - detecting use of default placeholder, not a real password
            # Warn in development/staging
            import warnings

            warnings.warn(
                "Using default secret_key! Please set a secure SECRET_KEY in .env file",
                stacklevel=2,
            )
        return self

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def logs_dir(self) -> Path:
        """Get logs directory path."""
        return Path(self.log_file_path).parent

    @property
    def data_dir(self) -> Path:
        """Get data directory path."""
        return Path("./data")

    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        directories = [
            self.logs_dir,
            self.data_dir,
            self.data_dir / "icd10",
            self.data_dir / "cpt",
            self.data_dir / "policies",
            Path(self.evaluation_output_dir),
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()

# Ensure directories exist on import
settings.ensure_directories()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings
