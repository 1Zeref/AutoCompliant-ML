"""Unit tests for data pipeline, adaptive preprocessor, and leakage prevention (Loop 2 Gate)."""

import pytest
import numpy as np
import pandas as pd

from autocompliant.config.loader import load_topology_config
from autocompliant.data.preprocessor import AdaptivePreprocessor
from autocompliant.data.synthetic_generator import SyntheticCompliantGenerator
from autocompliant.data.dataset import CompliantDataset


@pytest.fixture
def bridge_config():
    return load_topology_config("configs/bridge_amplifier.yaml")


def test_adaptive_preprocessor_shape_and_inverse(bridge_config):
    """Verify that AdaptivePreprocessor scales and recovers multi-output targets accurately."""
    preprocessor = AdaptivePreprocessor(scaler_type="standard")
    assert not preprocessor.is_fitted

    N = 100
    D_in = bridge_config.D_in
    D_out = bridge_config.D_out

    X = np.random.uniform(1.0, 10.0, size=(N, D_in))
    Y = np.random.uniform(5.0, 50.0, size=(N, D_out))

    X_scaled, Y_scaled = preprocessor.fit_transform(X, Y)

    assert preprocessor.is_fitted
    assert X_scaled.shape == (N, D_in)
    assert Y_scaled.shape == (N, D_out)

    # Standard scaled arrays should have mean ~ 0 and std ~ 1
    np.testing.assert_allclose(np.mean(X_scaled, axis=0), 0.0, atol=1e-7)
    np.testing.assert_allclose(np.std(X_scaled, axis=0), 1.0, atol=1e-7)

    # Invert transformation and check recovery precision
    X_recovered = preprocessor.inverse_transform_x(X_scaled)
    Y_recovered = preprocessor.inverse_transform_y(Y_scaled)

    np.testing.assert_allclose(X_recovered, X, atol=1e-6)
    np.testing.assert_allclose(Y_recovered, Y, atol=1e-6)


def test_no_data_leakage(bridge_config):
    """Ensure strict prevention of data leakage between training and testing sets."""
    preprocessor = AdaptivePreprocessor(scaler_type="standard")

    # 1. Transform before fit must fail
    with pytest.raises(RuntimeError):
        preprocessor.transform_x(np.array([[1.0, 2.0, 3.0, 4.0, 5.0]]))

    with pytest.raises(RuntimeError):
        preprocessor.transform_y(np.array([[1.0, 2.0, 3.0]]))

    # 2. Verify scaler statistics depend solely on the training partition
    X_train = np.array([[10.0, 10.0, 10.0, 10.0, 10.0], [20.0, 20.0, 20.0, 20.0, 20.0]])
    Y_train = np.array([[1.0, 2.0, 3.0], [3.0, 4.0, 5.0]])

    X_test = np.array([[1000.0, 1000.0, 1000.0, 1000.0, 1000.0]])
    Y_test = np.array([[100.0, 200.0, 300.0]])

    preprocessor.fit(X_train, Y_train)

    # Check fitted mean is strictly equal to X_train mean, ignoring X_test
    expected_train_mean = np.mean(X_train, axis=0)
    np.testing.assert_allclose(preprocessor.scaler_x.mean_, expected_train_mean)

    # Combined mean with test would be vastly different (~343)
    combined_mean = np.mean(np.vstack([X_train, X_test]), axis=0)
    assert not np.allclose(preprocessor.scaler_x.mean_, combined_mean)


def test_synthetic_generator_bounds_and_physical_validity(bridge_config):
    """Verify synthetic generator samples within configured geometric bounds and produces physical responses."""
    generator = SyntheticCompliantGenerator(bridge_config, seed=42)
    df = generator.generate(n_samples=300, noise_std=0.01)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 300

    # Verify input columns stay within [min, max]
    lower, upper = bridge_config.bounds
    for i, col in enumerate(bridge_config.input_names):
        assert df[col].min() >= lower[i] - 1e-9
        assert df[col].max() <= upper[i] + 1e-9

    # Verify physical responses (F1 > 0, F2 > 0, f > 100 Hz)
    assert (df["safety_factor"] > 0).all()
    assert (df["output_displacement"] > 0).all()
    assert (df["resonant_frequency"] > 100.0).all()


def test_compliant_dataset_train_test_split(bridge_config):
    """Verify end-to-end dataset manager, partitioning ratios, and getters."""
    dataset = CompliantDataset.from_synthetic(bridge_config, n_samples=200, seed=42)

    # Check split ratio (default test_size=0.2 -> 160 train, 40 test)
    assert dataset.n_train == 160
    assert dataset.n_test == 40

    # Scaled getters
    X_train_s, Y_train_s = dataset.get_train_data(scaled=True)
    X_test_s, Y_test_s = dataset.get_test_data(scaled=True)

    assert X_train_s.shape == (160, bridge_config.D_in)
    assert Y_train_s.shape == (160, bridge_config.D_out)
    assert X_test_s.shape == (40, bridge_config.D_in)
    assert Y_test_s.shape == (40, bridge_config.D_out)

    # Unscaled getters
    X_train_raw, Y_train_raw = dataset.get_train_data(scaled=False)
    assert np.allclose(X_train_raw, dataset.X_train_raw)


def test_dataset_missing_column_raises_error(bridge_config):
    """Ensure dataset instantiation fails when required schema columns are absent."""
    df_incomplete = pd.DataFrame({"hinge_thickness_t": [0.5, 0.6]})
    with pytest.raises(ValueError) as exc:
        CompliantDataset.from_dataframe(df_incomplete, bridge_config)
    assert "missing required input columns" in str(exc.value)
