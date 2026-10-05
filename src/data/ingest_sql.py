"""Bronze Data Ingestion: Extract MySQL dumps to column-oriented Parquet."""

from pathlib import Path

import polars as pl

from src.config import settings
from src.core.logging import logger, setup_logging

APIS_RAW_DATA_COLS = [
    "id_farm",
    "type_equip",
    "id_equip",
    "nm_api",
    "type_api",
    "total_time",
    "raw_data",
    "raw_date_time",
    "raw_last_valid_data",
    "log_date_creation",
]

FAZENDAS_COLS = [
    "idFazenda",
    "ID_Local",
    "ID_Estacao",
    "OpcaoETo",
    "OpcaoChuva",
    "ID_Estacao_Meteoblue",
    "identificador",
    "nome",
    "Ordem",
    "Selected",
    "CodEstacaoNormais",
    "cidade",
    "estado",
    "pais",
    "ID_Pais",
    "ID_Timezone",
    "latitude",
    "longitude",
    "Altitude",
    "idResponsavel",
    "ID_Subregiao",
    "idProprietario",
    "Proprietario",
    "situacao",
    "data_processamento",
    "data_atualizacao",
    "Decisao",
    "ResCompleto",
    "OmitirIrrigante",
    "ComSenha",
    "Senha",
    "CaDetalhado",
    "SelFazendas",
    "UnidadeMedida",
    "Manejo",
    "Manejo_Horario",
    "Manejo_Usar_UmidadeMedia",
    "Simula",
    "MDecisao",
    "Avalia",
    "DataImplantacao",
    "Sincronizar",
    "Sincronizada",
    "Wagnet_Login",
    "Wagnet_Senha",
    "Wagnet_Datetime",
    "Connected",
    "Inicio_Contrato",
    "Termino_Contrato",
    "Limite_Validacao",
    "Data_Validacao",
    "Valida",
    "Demo",
    "situacao_contrato",
    "IAPSIP_Atualizacao",
]

PIVOCENTRAL_COLS = [
    "ID",
    "ID_Fazenda",
    "ID_Conta",
    "ID_Conta_Agua",
    "ID_Local",
    "Nome",
    "Modelo",
    "Fabrica",
    "Velocidade",
    "RaioUltimaTorre",
    "PressaoServico",
    "VaoUltimaTorre",
    "TempoMaxOperacaoDia",
    "DiametroMaiorBocal",
    "DiametroMenorBocal",
    "Vazao",
    "CxUnifChristiansen",
    "PerdaConducao",
    "Tipo",
    "Latitude",
    "Longitude",
    "Raio",
    "PotenciaAbsolutaRede",
    "Fonte_Energia",
    "Area",
    "Lamina",
    "Lamina_Bruta",
    "Tempo_Volta",
    "Taxa_Aplicacao",
    "Potencia",
    "Potencia_Instalada",
    "Fator_Potencia",
    "Rendimento_Motor",
    "Indice_Carregamento",
    "Parte_Aerea",
    "KW_M3",
    "L_H",
    "Simulacao",
    "Selected",
    "Sincronizar",
    "Wagnet_ID_Pivo",
    "Wagnet_ID_Aquatrac",
    "Deleted",
    "Log_Delete_Date",
]


def parse_sql_inserts(filepath: Path, expected_cols: list[str]) -> pl.DataFrame:
    """Parses MySQL dump INSERT statements with robust escaping support."""
    rows: list[list[str | None]] = []
    num_cols = len(expected_cols)

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("INSERT INTO"):
                continue

            v_idx = line.find("VALUES (")
            if v_idx == -1:
                v_idx = line.find("VALUES(")
                if v_idx == -1:
                    continue
                start = v_idx + 7
            else:
                start = v_idx + 8

            end = line.rfind(");")
            if end == -1:
                end = line.rfind(")")
                if end == -1:
                    continue

            content = line[start:end]
            row: list[str | None] = []
            i = 0
            n = len(content)

            while i < n and len(row) < num_cols:
                while i < n and content[i] in " \t\r\n,":
                    i += 1
                if i >= n:
                    break

                if content[i] == "'":
                    i += 1
                    token_chars: list[str] = []
                    while i < n:
                        c = content[i]
                        if c == "\\":
                            if i + 1 < n:
                                nxt = content[i + 1]
                                if nxt == "n":
                                    token_chars.append("\n")
                                elif nxt == "r":
                                    token_chars.append("\r")
                                elif nxt == "t":
                                    token_chars.append("\t")
                                elif nxt == "'":
                                    token_chars.append("'")
                                elif nxt == '"':
                                    token_chars.append('"')
                                elif nxt == "\\":
                                    token_chars.append("\\")
                                else:
                                    token_chars.append(nxt)
                                i += 2
                            else:
                                i += 1
                        elif c == "'":
                            if i + 1 < n and content[i + 1] == "'":
                                token_chars.append("'")
                                i += 2
                            else:
                                i += 1
                                break
                        else:
                            token_chars.append(c)
                            i += 1
                    row.append("".join(token_chars))
                else:
                    val_chars: list[str] = []
                    while i < n and content[i] not in ",\r\n":
                        val_chars.append(content[i])
                        i += 1
                    raw_val = "".join(val_chars).strip()
                    if raw_val.upper() == "NULL" or raw_val == "":
                        row.append(None)
                    else:
                        row.append(raw_val)

            if len(row) == num_cols:
                rows.append(row)

    schema_dict = {col: pl.Utf8 for col in expected_cols}
    return pl.DataFrame(rows, schema=schema_dict, orient="row")


def run_bronze_ingestion() -> None:
    """Extracts all SQL dumps into partitioned Bronze Parquet files."""
    setup_logging()
    bronze_dir = settings.bronze_parquet_dir
    bronze_dir.mkdir(parents=True, exist_ok=True)

    # 1. Ingest apis_raw_data.sql
    raw_sql = Path(settings.raw_sql_path)
    if raw_sql.exists():
        logger.info("ingesting_apis_raw_data", path=str(raw_sql))
        df_apis = parse_sql_inserts(raw_sql, APIS_RAW_DATA_COLS)
        out_apis = bronze_dir / "apis_raw_data.parquet"
        df_apis.write_parquet(out_apis)
        logger.info("ingested_bronze_table", table="apis_raw_data", rows=len(df_apis), path=str(out_apis))

    # 2. Ingest fazendas.sql
    fazendas_sql = settings.old_db_dir / "fazendas.sql"
    if fazendas_sql.exists():
        logger.info("ingesting_fazendas", path=str(fazendas_sql))
        df_fazendas = parse_sql_inserts(fazendas_sql, FAZENDAS_COLS)
        out_fazendas = bronze_dir / "fazendas.parquet"
        df_fazendas.write_parquet(out_fazendas)
        logger.info("ingested_bronze_table", table="fazendas", rows=len(df_fazendas), path=str(out_fazendas))

    # 3. Ingest pivocentral.sql
    pivocentral_sql = settings.old_db_dir / "pivocentral.sql"
    if pivocentral_sql.exists():
        logger.info("ingesting_pivocentral", path=str(pivocentral_sql))
        df_pivocentral = parse_sql_inserts(pivocentral_sql, PIVOCENTRAL_COLS)
        out_pivocentral = bronze_dir / "pivocentral.parquet"
        df_pivocentral.write_parquet(out_pivocentral)
        logger.info("ingested_bronze_table", table="pivocentral", rows=len(df_pivocentral), path=str(out_pivocentral))


if __name__ == "__main__":
    run_bronze_ingestion()
