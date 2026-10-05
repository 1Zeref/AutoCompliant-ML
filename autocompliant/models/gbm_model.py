"""Gradient Boosted Decision Trees and Ensemble Surrogate Models."""

from typing import Optional
import numpy as np
from sklearn.multioutput import MultiOutputRegressor
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor

from autocompliant.models.base import BaseSurrogateModel


class XGBoostSurrogate(BaseSurrogateModel):
    """Multi-Output Extreme Gradient Boosting (XGBoost) Surrogate Model."""

    def __init__(
        self,
        n_estimators: int = 150,
        max_depth: int = 4,
        learning_rate: float = 0.08,
        subsample: float = 0.85,
        random_state: int = 42,
    ):
        super().__init__(name="XGBoost")
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.random_state = random_state
        self.model: Optional[MultiOutputRegressor] = None

    def fit(self, X: np.ndarray, Y: np.ndarray) -> "XGBoostSurrogate":
        X_arr = np.asarray(X, dtype=np.float64)
        Y_arr = np.asarray(Y, dtype=np.float64)
        if Y_arr.ndim == 1:
            Y_arr = Y_arr.reshape(-1, 1)

        self.D_in = X_arr.shape[1]
        self.D_out = Y_arr.shape[1]

        base_estimator = XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            random_state=self.random_state,
            verbosity=0,
            n_jobs=-1,
        )
        self.model = MultiOutputRegressor(base_estimator)
        self.model.fit(X_arr, Y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model must be fitted before calling predict.")
        X_arr = np.asarray(X, dtype=np.float64)
        return self.model.predict(X_arr)


class LightGBMSurrogate(BaseSurrogateModel):
    """Multi-Output LightGBM Surrogate Model."""

    def __init__(
        self,
        n_estimators: int = 150,
        max_depth: int = 5,
        learning_rate: float = 0.08,
        num_leaves: int = 31,
        random_state: int = 42,
    ):
        super().__init__(name="LightGBM")
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.random_state = random_state
        self.model: Optional[MultiOutputRegressor] = None

    def fit(self, X: np.ndarray, Y: np.ndarray) -> "LightGBMSurrogate":
        X_arr = np.asarray(X, dtype=np.float64)
        Y_arr = np.asarray(Y, dtype=np.float64)
        if Y_arr.ndim == 1:
            Y_arr = Y_arr.reshape(-1, 1)

        self.D_in = X_arr.shape[1]
        self.D_out = Y_arr.shape[1]

        base_estimator = LGBMRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            num_leaves=self.num_leaves,
            random_state=self.random_state,
            verbose=-1,
            n_jobs=-1,
        )
        self.model = MultiOutputRegressor(base_estimator)
        self.model.fit(X_arr, Y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model must be fitted before calling predict.")
        X_arr = np.asarray(X, dtype=np.float64)
        return self.model.predict(X_arr)


class RandomForestSurrogate(BaseSurrogateModel):
    """Multi-Output Random Forest Ensemble Baseline."""

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: Optional[int] = 10,
        random_state: int = 42,
    ):
        super().__init__(name="RandomForest")
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        self.model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=self.random_state,
            n_jobs=-1,
        )

    def fit(self, X: np.ndarray, Y: np.ndarray) -> "RandomForestSurrogate":
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
