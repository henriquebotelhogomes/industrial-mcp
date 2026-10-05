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

    @property
    def bronze_parquet_dir(self) -> Path:
        return self.parquet_dir / "bronze"

    @property
    def silver_parquet_dir(self) -> Path:
        return self.parquet_dir / "silver"

    @property
    def gold_parquet_dir(self) -> Path:
        return self.parquet_dir / "gold"


settings = Settings()
