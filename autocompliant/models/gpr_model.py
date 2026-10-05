"""Multi-Output Gaussian Process Regression (GPR / Kriging) with Uncertainty Quantification."""

from typing import List, Optional, Tuple
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel, RBF

from autocompliant.models.base import BaseSurrogateModel


class MultiOutputGPR(BaseSurrogateModel):
    """Gaussian Process Regressor with independent output estimators.

    Provides exact analytical Bayesian posterior mean predictions and
    predictive standard deviation (sigma / uncertainty quantification) per output.
    """

    def __init__(
        self,
        kernel_type: str = "matern52",
        n_restarts_optimizer: int = 2,
        alpha: float = 1e-6,
        random_state: int = 42,
    ):
        super().__init__(name="GaussianProcessRegression")
        self.kernel_type = kernel_type
        self.n_restarts_optimizer = n_restarts_optimizer
        self.alpha = alpha
        self.random_state = random_state
        self.models: List[GaussianProcessRegressor] = []

    def _build_kernel(self, D_in: int):
        length_scales = np.ones(D_in)
        if self.kernel_type == "matern52":
            base_kernel = Matern(length_scale=length_scales, nu=2.5)
        elif self.kernel_type == "rbf":
            base_kernel = RBF(length_scale=length_scales)
        else:
            raise ValueError(f"Unsupported kernel type: {self.kernel_type}")

        return ConstantKernel(1.0, (1e-2, 1e2)) * base_kernel + WhiteKernel(
            noise_level=1e-4, noise_level_bounds=(1e-7, 1e-1)
        )

    def fit(self, X: np.ndarray, Y: np.ndarray) -> "MultiOutputGPR":
        X_arr = np.asarray(X, dtype=np.float64)
        Y_arr = np.asarray(Y, dtype=np.float64)

        if Y_arr.ndim == 1:
            Y_arr = Y_arr.reshape(-1, 1)

        self.D_in = X_arr.shape[1]
        self.D_out = Y_arr.shape[1]
        self.models = []

        for j in range(self.D_out):
            kernel = self._build_kernel(self.D_in)
            gpr = GaussianProcessRegressor(
                kernel=kernel,
                n_restarts_optimizer=self.n_restarts_optimizer,
                alpha=self.alpha,
                random_state=self.random_state + j,
                normalize_y=True,
            )
            gpr.fit(X_arr, Y_arr[:, j])
            self.models.append(gpr)

        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling predict.")
        X_arr = np.asarray(X, dtype=np.float64)
        preds = [model.predict(X_arr) for model in self.models]
        return np.column_stack(preds)

    def predict_with_uncertainty(
        self, X: np.ndarray
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling predict_with_uncertainty.")
        X_arr = np.asarray(X, dtype=np.float64)
        means = []
        stds = []
        for model in self.models:
            mean, std = model.predict(X_arr, return_std=True)
            means.append(mean)
            stds.append(std)
        return np.column_stack(means), np.column_stack(stds)
