"""Adaptive preprocessor for multi-output compliant mechanism surrogate pipelines."""

from typing import Literal, Tuple, Union, Any, Optional, List
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


def filter_outliers(
    df,
    columns=None,
    method: Literal["iqr", "zscore"] = "iqr",
    factor: float = 1.5,
) -> Tuple[Any, np.ndarray]:
    """Detect and filter abnormal FEA distortion or convergence failure data points.

    Args:
        df: Input pandas DataFrame containing mechanical data.
        columns: Target columns to inspect for anomalies (e.g. outputs or inputs).
                 If None, inspects all numeric columns.
        method: Outlier detection method ('iqr' or 'zscore').
        factor: Multiplier for IQR (default 1.5) or standard deviation threshold (default 3.0 for zscore).

    Returns:
        Tuple[pd.DataFrame, np.ndarray]: (cleaned_df, outlier_mask_boolean_array).
            outlier_mask is True for anomalous rows that were filtered out.
    """
    import pandas as pd

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    if columns is None:
        target_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    else:
        target_cols = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]

    if not target_cols:
        return df.copy(), np.zeros(len(df), dtype=bool)

    outlier_mask = np.zeros(len(df), dtype=bool)

    for col in target_cols:
        series = df[col].astype(float)
        if method == "iqr":
            q25 = series.quantile(0.25)
            q75 = series.quantile(0.75)
            iqr = q75 - q25
            if iqr > 1e-12:
                lower_bound = q25 - factor * iqr
                upper_bound = q75 + factor * iqr
                col_mask = (series < lower_bound) | (series > upper_bound)
                outlier_mask = outlier_mask | col_mask.to_numpy()
        elif method == "zscore":
            mean = series.mean()
            std = series.std(ddof=0)
            if std > 1e-12:
                z = np.abs((series - mean) / std)
                col_mask = z > factor
                outlier_mask = outlier_mask | col_mask.to_numpy()

    cleaned_df = df.loc[~outlier_mask].reset_index(drop=True)
    return cleaned_df, outlier_mask

