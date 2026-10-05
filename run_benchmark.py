#!/usr/bin/env python
"""CLI Tool to run comparative benchmarking across multi-output surrogate models."""

import argparse
import pickle
import sys
from pathlib import Path

from autocompliant.config.loader import load_topology_config
from autocompliant.data.dataset import CompliantDataset
from autocompliant.evaluation.benchmark import ModelBenchmarkEngine
from autocompliant.models import (
    PolynomialRSMSurrogate,
    RandomForestSurrogate,
    XGBoostSurrogate,
    LightGBMSurrogate,
    AdaptiveMLPSurrogate,
    MultiOutputGPR,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="AutoCompliant-ML Multi-Output Surrogate Benchmark Runner."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/bridge_amplifier.yaml",
        help="Path to topology configuration YAML.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=350,
        help="Number of samples to generate if using synthetic dataset.",
    )
    parser.add_argument(
        "--cv-folds",
        type=int,
        default=5,
        help="Number of cross-validation folds.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports",
        help="Directory to save Leaderboard JSON and Markdown reports.",
    )
    parser.add_argument(
        "--artifact-dir",
        type=str,
        default="models/artifacts",
        help="Directory to persist the best performing surrogate model artifact.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run in automated verification mode (used by Loop Gate).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print(f"=== AutoCompliant-ML Surrogate Benchmark ===")
    print(f"Loading configuration from: {args.config}")
    config = load_topology_config(args.config)

    print(f"Topology: {config.topology.name} (D_in={config.D_in}, D_out={config.D_out})")
    print(f"Generating synthetic dataset with {args.samples} samples...")
    dataset = CompliantDataset.from_synthetic(config, n_samples=args.samples, seed=42)
    print(f"Dataset ready: {dataset.n_train} train samples, {dataset.n_test} test samples.")

    engine = ModelBenchmarkEngine(
        dataset=dataset,
        cv_folds=args.cv_folds if not args.check else 3,
        seed=42,
    )

    if args.check:
        # Fast model zoo subset for rapid automated gate verification
        candidate_models = [
            PolynomialRSMSurrogate(degree=2),
            XGBoostSurrogate(n_estimators=50, max_depth=3),
            LightGBMSurrogate(n_estimators=50, max_depth=4),
            RandomForestSurrogate(n_estimators=40, max_depth=6),
            MultiOutputGPR(n_restarts_optimizer=0),
        ]
    else:
        candidate_models = engine.get_default_model_zoo()

    print(f"Executing comparative benchmark across {len(candidate_models)} models...")
    result = engine.run_benchmark(models=candidate_models)

    # Export reports
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "leaderboard.json"
    md_path = out_dir / "leaderboard.md"

    result.to_json(json_path)
    result.to_markdown(md_path)
    print(f"Saved Leaderboard JSON: {json_path}")
    print(f"Saved Leaderboard Markdown: {md_path}")

    # Persist best surrogate model artifact
    art_dir = Path(args.artifact_dir)
    art_dir.mkdir(parents=True, exist_ok=True)
    model_path = art_dir / "best_surrogate.pkl"
    prep_path = art_dir / "preprocessor.pkl"

    result.best_model.save(model_path)
    with open(prep_path, "wb") as f:
        pickle.dump(dataset.preprocessor, f)

    print(f"Saved Best Model: {result.best_model.name} -> {model_path}")
    print(f"Saved Fitted Preprocessor -> {prep_path}")

    # Display Leaderboard
    print("\n" + "=" * 80)
    print(result.to_markdown())
    print("=" * 80)

    best_r2 = result.records[0]["test_r2_mean"]
    print(f"\nOptimal Surrogate: {result.best_model.name} (Test R² = {best_r2:.4f})")

    if best_r2 < 0.85:
        print(f"ERROR: Best model R2 ({best_r2:.4f}) is below acceptable threshold 0.85", file=sys.stderr)
        sys.exit(1)

    print("Benchmark successfully completed. Quality gate PASSED.")
    sys.exit(0)


if __name__ == "__main__":
    main()
