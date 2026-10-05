"""Multi-Criteria Decision Making (MCDM) and Knee-Point Selection via TOPSIS."""

from typing import Dict, List, Optional, Any
import numpy as np

from autocompliant.optimization.nsga2_solver import OptimizationResult


def topsis_select_best_tradeoff(
    opt_result: OptimizationResult,
    weights: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Identify the optimal knee-point compromise solution from the Pareto front using TOPSIS.

    TOPSIS ranks alternatives by calculating geometric distances to the Positive Ideal Solution (PIS)
    and Negative Ideal Solution (NIS).

    Args:
        opt_result: OptimizationResult containing Pareto front solutions.
        weights: Optional criteria weights for the objective functions. Defaults to equal weights.

    Returns:
        Dict[str, Any]: Selected optimal design inputs, responses, and TOPSIS scores.
    """
    if opt_result.n_pareto == 0:
        raise ValueError("Cannot perform TOPSIS selection on an empty Pareto set.")

    # Decision Matrix: We want to maximize original objective values
    # In pymoo, F_pareto minimizes objectives. Negating back gives the benefit criteria values.
    # Convert F_pareto: for 'maximize' objectives, value is -F.
    matrix = []
    for j, (_, direction) in enumerate(opt_result.problem.obj_indices):
        if direction == "maximize":
            # Higher is better
            matrix.append(-opt_result.F_pareto[:, j])
        else:
            # Lower is better (invert to benefit)
            matrix.append(-opt_result.F_pareto[:, j])
    decision_matrix = np.column_stack(matrix)

    n_alternatives, n_criteria = decision_matrix.shape

    # Criteria weights
    if weights is None:
        w = np.ones(n_criteria) / n_criteria
    else:
        w = np.array(weights, dtype=np.float64)
        w = w / np.sum(w)

    # 1. Vector normalization
    denominators = np.sqrt(np.sum(decision_matrix**2, axis=0))
    denominators = np.where(denominators == 0, 1e-12, denominators)
    norm_matrix = decision_matrix / denominators

    # 2. Weighted normalized decision matrix
    weighted_matrix = norm_matrix * w

    # 3. Determine Positive Ideal Solution (PIS) and Negative Ideal Solution (NIS)
    pis = np.max(weighted_matrix, axis=0)
    nis = np.min(weighted_matrix, axis=0)

    # 4. Calculate Euclidean distances to PIS and NIS
    d_plus = np.sqrt(np.sum((weighted_matrix - pis) ** 2, axis=1))
    d_minus = np.sqrt(np.sum((weighted_matrix - nis) ** 2, axis=1))

    # 5. Relative closeness to ideal solution: C_i = d_minus / (d_plus + d_minus)
    total_dist = d_plus + d_minus
    total_dist = np.where(total_dist == 0, 1e-12, total_dist)
    scores = d_minus / total_dist

    # Rank alternatives descending by score
    best_idx = int(np.argmax(scores))

    best_x = opt_result.X_pareto[best_idx]
    best_y = opt_result.Y_pareto[best_idx]

    inputs_dict = {
        name: float(best_x[i])
        for i, name in enumerate(opt_result.config.input_names)
    }
    outputs_dict = {
        name: float(best_y[i])
        for i, name in enumerate(opt_result.config.output_names)
    }

    return {
        "best_index": best_idx,
        "topsis_score": float(scores[best_idx]),
        "recommended_design_inputs": inputs_dict,
        "predicted_mechanical_responses": outputs_dict,
        "total_pareto_solutions": opt_result.n_pareto,
    }
