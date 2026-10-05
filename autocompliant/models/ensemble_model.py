"""Weighted Ensemble Surrogate Model with Uncertainty Quantification for AutoCompliant-ML."""

from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from autocompliant.models.base import BaseSurrogateModel


class WeightedEnsembleSurrogate(BaseSurrogateModel):
    """Ensemble surrogate model combining multiple multi-output predictors.

    Weights are assigned dynamically based on validation / cross-validation R² scores:
        w_m \\propto \\frac{\\max(0, R^2_m)}{1 - \\min(0.999, R^2_m) + \\epsilon}

    In addition, it calculates predictive epistemic uncertainty \\sigma(x) via weighted
    variance across member predictions:
        \\sigma^2(x) = \\sum_{m=1}^M w_m (\\hat{y}_m(x) - \\hat{y}_{\\text{ensemble}}(x))^2
    """

    def __init__(
        self,
        models: Optional[List[BaseSurrogateModel]] = None,
        weights: Optional[List[float]] = None,
        name: str = "WeightedEnsemble",
    ):
        super().__init__(name=name)
        self.models: List[BaseSurrogateModel] = models or []
        self.weights: Optional[np.ndarray] = None
        if weights is not None:
            w = np.array(weights, dtype=np.float64)
            if np.sum(w) > 0:
                self.weights = w / np.sum(w)
        self.r2_scores: Dict[str, float] = {}

    @classmethod
    def from_fitted_models(
        cls,
        models: List[BaseSurrogateModel],
        scores: Dict[str, float],
        name: str = "WeightedEnsemble",
        epsilon: float = 1e-4,
    ) -> "WeightedEnsembleSurrogate":
        """Build ensemble from pre-fitted models weighted by their R² performance.

        Args:
            models: List of fitted surrogate models.
            scores: Dict mapping model name to validation/test R² score.
            name: Ensemble name.
            epsilon: Numerical stability parameter.
        """
        valid_models = []
        raw_weights = []

        for m in models:
            r2 = scores.get(m.name, 0.0)
            valid_models.append(m)
            # Clip r2 below at 0.0 (no negative weights) and above at 0.999
            clipped_r2 = max(0.0, float(r2))
            w = clipped_r2 / (1.0 - min(0.999, clipped_r2) + epsilon)
            raw_weights.append(w)

        raw_weights = np.array(raw_weights, dtype=np.float64)
        if np.sum(raw_weights) <= 1e-12:
            norm_weights = np.ones(len(valid_models)) / len(valid_models)
        else:
            norm_weights = raw_weights / np.sum(raw_weights)

        ensemble = cls(models=valid_models, weights=norm_weights.tolist(), name=name)
        ensemble.r2_scores = scores
        if valid_models:
            ensemble.is_fitted = True
            ensemble.D_in = valid_models[0].D_in
            ensemble.D_out = valid_models[0].D_out
        return ensemble

    def fit(self, X: np.ndarray, Y: np.ndarray) -> "WeightedEnsembleSurrogate":
        """Fit all candidate base models on X and Y, and compute equal or CV weights."""
        X_arr = np.asarray(X, dtype=np.float64)
        Y_arr = np.asarray(Y, dtype=np.float64)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(-1, 1)
        if Y_arr.ndim == 1:
            Y_arr = Y_arr.reshape(-1, 1)

        self.D_in = X_arr.shape[1]
        self.D_out = Y_arr.shape[1]

        scores = {}
        for m in self.models:
            m.fit(X_arr, Y_arr)
            r2 = m.score_r2(X_arr, Y_arr)
            scores[m.name] = r2

        self.r2_scores = scores
        if self.weights is None:
            # Derive weights from training R2
            raw_w = [max(0.0, scores[m.name]) / (1.0 - min(0.999, max(0.0, scores[m.name])) + 1e-4) for m in self.models]
            raw_w = np.array(raw_w, dtype=np.float64)
            if np.sum(raw_w) <= 1e-12:
                self.weights = np.ones(len(self.models)) / len(self.models)
            else:
                self.weights = raw_w / np.sum(raw_w)

        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Weighted average prediction across all ensemble members."""
        if not self.is_fitted or not self.models:
            raise RuntimeError("WeightedEnsembleSurrogate must be fitted before predict.")

        X_arr = np.asarray(X, dtype=np.float64)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1)

        predictions = [m.predict(X_arr) for m in self.models]  # list of (N, D_out)
        stacked = np.stack(predictions, axis=0)  # shape (M, N, D_out)

        w = self.weights[:, np.newaxis, np.newaxis]  # shape (M, 1, 1)
        ensemble_pred = np.sum(stacked * w, axis=0)  # shape (N, D_out)
        return ensemble_pred

    def predict_with_uncertainty(
        self, X: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Predict responses along with ensemble epistemic uncertainty \\sigma(x).

        Returns:
            Tuple[np.ndarray, np.ndarray]:
                - ensemble_mean: (N, D_out)
                - ensemble_std: (N, D_out) standard deviation across models (+ member variance if available)
        """
        if not self.is_fitted or not self.models:
            raise RuntimeError("WeightedEnsembleSurrogate must be fitted before predict_with_uncertainty.")

        X_arr = np.asarray(X, dtype=np.float64)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1)

        predictions = []
        member_vars = []

        for m in self.models:
            pred, std = m.predict_with_uncertainty(X_arr)
            predictions.append(pred)
            if std is not None:
                member_vars.append(std ** 2)
            else:
                member_vars.append(np.zeros_like(pred))

        stacked_pred = np.stack(predictions, axis=0)  # (M, N, D_out)
        w = self.weights[:, np.newaxis, np.newaxis]

        mean_pred = np.sum(stacked_pred * w, axis=0)  # (N, D_out)

        # Variance across model predictions (epistemic disagreement)
        diff_sq = (stacked_pred - mean_pred[np.newaxis, :, :]) ** 2
        ensemble_var = np.sum(w * diff_sq, axis=0)

        # Add member-intrinsic variance if any
        stacked_vars = np.stack(member_vars, axis=0)
        intrinsic_var = np.sum(w * stacked_vars, axis=0)

        total_std = np.sqrt(ensemble_var + intrinsic_var)
        return mean_pred, total_std
