"""Unit tests for Pymoo Problem formulation, NSGA-II solver, and TOPSIS MCDM (Loop 5 Gate)."""

import pytest
import numpy as np

from autocompliant.config.loader import load_topology_config
from autocompliant.data.dataset import CompliantDataset
from autocompliant.models import XGBoostSurrogate, PolynomialRSMSurrogate
from autocompliant.optimization.problem import CompliantMechanismProblem
from autocompliant.optimization.nsga2_solver import NSGA2Solver
from autocompliant.optimization.mcdm import topsis_select_best_tradeoff


@pytest.fixture(scope="module")
def optimization_setup():
    config = load_topology_config("configs/bridge_amplifier.yaml")
    dataset = CompliantDataset.from_synthetic(config, n_samples=250, seed=42)

    X_train, Y_train = dataset.get_train_data(scaled=True)
    surrogate = PolynomialRSMSurrogate(degree=2)
    surrogate.fit(X_train, Y_train)

    problem = CompliantMechanismProblem(
        config=config,
        surrogate_model=surrogate,
        preprocessor=dataset.preprocessor,
    )
    return config, problem, dataset


def test_compliant_mechanism_problem_evaluation(optimization_setup):
    """Verify problem formulation dimensions, objective formulation, and constraints."""
    config, problem, _ = optimization_setup

    assert problem.n_var == 5
    assert problem.n_obj == 2  # F2 and f
    assert problem.n_ieq_constr == 1  # F1 >= 1.5

    # Evaluate batch of 10 random design vectors
    lower, upper = config.bounds
    X_sample = np.random.uniform(lower, upper, size=(10, 5))

    out = {}
    problem._evaluate(X_sample, out)

    assert "F" in out
    assert "G" in out
    assert out["F"].shape == (10, 2)
    assert out["G"].shape == (10, 1)


def test_nsga2_solver_finds_pareto_front(optimization_setup):
    """Verify evolutionary solver finds non-dominated Pareto front satisfying constraints."""
    _, problem, _ = optimization_setup

    solver = NSGA2Solver(pop_size=40, n_generations=25, seed=42)
    opt_res = solver.solve(problem)

    assert opt_res.runtime_sec < 4.0, f"Execution took too long: {opt_res.runtime_sec:.2f}s"
    assert opt_res.n_pareto >= 5, f"Expected at least 5 Pareto solutions, got {opt_res.n_pareto}"

    # Verify all Pareto solutions strictly satisfy the safety constraint F1 >= 1.5
    # F1 is index 0 in bridge_amplifier.yaml outputs
    F1_values = opt_res.Y_pareto[:, 0]
    assert np.all(F1_values >= 1.49), f"Some Pareto solutions violated safety factor >= 1.5: {np.min(F1_values)}"

    df = opt_res.to_dataframe()
    assert len(df) == opt_res.n_pareto
    assert "hinge_thickness_t" in df.columns
    assert "output_displacement" in df.columns


def test_topsis_knee_point_selection(optimization_setup):
    """Verify TOPSIS multi-criteria selection of optimal knee-point compromise solution."""
    config, problem, _ = optimization_setup

    solver = NSGA2Solver(pop_size=40, n_generations=25, seed=42)
    opt_res = solver.solve(problem)

    tradeoff = topsis_select_best_tradeoff(opt_res)

    assert "recommended_design_inputs" in tradeoff
    assert "predicted_mechanical_responses" in tradeoff
    assert 0.0 <= tradeoff["topsis_score"] <= 1.0

    inputs = tradeoff["recommended_design_inputs"]
    lower, upper = config.bounds

    # Ensure recommended inputs lie strictly inside geometric bounds
    for i, name in enumerate(config.input_names):
        val = inputs[name]
        assert lower[i] <= val <= upper[i], f"Input {name}={val} out of bounds [{lower[i]}, {upper[i]}]"

    responses = tradeoff["predicted_mechanical_responses"]
    assert responses["safety_factor"] >= 1.49
    assert responses["output_displacement"] > 0
    assert responses["resonant_frequency"] > 100
