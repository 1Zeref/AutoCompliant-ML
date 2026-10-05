"""Multi-output mechanical response metrics evaluation engine."""

from typing import Dict, List, Optional, Any
import numpy as np
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error


def evaluate_multioutput_metrics(
    Y_true: np.ndarray,
    Y_pred: np.ndarray,
    output_symbols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compute comprehensive multi-output regression metrics.

    Args:
        Y_true: Ground truth array of shape (N, D_out).
        Y_pred: Predicted responses array of shape (N, D_out).
        output_symbols: Optional list of output symbols (e.g. ['F1', 'F2', 'f']).

    Returns:
        Dict[str, Any]: Dictionary containing aggregate means and per-output metrics.
    """
    Y_t = np.asarray(Y_true, dtype=np.float64)
    Y_p = np.asarray(Y_pred, dtype=np.float64)

    if Y_t.ndim == 1:
        Y_t = Y_t.reshape(-1, 1)
    if Y_p.ndim == 1:
        Y_p = Y_p.reshape(-1, 1)

    D_out = Y_t.shape[1]
    symbols = output_symbols or [f"Y{j+1}" for j in range(D_out)]

    # Aggregate uniform average metrics
    r2_mean = float(r2_score(Y_t, Y_p, multioutput="uniform_average"))
    rmse_mean = float(np.sqrt(mean_squared_error(Y_t, Y_p)))
    mae_mean = float(mean_absolute_error(Y_t, Y_p))

    # Mean Absolute Percentage Error (MAPE)
    eps = 1e-8
    mape_per_dim = np.mean(np.abs((Y_t - Y_p) / (np.abs(Y_t) + eps)), axis=0) * 100.0
    mape_mean = float(np.mean(mape_per_dim))

    # Per-output breakdown
    per_output = {}
    r2_raw = r2_score(Y_t, Y_p, multioutput="raw_values")
    mse_raw = mean_squared_error(Y_t, Y_p, multioutput="raw_values")
    mae_raw = mean_absolute_error(Y_t, Y_p, multioutput="raw_values")

    for j, sym in enumerate(symbols):
        per_output[sym] = {
            "r2": float(r2_raw[j]),
            "rmse": float(np.sqrt(mse_raw[j])),
            "mae": float(mae_raw[j]),
            "mape": float(mape_per_dim[j]),
            "max_abs_error": float(np.max(np.abs(Y_t[:, j] - Y_p[:, j]))),
        }

    return {
        "r2_mean": r2_mean,
        "rmse_mean": rmse_mean,
        "mae_mean": mae_mean,
        "mape_mean": mape_mean,
        "per_output": per_output,
    }
