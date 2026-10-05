"""Multi-Criteria Decision Making (MCDM) and Knee-Point Selection via TOPSIS."""

from typing import Dict, List, Optional, Any
import numpy as np

from autocompliant.optimization.nsga2_solver import OptimizationResult


def calculate_extrapolation_risk(
    design_point: np.ndarray,
    train_x: np.ndarray,
) -> Dict[str, Any]:
    """Calculate distance of a design point from training distribution to estimate extrapolation risk.

    Args:
        design_point: 1D array of design variables (D_in,).
        train_x: 2D array of training design inputs (N_train, D_in).

    Returns:
        Dict[str, Any] containing z-score distance, extrapolation category, and confidence score (0-100%).
    """
    x = np.asarray(design_point, dtype=np.float64).flatten()
    X_tr = np.asarray(train_x, dtype=np.float64)

    mean = np.mean(X_tr, axis=0)
    std = np.std(X_tr, axis=0)
    std = np.where(std < 1e-12, 1.0, std)

    # Standardized z-score distance
    z_scores = np.abs((x - mean) / std)
    max_z = float(np.max(z_scores))
    mean_z = float(np.mean(z_scores))

    # Confidence score calculation: e^(-0.5 * mean_z) * 100%
    confidence_pct = max(0.0, min(100.0, float(np.exp(-0.4 * max_z) * 100.0)))

    if max_z <= 1.5:
        level = "High Confidence"
        level_vi = "Độ tin cậy cao (Nội suy an toàn)"
        risk_color = "emerald"
    elif max_z <= 2.5:
        level = "Moderate Confidence"
        level_vi = "Độ tin cậy trung bình (Gần biên dữ liệu)"
        risk_color = "amber"
    else:
        level = "High Extrapolation Risk"
        level_vi = "Nguy cơ ngoại suy cao (Ngoài vùng huấn luyện)"
        risk_color = "rose"

    return {
        "max_z_score": round(max_z, 3),
        "mean_z_score": round(mean_z, 3),
        "confidence_percentage": round(confidence_pct, 1),
        "confidence_level": level,
        "confidence_level_vi": level_vi,
        "risk_color": risk_color,
    }


def topsis_select_best_tradeoff(
    opt_result: OptimizationResult,
    weights: Optional[List[float]] = None,
    train_x: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Identify the optimal knee-point compromise solution from the Pareto front using TOPSIS.

    TOPSIS ranks alternatives by calculating geometric distances to the Positive Ideal Solution (PIS)
    and Negative Ideal Solution (NIS).

    Args:
        opt_result: OptimizationResult containing Pareto front solutions.
        weights: Optional criteria weights for the objective functions. Defaults to equal weights.
        train_x: Optional training feature array to evaluate extrapolation risk of the chosen design.

    Returns:
        Dict[str, Any]: Selected optimal design inputs, responses, TOPSIS scores, and extrapolation risk.
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

    res = {
        "best_index": best_idx,
        "topsis_score": float(scores[best_idx]),
        "recommended_design_inputs": inputs_dict,
        "predicted_mechanical_responses": outputs_dict,
        "total_pareto_solutions": opt_result.n_pareto,
    }

    if train_x is not None:
        res["extrapolation_risk"] = calculate_extrapolation_risk(best_x, train_x)

    return res
