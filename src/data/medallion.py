"""Medallion Pipeline: Bronze -> Silver -> Gold with DuckDB and Polars."""

import json
from pathlib import Path

import duckdb
import polars as pl

from src.config import settings
from src.core.logging import logger, setup_logging
from src.ml.domain_rules import DomainRuleEngine


def extract_telemetry_json(raw_str: str | None) -> dict[str, str | float | None]:
    """Safely extracts JSON telemetry payload into normalized dict."""
    if not raw_str:
        return {}
    try:
        data = json.loads(raw_str)
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def to_float(val: str | float | None, default: float = 0.0) -> float:
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def process_silver_layer() -> pl.DataFrame:
    """Transforms raw Bronze dumps into enriched, typed Silver telemetry."""
    setup_logging()
    bronze_dir = settings.bronze_parquet_dir
    silver_dir = settings.silver_parquet_dir
    silver_dir.mkdir(parents=True, exist_ok=True)

    apis_pq = bronze_dir / "apis_raw_data.parquet"
    fazendas_pq = bronze_dir / "fazendas.parquet"
    pivo_pq = bronze_dir / "pivocentral.parquet"

    if not apis_pq.exists():
        logger.error("bronze_table_missing", path=str(apis_pq))
        raise FileNotFoundError(f"Missing {apis_pq}")

    logger.info("processing_silver_layer", source=str(apis_pq))

    df_apis = pl.read_parquet(apis_pq)
    df_fazendas = pl.read_parquet(fazendas_pq) if fazendas_pq.exists() else pl.DataFrame()
    df_pivo = pl.read_parquet(pivo_pq) if pivo_pq.exists() else pl.DataFrame()

    # Filter for Center Pivots (type_equip == '3') with non-empty payload
    df_pivots = df_apis.filter((pl.col("type_equip") == "3") & (pl.col("raw_data").is_not_null()))

    records: list[dict] = []
    for row in df_pivots.iter_rows(named=True):
        raw_json_str = row["raw_data"] or row["raw_last_valid_data"]
        payload = extract_telemetry_json(raw_json_str)
        if not payload:
            continue

        id_farm = int(row["id_farm"])
        id_equip = int(row["id_equip"])
        api_provider = "WAGNET" if row["nm_api"] == "1" else ("BASE_STATION" if row["nm_api"] == "2" else "METOS")

        created_dt = payload.get("CreatedDate") or row["raw_date_time"] or row["log_date_creation"]
        curr_angle = to_float(payload.get("PivotCurrentPosition"), 0.0)
        direction = str(payload.get("PivotDirection") or "Forward").capitalize()
        running_status = str(payload.get("PivotRunningStatus") or "Stopped").capitalize()
        water_mode = str(payload.get("WaterMode") or "Dry").capitalize()
        percent_timer = to_float(payload.get("PercentTimer"), 0.0)
        pressure_begin = to_float(payload.get("PressureBeginValue"), 0.0)
        pressure_end = to_float(payload.get("PressureEndValue"), 0.0)
        flow_rate = to_float(payload.get("FlowRateMeter1") or payload.get("FlowRateMeter2"), 0.0)
        deg_travelled = to_float(payload.get("DegreesTravelled"), 0.0)
        hour_meter = to_float(payload.get("HourMeter"), 0.0)

        records.append({
            "id_farm": id_farm,
            "id_equip": id_equip,
            "api_provider": api_provider,
            "timestamp": str(created_dt),
            "current_angle": curr_angle,
            "direction": direction,
            "running_status": running_status,
            "water_mode": water_mode,
            "percent_timer": percent_timer,
            "pressure_begin": pressure_begin,
            "pressure_end": pressure_end,
            "flow_rate": flow_rate,
            "degrees_travelled": deg_travelled,
            "hour_meter": hour_meter,
        })

    df_silver = pl.DataFrame(records)
    logger.info("silver_telemetry_extracted", rows=len(df_silver))

    # Join with fazendas metadata
    if not df_fazendas.is_empty():
        faz_meta = df_fazendas.select([
            pl.col("idFazenda").cast(pl.Int64).alias("id_farm"),
            pl.col("nome").alias("farm_name"),
            pl.col("cidade").alias("farm_city"),
            pl.col("estado").alias("farm_state"),
            pl.col("Proprietario").alias("farm_owner"),
        ]).unique(subset=["id_farm"])
        df_silver = df_silver.join(faz_meta, on="id_farm", how="left")

    # Join with pivocentral metadata
    if not df_pivo.is_empty():
        pivo_meta = df_pivo.select([
            pl.col("ID").cast(pl.Int64).alias("id_equip"),
            pl.col("Nome").alias("pivot_name"),
            pl.col("Modelo").alias("pivot_model"),
            pl.col("Fabrica").alias("pivot_maker"),
            pl.col("RaioUltimaTorre").cast(pl.Float64, strict=False).alias("pivot_radius"),
            pl.col("PressaoServico").cast(pl.Float64, strict=False).alias("nominal_pressure"),
            pl.col("Vazao").cast(pl.Float64, strict=False).alias("nominal_flow"),
        ]).unique(subset=["id_equip"])
        df_silver = df_silver.join(pivo_meta, on="id_equip", how="left")

    out_silver = silver_dir / "pivot_telemetry.parquet"
    df_silver.write_parquet(out_silver)
    logger.info("silver_layer_saved", path=str(out_silver), shape=df_silver.shape)
    return df_silver


