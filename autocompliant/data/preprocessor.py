"""Adaptive preprocessor for multi-output compliant mechanism surrogate pipelines."""

from typing import Literal, Tuple, Union
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler

from autocompliant.config.schema import TopologyConfig


class AdaptivePreprocessor:
    """Config-driven feature and multi-output target scaler with strict data-leakage protection.

    Maintains separate, independent scaling pipelines for input design variables (X)
    and mechanical response targets (Y).
    """

    def __init__(self, scaler_type: Literal["standard", "minmax", "robust"] = "standard"):
        """Initialize the preprocessor.

        Args:
            scaler_type: Type of scaling algorithm ("standard", "minmax", or "robust").
        """
        self.scaler_type = scaler_type
        self.scaler_x = self._create_scaler(scaler_type)
        self.scaler_y = self._create_scaler(scaler_type)
        self.is_fitted = False

    @classmethod
    def from_config(cls, config: TopologyConfig) -> "AdaptivePreprocessor":
        """Instantiate preprocessor configured according to topology YAML settings."""
        scaler_type = config.surrogate.scaler
        return cls(scaler_type=scaler_type)

    def _create_scaler(self, scaler_type: str):
        if scaler_type == "standard":
            return StandardScaler()
        elif scaler_type == "minmax":
            return MinMaxScaler()
        elif scaler_type == "robust":
            return RobustScaler()
        else:
            raise ValueError(f"Unsupported scaler type: '{scaler_type}'. Supported: standard, minmax, robust.")

    def fit(self, X: Union[np.ndarray, list], Y: Union[np.ndarray, list]) -> "AdaptivePreprocessor":
        """Fit feature and target scalers exclusively on training data.

        Args:
            X: Input features array of shape (N, D_in).
            Y: Output targets array of shape (N, D_out).

        Returns:
            self: Fitted preprocessor instance.
        """
        X_arr = np.asarray(X, dtype=np.float64)
        Y_arr = np.asarray(Y, dtype=np.float64)

        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(-1, 1)
        if Y_arr.ndim == 1:
            Y_arr = Y_arr.reshape(-1, 1)

        self.scaler_x.fit(X_arr)
        self.scaler_y.fit(Y_arr)
        self.is_fitted = True
        return self

    def transform_x(self, X: Union[np.ndarray, list]) -> np.ndarray:
        """Transform input features using fitted scaler_x."""
        if not self.is_fitted:
            raise RuntimeError("AdaptivePreprocessor must be fitted before calling transform_x.")
        X_arr = np.asarray(X, dtype=np.float64)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(-1, 1)
        return self.scaler_x.transform(X_arr)

    def transform_y(self, Y: Union[np.ndarray, list]) -> np.ndarray:
        """Transform multi-output mechanical targets using fitted scaler_y."""
        if not self.is_fitted:
            raise RuntimeError("AdaptivePreprocessor must be fitted before calling transform_y.")
        Y_arr = np.asarray(Y, dtype=np.float64)
        if Y_arr.ndim == 1:
            Y_arr = Y_arr.reshape(-1, 1)
        return self.scaler_y.transform(Y_arr)

    def fit_transform(
        self, X: Union[np.ndarray, list], Y: Union[np.ndarray, list]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Fit scalers on X, Y and return transformed arrays."""
        self.fit(X, Y)
        return self.transform_x(X), self.transform_y(Y)

    def inverse_transform_x(self, X_scaled: Union[np.ndarray, list]) -> np.ndarray:
        """Invert scaling transformation on input features."""
        if not self.is_fitted:
            raise RuntimeError("AdaptivePreprocessor must be fitted before calling inverse_transform_x.")
        X_arr = np.asarray(X_scaled, dtype=np.float64)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(-1, 1)
        return self.scaler_x.inverse_transform(X_arr)

    def inverse_transform_y(self, Y_scaled: Union[np.ndarray, list]) -> np.ndarray:
        """Invert scaling transformation on multi-output predictions."""
        if not self.is_fitted:
            raise RuntimeError("AdaptivePreprocessor must be fitted before calling inverse_transform_y.")
        Y_arr = np.asarray(Y_scaled, dtype=np.float64)
        if Y_arr.ndim == 1:
            Y_arr = Y_arr.reshape(-1, 1)
        return self.scaler_y.inverse_transform(Y_arr)
