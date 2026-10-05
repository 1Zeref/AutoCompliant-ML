"""Unit tests for Multi-Output Surrogate Model Zoo and R2 Floor Verification (Loop 3 Gate)."""

import pytest
import numpy as np
from pathlib import Path

from autocompliant.config.loader import load_topology_config
from autocompliant.data.dataset import CompliantDataset
from autocompliant.models import (
    MultiOutputGPR,
    XGBoostSurrogate,
    LightGBMSurrogate,
    RandomForestSurrogate,
    AdaptiveMLPSurrogate,
    PolynomialRSMSurrogate,
)


@pytest.fixture(scope="module")
def bridge_dataset():
    config = load_topology_config("configs/bridge_amplifier.yaml")
    # Generate 350 samples for clean surrogate learning
    return CompliantDataset.from_synthetic(config, n_samples=350, noise_std=0.005, seed=42)


def test_model_fit_predict_shape(bridge_dataset):
    """Verify that all models accept (N, D_in) and predict exact (N_test, D_out) arrays."""
    X_train, Y_train = bridge_dataset.get_train_data(scaled=True)
    X_test, Y_test = bridge_dataset.get_test_data(scaled=True)

    D_in = bridge_dataset.config.D_in
    D_out = bridge_dataset.config.D_out
    N_test = len(X_test)

    models = [
        PolynomialRSMSurrogate(),
        RandomForestSurrogate(n_estimators=30, max_depth=6),
        XGBoostSurrogate(n_estimators=50, max_depth=3),
        LightGBMSurrogate(n_estimators=50, max_depth=4),
        AdaptiveMLPSurrogate(hidden_dim=32, epochs=30),
        MultiOutputGPR(n_restarts_optimizer=0),
    ]

    for model in models:
        assert not model.is_fitted
        model.fit(X_train, Y_train)
        assert model.is_fitted
        assert model.D_in == D_in
        assert model.D_out == D_out

        preds = model.predict(X_test)
        assert isinstance(preds, np.ndarray)
        assert preds.shape == (N_test, D_out), f"{model.name} output shape mismatch."


def test_gpr_uncertainty_quantification(bridge_dataset):
    """Verify GPR posterior uncertainty standard deviation estimation."""
    X_train, Y_train = bridge_dataset.get_train_data(scaled=True)
    X_test, _ = bridge_dataset.get_test_data(scaled=True)

    gpr = MultiOutputGPR(n_restarts_optimizer=0)
    gpr.fit(X_train, Y_train)

    mean_pred, std_pred = gpr.predict_with_uncertainty(X_test)

    assert std_pred is not None
    assert std_pred.shape == mean_pred.shape
    assert (std_pred > 0.0).all(), "Uncertainty sigma must be strictly positive."


def test_model_r2_score(bridge_dataset):
    """Verify that surrogate models meet the required R2 accuracy floor (R2 >= 0.90)."""
    X_train, Y_train = bridge_dataset.get_train_data(scaled=True)
    X_test, Y_test = bridge_dataset.get_test_data(scaled=True)

    # Test top gradient boosted surrogate model
    xgb = XGBoostSurrogate(n_estimators=100, max_depth=4, learning_rate=0.08)
    xgb.fit(X_train, Y_train)
    r2_xgb = xgb.score_r2(X_test, Y_test)
    assert r2_xgb >= 0.90, f"XGBoost R2 score ({r2_xgb:.4f}) must be >= 0.90"

    # Test Polynomial RSM baseline
    rsm = PolynomialRSMSurrogate(degree=2)
    rsm.fit(X_train, Y_train)
    r2_rsm = rsm.score_r2(X_test, Y_test)
    assert r2_rsm >= 0.90, f"Polynomial RSM R2 score ({r2_rsm:.4f}) must be >= 0.90"

    # Test GPR
    gpr = MultiOutputGPR(n_restarts_optimizer=1)
    gpr.fit(X_train, Y_train)
    r2_gpr = gpr.score_r2(X_test, Y_test)
    assert r2_gpr >= 0.90, f"GPR R2 score ({r2_gpr:.4f}) must be >= 0.90"


def test_model_serialization(tmp_path, bridge_dataset):
    """Verify saving and restoring model artifacts to disk."""
    X_train, Y_train = bridge_dataset.get_train_data(scaled=True)
    X_test, _ = bridge_dataset.get_test_data(scaled=True)

    model = XGBoostSurrogate(n_estimators=30)
    model.fit(X_train, Y_train)
    orig_preds = model.predict(X_test)

    save_path = tmp_path / "test_xgb.pkl"
    model.save(save_path)
    assert save_path.exists()

    loaded_model = XGBoostSurrogate.load(save_path)
    assert loaded_model.is_fitted
    loaded_preds = loaded_model.predict(X_test)

    np.testing.assert_allclose(orig_preds, loaded_preds, atol=1e-6)