def process_gold_layer() -> pl.DataFrame:
    """Computes Gold operational metrics, physics rule evaluations, and anomaly flags."""
    setup_logging()
    silver_pq = settings.silver_parquet_dir / "pivot_telemetry.parquet"
    gold_dir = settings.gold_parquet_dir
    gold_dir.mkdir(parents=True, exist_ok=True)

    if not silver_pq.exists():
        process_silver_layer()

    df_silver = pl.read_parquet(silver_pq)
    logger.info("processing_gold_layer", input_rows=len(df_silver))

    # Evaluate physics and domain anomalies across rows
    pump_anomaly_flags: list[bool] = []
    effective_irrigation: list[bool] = []

    for row in df_silver.iter_rows(named=True):
        water_mode = row["water_mode"] or "Dry"
        p_begin = row["pressure_begin"] or 0.0
        p_nom = row.get("nominal_pressure")

        is_pump_anom, _ = DomainRuleEngine.validate_pump_pressure_congruence(
            water_mode=water_mode,
            pressure_begin=p_begin,
            nominal_pressure=p_nom,
        )
        pump_anomaly_flags.append(is_pump_anom)
        # Real irrigation: pump commanded Wet AND actual pressure verified
        effective_irrigation.append(water_mode.lower() == "wet" and not is_pump_anom)

    df_gold = df_silver.with_columns([
        pl.Series("flag_pressure_anomaly", pump_anomaly_flags, dtype=pl.Boolean),
        pl.Series("is_effective_irrigation", effective_irrigation, dtype=pl.Boolean),
    ])

    out_gold = gold_dir / "pivot_gold_metrics.parquet"
    df_gold.write_parquet(out_gold)
    logger.info("gold_layer_saved", path=str(out_gold), shape=df_gold.shape)

    # Sync with DuckDB OLAP
    sync_duckdb()
    return df_gold


def sync_duckdb() -> None:
    """Creates views in local DuckDB for analytical OLAP querying."""
    db_path = settings.duckdb_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path))
    silver_pq = str(settings.silver_parquet_dir / "pivot_telemetry.parquet").replace("\\", "/")
    gold_pq = str(settings.gold_parquet_dir / "pivot_gold_metrics.parquet").replace("\\", "/")

    if Path(settings.silver_parquet_dir / "pivot_telemetry.parquet").exists():
        con.execute(f"CREATE OR REPLACE VIEW v_silver_telemetry AS SELECT * FROM read_parquet('{silver_pq}');")
    if Path(settings.gold_parquet_dir / "pivot_gold_metrics.parquet").exists():
        con.execute(f"CREATE OR REPLACE VIEW v_gold_metrics AS SELECT * FROM read_parquet('{gold_pq}');")

    tables = con.execute("SHOW TABLES;").fetchall()
    con.close()
    logger.info("duckdb_synced", tables=[t[0] for t in tables], db_path=str(db_path))


if __name__ == "__main__":
    process_silver_layer()
    process_gold_layer()
