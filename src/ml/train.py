"""Explicit MLOps training script with strict temporal split to prevent data leakage."""

import sys

from src.core.logging import setup_logging
from src.ml.anomaly_detector import OperationalAnomalyDetector

if __name__ == "__main__":
    setup_logging()
    print("\n[MLOps] Iniciando treinamento do Isolation Forest com split temporal estrito...")
    detector = OperationalAnomalyDetector()
    metrics = detector.fit_from_gold_layer()
    print(f"[MLOps] Treinamento concluído com status: {metrics.get('status')}")
    print(f"  - Total de registros Gold: {metrics.get('total_records', 'N/A')}")
    print(f"  - Amostras de treino nominal (T < T_cutoff): {metrics.get('train_samples', 'N/A')}")
    print(f"  - Amostras de teste fora do tempo (T >= T_cutoff): {metrics.get('test_samples', 'N/A')}")
    print(f"  - Taxa de anomalias no teste: {metrics.get('test_anomaly_rate', 'N/A')}")
    print(f"  - Split ratio: {metrics.get('split_ratio', 0.8)}\n")
    sys.exit(0 if metrics.get("status") == "SUCCESS" else 1)
