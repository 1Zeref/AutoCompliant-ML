"""Baseline Polynomial Response Surface Methodology (RSM) Surrogate Model."""

import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import Ridge

from autocompliant.models.base import BaseSurrogateModel


class PolynomialRSMSurrogate(BaseSurrogateModel):
    """Response Surface Methodology (Degree-2 Polynomial Regression) Baseline."""

    def __init__(self, degree: int = 2, alpha: float = 1.0):
        super().__init__(name="PolynomialRSM")
        self.degree = degree
        self.alpha = alpha
        self.model = make_pipeline(
            PolynomialFeatures(degree=self.degree, include_bias=True),
            Ridge(alpha=self.alpha),
        )

    def fit(self, X: np.ndarray, Y: np.ndarray) -> "PolynomialRSMSurrogate":
        X_arr = np.asarray(X, dtype=np.float64)
        Y_arr = np.asarray(Y, dtype=np.float64)
        if Y_arr.ndim == 1:
            Y_arr = Y_arr.reshape(-1, 1)

        self.D_in = X_arr.shape[1]
        self.D_out = Y_arr.shape[1]

        self.model.fit(X_arr, Y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling predict.")
        X_arr = np.asarray(X, dtype=np.float64)
        return self.model.predict(X_arr)
