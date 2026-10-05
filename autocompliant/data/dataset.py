"""Dataset abstraction and pipeline manager for compliant mechanism surrogate training."""

from pathlib import Path
from typing import Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from autocompliant.config.schema import TopologyConfig
from autocompliant.data.preprocessor import AdaptivePreprocessor
from autocompliant.data.synthetic_generator import SyntheticCompliantGenerator


class CompliantDataset:
    """End-to-end dataset manager with train/test partitioning and adaptive preprocessor.

    Guarantees no data leakage: Preprocessor is fitted strictly on the training partition.
    """

    def __init__(
        self,
        X_train: np.ndarray,
        X_test: np.ndarray,
        Y_train: np.ndarray,
        Y_test: np.ndarray,
        config: TopologyConfig,
        preprocessor: Optional[AdaptivePreprocessor] = None,
    ):
        self.config = config
        self.X_train_raw = np.asarray(X_train, dtype=np.float64)
        self.X_test_raw = np.asarray(X_test, dtype=np.float64)
        self.Y_train_raw = np.asarray(Y_train, dtype=np.float64)
        self.Y_test_raw = np.asarray(Y_test, dtype=np.float64)

        # Initialize and fit preprocessor strictly on training data
        self.preprocessor = preprocessor or AdaptivePreprocessor.from_config(config)
        if not self.preprocessor.is_fitted:
            self.preprocessor.fit(self.X_train_raw, self.Y_train_raw)

    @classmethod
    def from_dataframe(
        cls,
        df: pd.DataFrame,
        config: TopologyConfig,
        test_size: Optional[float] = None,
        random_state: Optional[int] = None,
        preprocessor: Optional[AdaptivePreprocessor] = None,
    ) -> "CompliantDataset":
        """Instantiate dataset from a pandas DataFrame according to topology schema."""
        test_sz = test_size if test_size is not None else config.surrogate.test_size
        rnd = random_state if random_state is not None else config.surrogate.random_state

        # Validate required columns
        missing_inputs = set(config.input_names) - set(df.columns)
        if missing_inputs:
            raise ValueError(f"DataFrame is missing required input columns: {missing_inputs}")

        missing_outputs = set(config.output_names) - set(df.columns)
        if missing_outputs:
            raise ValueError(f"DataFrame is missing required output columns: {missing_outputs}")

        X = df[config.input_names].to_numpy(dtype=np.float64)
        Y = df[config.output_names].to_numpy(dtype=np.float64)

        X_train, X_test, Y_train, Y_test = train_test_split(
            X, Y, test_size=test_sz, random_state=rnd
        )

        return cls(X_train, X_test, Y_train, Y_test, config=config, preprocessor=preprocessor)

    @classmethod
    def from_csv(
        cls,
        file_path: Union[str, Path],
        config: TopologyConfig,
        test_size: Optional[float] = None,
        random_state: Optional[int] = None,
    ) -> "CompliantDataset":
        """Load and instantiate dataset from a CSV file."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Data file not found at: {path.resolve()}")
        df = pd.read_csv(path)
        return cls.from_dataframe(df, config, test_size=test_size, random_state=random_state)

    @classmethod
    def from_synthetic(
        cls,
        config: TopologyConfig,
        n_samples: int = 500,
        noise_std: float = 0.01,
        seed: Optional[int] = None,
    ) -> "CompliantDataset":
        """Generate analytical synthetic benchmark data and build dataset."""
        rnd = seed if seed is not None else config.surrogate.random_state
        generator = SyntheticCompliantGenerator(config, seed=rnd)
        df = generator.generate(n_samples=n_samples, noise_std=noise_std)
        return cls.from_dataframe(df, config, random_state=rnd)

    def get_train_data(self, scaled: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """Retrieve training inputs and targets (scaled or raw)."""
        if scaled:
            return (
                self.preprocessor.transform_x(self.X_train_raw),
                self.preprocessor.transform_y(self.Y_train_raw),
            )
        return self.X_train_raw.copy(), self.Y_train_raw.copy()

    def get_test_data(self, scaled: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """Retrieve testing inputs and targets (scaled or raw)."""
        if scaled:
            return (
                self.preprocessor.transform_x(self.X_test_raw),
                self.preprocessor.transform_y(self.Y_test_raw),
            )
        return self.X_test_raw.copy(), self.Y_test_raw.copy()

    @property
    def n_train(self) -> int:
        return len(self.X_train_raw)

    @property
    def n_test(self) -> int:
        return len(self.X_test_raw)
