"""Benchmarking engine for cross-validation, inference latency, and leaderboard generation."""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

from autocompliant.data.dataset import CompliantDataset
from autocompliant.models.base import BaseSurrogateModel
from autocompliant.models import (
    MultiOutputGPR,
    XGBoostSurrogate,
    LightGBMSurrogate,
    RandomForestSurrogate,
    AdaptiveMLPSurrogate,
    PolynomialRSMSurrogate,
)
from autocompliant.evaluation.metrics import evaluate_multioutput_metrics


class BenchmarkResult:
    """Encapsulates benchmark outputs, rankings, and export formatting."""

    def __init__(
        self,
        records: List[Dict[str, Any]],
        best_model: BaseSurrogateModel,
        output_symbols: List[str],
        fitted_models: Optional[Dict[str, BaseSurrogateModel]] = None,
    ):
        self.records = records
        self.best_model = best_model
        self.output_symbols = output_symbols
        self.fitted_models = fitted_models or {}

    def to_dataframe(self) -> pd.DataFrame:
        """Convert benchmark records into a formatted pandas DataFrame."""
        rows = []
        for rec in self.records:
            row = {
                "Rank": rec["rank"],
                "Model": rec["model_name"],
                "Test R² (Mean)": f"{rec['test_r2_mean']:.4f}",
                "CV R² (Mean)": f"{rec['cv_r2_mean']:.4f} ± {rec['cv_r2_std']:.4f}",
                "Test RMSE": f"{rec['test_rmse_mean']:.4f}",
                "Test MAE": f"{rec['test_mae_mean']:.4f}",
                "Latency (ms/1k)": f"{rec['inference_latency_ms']:.2f}",
                "Train Time (s)": f"{rec['train_time_sec']:.2f}",
            }
            # Append per-output R2
            for sym, metric_dict in rec["per_output"].items():
                row[f"{sym} R²"] = f"{metric_dict['r2']:.4f}"
            rows.append(row)
        return pd.DataFrame(rows)

    def to_json(self, path: Optional[Path] = None) -> str:
        """Export benchmark results as a structured JSON string/file."""
        data = {
            "best_model_name": self.best_model.name,
            "output_symbols": self.output_symbols,
            "leaderboard": self.records,
        }
        json_str = json.dumps(data, indent=2)
        if path:
            path_obj = Path(path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            with open(path_obj, "w", encoding="utf-8") as f:
                f.write(json_str)
        return json_str

    def to_markdown(self, path: Optional[Path] = None) -> str:
        """Generate a GitHub Flavored Markdown Leaderboard table."""
        df = self.to_dataframe()
        try:
            md_table = df.to_markdown(index=False)
        except Exception:
            headers = list(df.columns)
            lines = [
                "| " + " | ".join(headers) + " |",
                "| " + " | ".join(["---"] * len(headers)) + " |",
            ]
            for _, row in df.iterrows():
                lines.append("| " + " | ".join(str(val) for val in row.values) + " |")
            md_table = "\n".join(lines)

        content = (
            f"# AutoCompliant-ML Surrogate Benchmark Leaderboard\n\n"
            f"> **Top Ranked Model**: `{self.best_model.name}`\n\n"
            f"{md_table}\n"
        )
        if path:
            path_obj = Path(path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            with open(path_obj, "w", encoding="utf-8") as f:
                f.write(content)
        return content


class ModelBenchmarkEngine:
    """Automated benchmark executor across the multi-output Model Zoo."""

    def __init__(self, dataset: CompliantDataset, cv_folds: int = 5, seed: int = 42):
        self.dataset = dataset
        self.cv_folds = cv_folds
        self.seed = seed
        self.config = dataset.config

    def get_default_model_zoo(self) -> List[BaseSurrogateModel]:
        """Instantiate default candidate models for comparative benchmarking."""
        return [
            PolynomialRSMSurrogate(degree=2),
            RandomForestSurrogate(n_estimators=100, max_depth=8, random_state=self.seed),
            XGBoostSurrogate(n_estimators=120, max_depth=4, learning_rate=0.08, random_state=self.seed),
            LightGBMSurrogate(n_estimators=120, max_depth=5, learning_rate=0.08, random_state=self.seed),
            AdaptiveMLPSurrogate(hidden_dim=64, epochs=60, random_state=self.seed),
            MultiOutputGPR(n_restarts_optimizer=1, random_state=self.seed),
        ]

    def run_benchmark(
        self, models: Optional[List[BaseSurrogateModel]] = None
    ) -> BenchmarkResult:
        """Execute cross-validation, test partition evaluation, and latency benchmarking."""
        model_list = models if models is not None else self.get_default_model_zoo()
        X_train, Y_train = self.dataset.get_train_data(scaled=True)
        X_test, Y_test = self.dataset.get_test_data(scaled=True)

        records = []
        fitted_models: Dict[str, BaseSurrogateModel] = {}

        kf = KFold(n_splits=self.cv_folds, shuffle=True, random_state=self.seed)

        for model in model_list:
            # 1. K-Fold Cross Validation on Train Data
            cv_scores = []
            for train_idx, val_idx in kf.split(X_train):
                X_tr, X_val = X_train[train_idx], X_train[val_idx]
                Y_tr, Y_val = Y_train[train_idx], Y_train[val_idx]

                # Train fresh instance on fold
                fold_model = type(model)() if hasattr(model, "__init__") else model
                fold_model.fit(X_tr, Y_tr)
                cv_scores.append(fold_model.score_r2(X_val, Y_val))

            cv_r2_mean = float(np.mean(cv_scores))
            cv_r2_std = float(np.std(cv_scores))

            # 2. Train on full Training partition & measure training duration
            t0 = time.perf_counter()
            model.fit(X_train, Y_train)
            train_time_sec = float(time.perf_counter() - t0)
            fitted_models[model.name] = model

            # 3. Measure inference latency (per 1,000 predictions in milliseconds)
            warmup_x = X_test[: min(10, len(X_test))]
            _ = model.predict(warmup_x)  # warmup

            # Repeat test inference to get accurate timing
            benchmark_x = np.repeat(X_test, repeats=max(1, 1000 // len(X_test)), axis=0)[:1000]
            t_inf0 = time.perf_counter()
            _ = model.predict(benchmark_x)
            inference_latency_ms = float((time.perf_counter() - t_inf0) * 1000.0)

            # 4. Evaluate on held-out Test partition
            Y_test_pred = model.predict(X_test)
            metrics = evaluate_multioutput_metrics(
                Y_test, Y_test_pred, output_symbols=self.config.output_symbols
            )

            records.append({
                "model_name": model.name,
                "cv_r2_mean": cv_r2_mean,
                "cv_r2_std": cv_r2_std,
                "test_r2_mean": metrics["r2_mean"],
                "test_rmse_mean": metrics["rmse_mean"],
                "test_mae_mean": metrics["mae_mean"],
                "test_mape_mean": metrics["mape_mean"],
                "inference_latency_ms": inference_latency_ms,
                "train_time_sec": train_time_sec,
                "per_output": metrics["per_output"],
            })

        # Rank models: Primary by Test R2 descending, secondary by latency ascending
        records.sort(
            key=lambda r: (r["test_r2_mean"], -r["inference_latency_ms"]), reverse=True
        )

        for rank, rec in enumerate(records, start=1):
            rec["rank"] = rank

        best_model_name = records[0]["model_name"]
        best_model = fitted_models[best_model_name]

        return BenchmarkResult(
            records=records,
            best_model=best_model,
            output_symbols=self.config.output_symbols,
            fitted_models=fitted_models,
        )
