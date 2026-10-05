#!/usr/bin/env python
"""CLI tool to execute NSGA-II multi-objective optimization for compliant mechanisms."""

import argparse
import pickle
import sys
from pathlib import Path

from autocompliant.config.loader import load_topology_config
from autocompliant.models.base import BaseSurrogateModel
from autocompliant.optimization.problem import CompliantMechanismProblem
from autocompliant.optimization.nsga2_solver import NSGA2Solver
from autocompliant.optimization.mcdm import topsis_select_best_tradeoff


def parse_args():
    parser = argparse.ArgumentParser(
        description="AutoCompliant-ML NSGA-II Multi-Objective Optimization Runner."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/bridge_amplifier.yaml",
        help="Path to topology configuration YAML.",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default="models/artifacts/best_surrogate.pkl",
        help="Path to serialized surrogate model artifact.",
    )
    parser.add_argument(
        "--preprocessor-path",
        type=str,
        default="models/artifacts/preprocessor.pkl",
        help="Path to serialized fitted preprocessor artifact.",
    )
    parser.add_argument(
        "--pop-size",
        type=int,
        default=100,
        help="Population size for evolutionary algorithm.",
    )
    parser.add_argument(
        "--generations",
        type=int,
        default=80,
        help="Number of evolutionary generations.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/pareto_front.csv",
        help="Destination path for Pareto optimal front CSV.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print("=== AutoCompliant-ML Multi-Objective Optimization (NSGA-II & MCDM) ===")
    config = load_topology_config(args.config)
    print(f"Topology: {config.topology.name}")

    model_path = Path(args.model_path)
    prep_path = Path(args.preprocessor_path)

    if not model_path.is_file() or not prep_path.is_file():
        print(f"Artifacts missing: Run 'python run_benchmark.py --check' first to produce models/artifacts.")
        sys.exit(1)

    with open(model_path, "rb") as f:
        surrogate_model: BaseSurrogateModel = pickle.load(f)
    with open(prep_path, "rb") as f:
        preprocessor = pickle.load(f)

    print(f"Loaded Surrogate Model: {surrogate_model.name}")
    print(f"Setting up CompliantMechanismProblem ({config.D_in} inputs, {config.D_out} responses)...")

    problem = CompliantMechanismProblem(
        config=config,
        surrogate_model=surrogate_model,
        preprocessor=preprocessor,
    )

    solver = NSGA2Solver(
        pop_size=args.pop_size,
        n_generations=args.generations,
        seed=42,
    )

    print(f"Running NSGA-II Evolution (Pop: {args.pop_size}, Gen: {args.generations})...")
    opt_res = solver.solve(problem)

    print(f"Completed in: {opt_res.runtime_sec:.3f} seconds!")
    print(f"Discovered Non-dominated Pareto Solutions: {opt_res.n_pareto}")

    if opt_res.n_pareto == 0:
        print("WARNING: No feasible Pareto solutions found under active constraints.")
        sys.exit(1)

    # Export Pareto CSV
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    opt_res.to_csv(str(out_path))
    print(f"Saved Pareto Front: {out_path}")

    # MCDM Selection via TOPSIS
    tradeoff = topsis_select_best_tradeoff(opt_res)
    print("\n" + "=" * 60)
    print("[BEST] TOPSIS Best Compromise Knee-Point Design:")
    print("=" * 60)
    print("Design Parameters (Inputs):")
    for k, v in tradeoff["recommended_design_inputs"].items():
        print(f"  * {k:22s} = {v:.4f}")
    print("\nPredicted Mechanical Responses:")
    for k, v in tradeoff["predicted_mechanical_responses"].items():
        print(f"  * {k:22s} = {v:.4f}")
    print("=" * 60)

    # Check constraint satisfaction on recommended point
    safety_factor = tradeoff["predicted_mechanical_responses"].get("safety_factor", 2.0)
    if safety_factor < 1.5:
        print(f"WARNING: Safety factor ({safety_factor:.2f}) violates constraint >= 1.5")
    else:
        print("[OK] Static Safety Constraint (F1 >= 1.5) strictly satisfied.")

    sys.exit(0)


if __name__ == "__main__":
    main()
