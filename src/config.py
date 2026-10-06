"""Application configuration using Pydantic Settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server Configuration
    host: str = "127.0.0.1"
    port: int = 8000
    environment: str = "development"
    log_level: str = "INFO"

    # Data & Storage
    base_dir: Path = Path(__file__).resolve().parent.parent
    parquet_dir: Path = Path("data/parquet")
    duckdb_path: Path = Path("data/industrial.duckdb")
    raw_sql_path: Path = Path("apis_raw_data.sql")
    old_db_dir: Path = Path("OLD_DB")

    # MCP Configuration
    mcp_server_name: str = "Industrial-Telemetry-MCP"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8001

    # Real-time Stream Simulation
    stream_tick_rate_ms: int = 1000
    stream_default_speed: float = 1.0

    # LLM & Multi-Agent Configuration (LangGraph System 2)
    llm_provider: str = "openrouter"
    llm_model: str = "google/gemini-3.8-flash"
    llm_fallback_model: str = "deepseek/deepseek-v4-flash"
    llm_decision_model: str = "typesafe/jev-latest"
    openrouter_api_key: str | None = None
    gemini_api_key: str | None = None
    openai_api_key: str | None = None

    # FinOps & Semantic Caching
    semantic_cache_enabled: bool = True
    semantic_cache_similarity_threshold: float = 0.88
    max_daily_token_budget: int = 100000

    @property
    def bronze_parquet_dir(self) -> Path:
        return self.parquet_dir / "bronze"

    @property
    def silver_parquet_dir(self) -> Path:
        return self.parquet_dir / "silver"

    @property
    def gold_parquet_dir(self) -> Path:
        return self.parquet_dir / "gold"

    @property
    def dlq_parquet_dir(self) -> Path:
        return self.parquet_dir / "dlq"


settings = Settings()
