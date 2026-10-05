"""Base interface specification for all multi-output compliant mechanism surrogate models."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple, Union
import pickle
import numpy as np
from sklearn.metrics import r2_score


class BaseSurrogateModel(ABC):
    """Abstract Base Class for Multi-Output Surrogate Models.

    Enforces uniform API for model training, inference, uncertainty quantification,
    and artifact persistence.
    """

    def __init__(self, name: str):
        self.name = name
        self.is_fitted = False
        self.D_in: Optional[int] = None
        self.D_out: Optional[int] = None

    @abstractmethod
    def fit(self, X: np.ndarray, Y: np.ndarray) -> "BaseSurrogateModel":
        """Fit the surrogate model on input features X and multi-output responses Y.

        Args:
            X: Input array of shape (N, D_in).
            Y: Output targets array of shape (N, D_out).

        Returns:
            self
        """
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict multi-output responses for given design inputs.

        Args:
            X: Input array of shape (N, D_in).

        Returns:
            np.ndarray: Predicted responses of shape (N, D_out).
        """
        pass

    def predict_with_uncertainty(
        self, X: np.ndarray
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Predict responses along with predictive uncertainty (standard deviation).

        Args:
            X: Input array of shape (N, D_in).

        Returns:
            Tuple[np.ndarray, Optional[np.ndarray]]: (predictions, uncertainty_std).
            If model does not quantify uncertainty, second element is None.
        """
        return self.predict(X), None

    def score_r2(self, X: np.ndarray, Y: np.ndarray) -> float:
        """Compute the average R-squared score across all output targets."""
        Y_pred = self.predict(X)
        return float(r2_score(Y, Y_pred, multioutput="uniform_average"))

    def score_r2_per_output(self, X: np.ndarray, Y: np.ndarray) -> np.ndarray:
        """Compute R-squared scores for each output dimension individually."""
        Y_pred = self.predict(X)
        return r2_score(Y, Y_pred, multioutput="raw_values")

    def save(self, path: Union[str, Path]) -> None:
        """Persist the model artifact to disk."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "BaseSurrogateModel":
        """Load a persisted model artifact from disk."""
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"Model artifact not found at: {source.resolve()}")
        with open(source, "rb") as f:
            model = pickle.load(f)
        if not isinstance(model, cls):
            raise TypeError(f"Loaded artifact is an instance of {type(model)}, expected {cls}.")
        return model
