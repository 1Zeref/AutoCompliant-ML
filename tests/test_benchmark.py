"""Unit tests for multi-output metrics and benchmarking engine (Loop 4 Gate)."""

import json
import pytest
import numpy as np

from autocompliant.config.loader import load_topology_config
from autocompliant.data.dataset import CompliantDataset
from autocompliant.evaluation.metrics import evaluate_multioutput_metrics
from autocompliant.evaluation.benchmark import ModelBenchmarkEngine
from autocompliant.models import PolynomialRSMSurrogate, RandomForestSurrogate


def test_multioutput_metrics_accuracy():
    """Verify metrics calculation against exact known values."""
    Y_true = np.array([[10.0, 20.0], [20.0, 40.0], [30.0, 60.0]])
    Y_pred = np.array([[10.0, 20.0], [20.0, 40.0], [30.0, 60.0]])

    metrics = evaluate_multioutput_metrics(Y_true, Y_pred, output_symbols=["O1", "O2"])

    assert metrics["r2_mean"] == 1.0
    assert metrics["rmse_mean"] == 0.0
    assert metrics["mae_mean"] == 0.0
    assert metrics["mape_mean"] == 0.0
    assert "O1" in metrics["per_output"]
    assert metrics["per_output"]["O1"]["r2"] == 1.0


def test_benchmark_engine_execution(tmp_path):
    """Verify end-to-end benchmark engine run and leaderboard structure."""
    config = load_topology_config("configs/bridge_amplifier.yaml")
    dataset = CompliantDataset.from_synthetic(config, n_samples=150, seed=42)

    engine = ModelBenchmarkEngine(dataset=dataset, cv_folds=2, seed=42)
    models = [
        PolynomialRSMSurrogate(degree=2),
        RandomForestSurrogate(n_estimators=20, max_depth=4),
    ]

    result = engine.run_benchmark(models=models)

    assert len(result.records) == 2
    assert result.records[0]["rank"] == 1
    assert result.records[1]["rank"] == 2
    assert result.best_model is not None

    # Check JSON export
    json_path = tmp_path / "leaderboard.json"
    result.to_json(json_path)
    assert json_path.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "leaderboard" in data
    assert "best_model_name" in data
    assert len(data["leaderboard"]) == 2

    # Check Markdown export
    md_path = tmp_path / "leaderboard.md"
    md_content = result.to_markdown(md_path)
    assert md_path.exists()
    assert "Rank" in md_content
    assert "Model" in md_content
    assert result.best_model.name in md_content
