"""Equipment and Farm catalog service with DuckDB fast OLAP queries."""

from typing import Any

import duckdb

from src.config import settings
from src.core.logging import logger

EQUIPMENT_TYPES = [
    {"code": "all", "name": "Todos os Tipos"},
    {"code": "3", "name": "Pivô Central"},
    {"code": "2", "name": "Gotejamento"},
    {"code": "1", "name": "Microaspersor"},
    {"code": "0", "name": "Aspersor Convencional"},
    {"code": "4", "name": "Equipamento Linear"},
    {"code": "5", "name": "Autopropelido"},
]


class AssetCatalogService:
    """Manages searchable catalog of Farms and Equipment."""

    def __init__(self):
        self._ensure_views()

    def _ensure_views(self) -> None:
        """Ensures analytical views exist in DuckDB for all 6 equipment types."""
        try:
            con = duckdb.connect(str(settings.duckdb_path))
            pivo_pq = str(settings.bronze_parquet_dir / "pivocentral.parquet").replace("\\", "/")
            faz_pq = str(settings.bronze_parquet_dir / "fazendas.parquet").replace("\\", "/")
            gotej_pq = str(settings.bronze_parquet_dir / "gotejador.parquet").replace("\\", "/")
            micro_pq = str(settings.bronze_parquet_dir / "microaspersor.parquet").replace("\\", "/")
            asper_pq = str(settings.bronze_parquet_dir / "aspersor.parquet").replace("\\", "/")
            linear_pq = str(settings.bronze_parquet_dir / "equipamento_linear.parquet").replace("\\", "/")
            auto_pq = str(settings.bronze_parquet_dir / "autopropelido.parquet").replace("\\", "/")

            query = f"""
            CREATE OR REPLACE VIEW v_equipment_catalog AS
            -- 3. Pivô Central
            SELECT
                CAST(p.ID AS BIGINT) as equip_id,
                CAST(p.ID_Fazenda AS BIGINT) as farm_id,
                f.nome as farm_name,
                COALESCE(f.cidade, '') as farm_city,
                COALESCE(f.estado, '') as farm_state,
                p.Nome as equip_name,
                '3' as type_code,
                'Pivô Central' as type_name,
                COALESCE(NULLIF(p.Fabrica, ''), 'Valmont') as maker,
                COALESCE(NULLIF(p.Modelo, ''), 'Valley 8000C') as model,
                TRY_CAST(p.PressaoServico AS DOUBLE) as raw_pressure,
                CASE
                    WHEN TRY_CAST(p.PressaoServico AS DOUBLE) > 10.0
                    THEN ROUND(TRY_CAST(p.PressaoServico AS DOUBLE) / 10.0, 2)
                    ELSE COALESCE(TRY_CAST(p.PressaoServico AS DOUBLE), 3.4)
                END as nominal_pressure,
                COALESCE(TRY_CAST(p.RaioUltimaTorre AS DOUBLE), 380.0) as radius,
                COALESCE(TRY_CAST(p.Vazao AS DOUBLE), 185.0) as flow_rate,
                COALESCE(TRY_CAST(p.Area AS DOUBLE), 45.0) as area
            FROM read_parquet('{pivo_pq}') p
            JOIN read_parquet('{faz_pq}') f ON p.ID_Fazenda = f.idFazenda
            WHERE p.Nome IS NOT NULL AND p.Nome != '' AND f.nome IS NOT NULL AND f.nome != ''

            UNION ALL

            -- 2. Gotejamento
            SELECT
                CAST(g.ID AS BIGINT) as equip_id,
                CAST(g.ID_Fazenda AS BIGINT) as farm_id,
                f.nome as farm_name,
                COALESCE(f.cidade, '') as farm_city,
                COALESCE(f.estado, '') as farm_state,
                g.Nome as equip_name,
                '2' as type_code,
                'Gotejamento' as type_name,
                COALESCE(NULLIF(g.Fabrica, ''), 'Netafim') as maker,
                COALESCE(NULLIF(g.Tipo, ''), 'Drip Line') as model,
                TRY_CAST(g.PressaoServico AS DOUBLE) as raw_pressure,
                CASE
                    WHEN TRY_CAST(g.PressaoServico AS DOUBLE) > 10.0
                    THEN ROUND(TRY_CAST(g.PressaoServico AS DOUBLE) / 10.0, 2)
                    ELSE COALESCE(TRY_CAST(g.PressaoServico AS DOUBLE), 1.5)
                END as nominal_pressure,
                150.0 as radius,
                COALESCE(TRY_CAST(g.Vazao AS DOUBLE), 45.0) as flow_rate,
                20.0 as area
            FROM read_parquet('{gotej_pq}') g
            JOIN read_parquet('{faz_pq}') f ON g.ID_Fazenda = f.idFazenda
            WHERE g.Nome IS NOT NULL AND g.Nome != '' AND f.nome IS NOT NULL AND f.nome != ''

            UNION ALL

            -- 1. Microaspersor
            SELECT
                CAST(m.ID AS BIGINT) as equip_id,
                CAST(m.ID_Fazenda AS BIGINT) as farm_id,
                f.nome as farm_name,
                COALESCE(f.cidade, '') as farm_city,
                COALESCE(f.estado, '') as farm_state,
                m.Nome as equip_name,
                '1' as type_code,
                'Microaspersor' as type_name,
                COALESCE(NULLIF(m.Fabrica, ''), 'NaanDanJain') as maker,
                COALESCE(NULLIF(m.Tipo, ''), 'Micro-Spin') as model,
                TRY_CAST(m.PressaoServico AS DOUBLE) as raw_pressure,
                CASE
                    WHEN TRY_CAST(m.PressaoServico AS DOUBLE) > 10.0
                    THEN ROUND(TRY_CAST(m.PressaoServico AS DOUBLE) / 10.0, 2)
                    ELSE COALESCE(TRY_CAST(m.PressaoServico AS DOUBLE), 2.0)
                END as nominal_pressure,
                COALESCE(TRY_CAST(m.DiametroMolhado AS DOUBLE)/2.0, 15.0) as radius,
                COALESCE(TRY_CAST(m.Vazao AS DOUBLE), 35.0) as flow_rate,
                15.0 as area
            FROM read_parquet('{micro_pq}') m
            JOIN read_parquet('{faz_pq}') f ON m.ID_Fazenda = f.idFazenda
            WHERE m.Nome IS NOT NULL AND m.Nome != '' AND f.nome IS NOT NULL AND f.nome != ''

            UNION ALL

            -- 0. Aspersor Convencional
            SELECT
                CAST(a.ID AS BIGINT) as equip_id,
                CAST(a.ID_Fazenda AS BIGINT) as farm_id,
                f.nome as farm_name,
                COALESCE(f.cidade, '') as farm_city,
                COALESCE(f.estado, '') as farm_state,
                a.Nome as equip_name,
                '0' as type_code,
                'Aspersor Convencional' as type_name,
                COALESCE(NULLIF(a.Fabrica, ''), 'Rain Bird') as maker,
                COALESCE(NULLIF(a.Modelo, ''), 'Impact 30JH') as model,
                TRY_CAST(a.PressaoServico AS DOUBLE) as raw_pressure,
                CASE
                    WHEN TRY_CAST(a.PressaoServico AS DOUBLE) > 10.0
                    THEN ROUND(TRY_CAST(a.PressaoServico AS DOUBLE) / 10.0, 2)
                    ELSE COALESCE(TRY_CAST(a.PressaoServico AS DOUBLE), 3.0)
                END as nominal_pressure,
                30.0 as radius,
                COALESCE(TRY_CAST(a.Vazao AS DOUBLE), 50.0) as flow_rate,
                12.0 as area
            FROM read_parquet('{asper_pq}') a
            JOIN read_parquet('{faz_pq}') f ON a.ID_Fazenda = f.idFazenda
            WHERE a.Nome IS NOT NULL AND a.Nome != '' AND f.nome IS NOT NULL AND f.nome != ''

            UNION ALL

            -- 4. Equipamento Linear
            SELECT
                CAST(l.ID AS BIGINT) as equip_id,
                CAST(l.ID_Fazenda AS BIGINT) as farm_id,
                f.nome as farm_name,
                COALESCE(f.cidade, '') as farm_city,
                COALESCE(f.estado, '') as farm_state,
                l.Nome as equip_name,
                '4' as type_code,
                'Equipamento Linear' as type_name,
                COALESCE(NULLIF(l.Fabrica, ''), 'Lindsay') as maker,
                COALESCE(NULLIF(l.Modelo, ''), 'Zimmatic Linear') as model,
                TRY_CAST(l.PressaoServico AS DOUBLE) as raw_pressure,
                CASE
                    WHEN TRY_CAST(l.PressaoServico AS DOUBLE) > 10.0
                    THEN ROUND(TRY_CAST(l.PressaoServico AS DOUBLE) / 10.0, 2)
                    ELSE COALESCE(TRY_CAST(l.PressaoServico AS DOUBLE), 3.2)
                END as nominal_pressure,
                COALESCE(TRY_CAST(l.ComprimentoUltTorre AS DOUBLE), 400.0) as radius,
                COALESCE(TRY_CAST(l.VazaoTotal AS DOUBLE), 220.0) as flow_rate,
                60.0 as area
            FROM read_parquet('{linear_pq}') l
            JOIN read_parquet('{faz_pq}') f ON l.ID_Fazenda = f.idFazenda
            WHERE l.Nome IS NOT NULL AND l.Nome != '' AND f.nome IS NOT NULL AND f.nome != ''

            UNION ALL

            -- 5. Autopropelido
            SELECT
                CAST(ap.ID AS BIGINT) as equip_id,
                CAST(ap.ID_Fazenda AS BIGINT) as farm_id,
                f.nome as farm_name,
                COALESCE(f.cidade, '') as farm_city,
                COALESCE(f.estado, '') as farm_state,
                ap.Nome as equip_name,
                '5' as type_code,
                'Autopropelido' as type_name,
                COALESCE(NULLIF(ap.Fabrica, ''), 'IrrigaSys') as maker,
                COALESCE(NULLIF(ap.Modelo, ''), 'Turbo Reel') as model,
                TRY_CAST(ap.PressaoServico AS DOUBLE) as raw_pressure,
                CASE
                    WHEN TRY_CAST(ap.PressaoServico AS DOUBLE) > 10.0
                    THEN ROUND(TRY_CAST(ap.PressaoServico AS DOUBLE) / 10.0, 2)
                    ELSE COALESCE(TRY_CAST(ap.PressaoServico AS DOUBLE), 6.0)
                END as nominal_pressure,
                COALESCE(TRY_CAST(ap.AlcanceCanhao AS DOUBLE), 60.0) as radius,
                COALESCE(TRY_CAST(ap.Vazao AS DOUBLE), 90.0) as flow_rate,
                25.0 as area
            FROM read_parquet('{auto_pq}') ap
            JOIN read_parquet('{faz_pq}') f ON ap.ID_Fazenda = f.idFazenda
            WHERE ap.Nome IS NOT NULL AND ap.Nome != '' AND f.nome IS NOT NULL AND f.nome != ''
            """
            con.execute(query)
            con.close()
            logger.info("asset_catalog_view_ready", total_types=6)
        except Exception as e:
            logger.error("failed_to_create_catalog_view", error=str(e))

    def get_farms(
        self,
        search: str = "",
        limit: int = 300,
        include_farm_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Returns list of farms matching search query with equipment count."""
        try:
            con = duckdb.connect(str(settings.duckdb_path), read_only=True)
            filter_sql = ""
            if search.strip():
                clean_q = search.replace("'", "''").lower()
                filter_sql = f"WHERE lower(farm_name) LIKE '%{clean_q}%' OR lower(farm_city) LIKE '%{clean_q}%'"

            query = f"""
                SELECT
                    farm_id, farm_name, farm_city, farm_state,
                    COUNT(equip_id) as total_equips
                FROM v_equipment_catalog
                {filter_sql}
                GROUP BY farm_id, farm_name, farm_city, farm_state
                ORDER BY total_equips DESC, farm_name ASC
                LIMIT {limit}
            """
            rows = con.execute(query).fetchall()
            farms = [
                {
                    "farm_id": r[0],
                    "farm_name": r[1],
                    "farm_city": r[2],
                    "farm_state": r[3],
                    "total_equips": r[4],
                }
                for r in rows
            ]

            # Guarantee that include_farm_id is included even if it has fewer equips than top limit
            if include_farm_id is not None and not any(f["farm_id"] == include_farm_id for f in farms):
                specific_row = con.execute(f"""
                    SELECT
                        farm_id, farm_name, farm_city, farm_state,
                        COUNT(equip_id) as total_equips
                    FROM v_equipment_catalog
                    WHERE farm_id = {include_farm_id}
                    GROUP BY farm_id, farm_name, farm_city, farm_state
                    LIMIT 1
                """).fetchone()
                if specific_row:
                    farms.insert(0, {
                        "farm_id": specific_row[0],
                        "farm_name": specific_row[1],
                        "farm_city": specific_row[2],
                        "farm_state": specific_row[3],
                        "total_equips": specific_row[4],
                    })

            con.close()
            return farms
        except Exception as e:
            logger.error("error_querying_farms", error=str(e))
            return []

    def get_farm_by_id(self, farm_id: int) -> dict[str, Any] | None:
        """Returns single farm summary by farm_id."""
        try:
            con = duckdb.connect(str(settings.duckdb_path), read_only=True)
            row = con.execute(f"""
                SELECT
                    farm_id, farm_name, farm_city, farm_state,
                    COUNT(equip_id) as total_equips
                FROM v_equipment_catalog
                WHERE farm_id = {farm_id}
                GROUP BY farm_id, farm_name, farm_city, farm_state
                LIMIT 1
            """).fetchone()
            con.close()
            if not row:
                return None
            return {
                "farm_id": row[0],
                "farm_name": row[1],
                "farm_city": row[2],
                "farm_state": row[3],
                "total_equips": row[4],
            }
        except Exception as e:
            logger.error("error_querying_farm_by_id", error=str(e), farm_id=farm_id)
            return None

    def get_equipment_types(self) -> list[dict[str, str]]:
        """Returns supported equipment types."""
        return EQUIPMENT_TYPES

    def get_equipment(
        self,
        farm_id: int | None = None,
        type_code: str | None = None,
        search: str = "",
        limit: int = 100,
        include_equip_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Returns equipments matching farm, type, and search filters."""
        try:
            con = duckdb.connect(str(settings.duckdb_path), read_only=True)
            conditions = []
            if farm_id is not None:
                conditions.append(f"farm_id = {farm_id}")
            if type_code and type_code != "all":
                conditions.append(f"type_code = '{type_code}'")
            if search.strip():
                clean_q = search.replace("'", "''").lower()
                conditions.append(f"(lower(equip_name) LIKE '%{clean_q}%' OR lower(maker) LIKE '%{clean_q}%' OR lower(model) LIKE '%{clean_q}%')")

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            query = f"""
                SELECT
                    equip_id, farm_id, farm_name, farm_city, farm_state,
                    equip_name, type_code, type_name, maker, model,
                    nominal_pressure, radius, flow_rate, area
                FROM v_equipment_catalog
                {where_clause}
                ORDER BY equip_name ASC
                LIMIT {limit}
            """
            rows = con.execute(query).fetchall()
            equips = [
                {
                    "equip_id": r[0],
                    "farm_id": r[1],
                    "farm_name": r[2],
                    "farm_city": r[3],
                    "farm_state": r[4],
                    "equip_name": r[5],
                    "type_code": r[6],
                    "type_name": r[7],
                    "maker": r[8],
                    "model": r[9],
                    "nominal_pressure": r[10],
                    "radius": r[11],
                    "flow_rate": r[12],
                    "area": r[13],
                }
                for r in rows
            ]

            # Guarantee that include_equip_id is included even if filtered or capped
            if include_equip_id is not None and not any(e["equip_id"] == include_equip_id for e in equips):
                specific_row = con.execute(f"""
                    SELECT
                        equip_id, farm_id, farm_name, farm_city, farm_state,
                        equip_name, type_code, type_name, maker, model,
                        nominal_pressure, radius, flow_rate, area
                    FROM v_equipment_catalog
                    WHERE equip_id = {include_equip_id}
                    LIMIT 1
                """).fetchone()
                if specific_row:
                    equips.insert(0, {
                        "equip_id": specific_row[0],
                        "farm_id": specific_row[1],
                        "farm_name": specific_row[2],
                        "farm_city": specific_row[3],
                        "farm_state": specific_row[4],
                        "equip_name": specific_row[5],
                        "type_code": specific_row[6],
                        "type_name": specific_row[7],
                        "maker": specific_row[8],
                        "model": specific_row[9],
                        "nominal_pressure": specific_row[10],
                        "radius": specific_row[11],
                        "flow_rate": specific_row[12],
                        "area": specific_row[13],
                    })

            con.close()
            return equips
        except Exception as e:
            logger.error("error_querying_equipment", error=str(e))
            return []

    def get_equipment_by_id(self, equip_id: int) -> dict[str, Any] | None:
        """Returns detailed specifications for single equipment."""
        try:
            con = duckdb.connect(str(settings.duckdb_path), read_only=True)
            row = con.execute(f"""
                SELECT
                    equip_id, farm_id, farm_name, farm_city, farm_state,
                    equip_name, type_code, type_name, maker, model,
                    nominal_pressure, radius, flow_rate, area
                FROM v_equipment_catalog
                WHERE equip_id = {equip_id}
                LIMIT 1
            """).fetchone()
            con.close()
            if not row:
                return None
            return {
                "equip_id": row[0],
                "farm_id": row[1],
                "farm_name": row[2],
                "farm_city": row[3],
                "farm_state": row[4],
                "equip_name": row[5],
                "type_code": row[6],
                "type_name": row[7],
                "maker": row[8],
                "model": row[9],
                "nominal_pressure": row[10],
                "radius": row[11],
                "flow_rate": row[12],
                "area": row[13],
            }
        except Exception as e:
            logger.error("error_querying_equipment_by_id", error=str(e), equip_id=equip_id)
            return None


asset_catalog = AssetCatalogService()
