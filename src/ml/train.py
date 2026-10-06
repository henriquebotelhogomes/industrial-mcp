"""Explicit MLOps training script with strict temporal split, MLflow and DagsHub tracking."""

import os
import sys

import mlflow
import mlflow.sklearn

from src.config import settings
from src.core.logging import logger, setup_logging
from src.ml.anomaly_detector import OperationalAnomalyDetector


def setup_mlflow_tracking() -> bool:
    """Configures MLflow tracking URI, either locally or integrated with DagsHub."""
    # 1. Option A: DagsHub automatic integration
    if settings.dagshub_repo_owner and settings.dagshub_repo_name:
        try:
            import dagshub

            if settings.dagshub_token:
                os.environ["DAGSHUB_USER_TOKEN"] = settings.dagshub_token
            dagshub.init(
                repo_owner=settings.dagshub_repo_owner,
                repo_name=settings.dagshub_repo_name,
                mlflow=True,
            )
            logger.info(
                "dagshub_mlflow_initialized",
                repo=f"{settings.dagshub_repo_owner}/{settings.dagshub_repo_name}",
            )
            return True
        except Exception as e:
            logger.warn("dagshub_init_failed_falling_back", error=str(e))

    # 2. Option B: Explicit MLflow tracking URI (remote server or local directory)
    if settings.mlflow_tracking_uri:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        logger.info("mlflow_tracking_uri_set", uri=settings.mlflow_tracking_uri)
        return True

    # 3. Option C: Default local SQLite database backend (MLflow v3+ standard)
    local_db_path = settings.base_dir / "data" / "mlflow.db"
    mlflow.set_tracking_uri(f"sqlite:///{str(local_db_path).replace('\\', '/')}")
    logger.info("mlflow_local_tracking_uri_set", path=str(local_db_path))
    return True


if __name__ == "__main__":
    setup_logging()
    print("\n[MLOps] Iniciando pipeline de treino com split temporal estrito e MLflow...")
    setup_mlflow_tracking()

    mlflow.set_experiment(settings.mlflow_experiment_name)

    detector = OperationalAnomalyDetector()

    with mlflow.start_run(run_name="isolation-forest-temporal-split") as run:
        # Registrar hiperparâmetros
        mlflow.log_params({
            "model_type": "IsolationForest",
            "contamination": detector.model.contamination,
            "n_estimators": detector.model.n_estimators,
            "split_ratio": 0.8,
            "features": "pressure_begin, percent_timer, angular_speed, pressure_ratio, flow_rate",
            "split_strategy": "strict_temporal_chronological",
        })

        # Treinamento com corte temporal
        metrics = detector.fit_from_gold_layer()

        # Registrar métricas da divisão temporal
        if metrics.get("status") == "SUCCESS":
            mlflow.log_metrics({
                "total_records": float(metrics.get("total_records", 0)),
                "train_samples": float(metrics.get("train_samples", 0)),
                "test_samples": float(metrics.get("test_samples", 0)),
                "test_anomaly_rate": float(metrics.get("test_anomaly_rate", 0.0)),
            })

            # Registrar tags de governança
            mlflow.set_tags({
                "project": "industrial-mcp",
                "framework": "scikit-learn",
                "governance": "LGPD_Zero_PII",
                "validation": "out_of_time_validation",
                "run_id": run.info.run_id,
            })

            # Logar o artefato do modelo treinado com tipos confiáveis para o Isolation Forest
            mlflow.sklearn.log_model(
                sk_model=detector.model,
                name="model",
                skops_trusted_types=["sklearn.tree._tree.Tree"],
                registered_model_name="IndustrialIsolationForest",
            )
            print(f"[MLOps] Modelo registrado no MLflow com Run ID: {run.info.run_id}")

        print(f"[MLOps] Treinamento concluído com status: {metrics.get('status')}")
        print(f"  - Total de registros Gold: {metrics.get('total_records', 'N/A')}")
        print(f"  - Amostras de treino nominal (T < T_cutoff): {metrics.get('train_samples', 'N/A')}")
        print(f"  - Amostras de teste fora do tempo (T >= T_cutoff): {metrics.get('test_samples', 'N/A')}")
        print(f"  - Taxa de anomalias no teste: {metrics.get('test_anomaly_rate', 'N/A')}")
        print(f"  - Split ratio: {metrics.get('split_ratio', 0.8)}\n")

    sys.exit(0 if metrics.get("status") == "SUCCESS" else 1)

