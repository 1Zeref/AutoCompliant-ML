"""Comprehensive unit and integration tests for precision & robustness enhancements:
1. Outlier detection and cleaning (filter_outliers).
2. WeightedEnsembleSurrogate model with uncertainty quantification.
3. Uncertainty-aware CompliantMechanismProblem formulation (LCB penalty).
4. Extrapolation risk metric in TOPSIS knee-point selection.
5. End-to-end integration via FastAPI wizard endpoints.
"""

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from autocompliant.config.loader import load_topology_config
from autocompliant.data.preprocessor import AdaptivePreprocessor, filter_outliers
from autocompliant.data.synthetic_generator import SyntheticCompliantGenerator
from autocompliant.data.dataset import CompliantDataset
from autocompliant.models import (
    XGBoostSurrogate,
    LightGBMSurrogate,
    RandomForestSurrogate,
    WeightedEnsembleSurrogate,
)
from autocompliant.optimization.problem import CompliantMechanismProblem
from autocompliant.optimization.nsga2_solver import NSGA2Solver
from autocompliant.optimization.mcdm import calculate_extrapolation_risk, topsis_select_best_tradeoff
from autocompliant.web.app import app


client = TestClient(app)


def test_filter_outliers_iqr_and_zscore():
    """Test outlier detection removes extreme spikes and leaves regular data intact."""
    np.random.seed(42)
    # 100 normal points + 2 extreme anomalies
    data = np.random.normal(loc=10.0, scale=1.0, size=(100, 2))
    df = pd.DataFrame(data, columns=["val1", "val2"])

    # Inject extreme FEA divergence spikes
    df.loc[10, "val1"] = 1000.0  # huge positive spike
    df.loc[25, "val2"] = -500.0  # huge negative spike

    cleaned_iqr, mask_iqr = filter_outliers(df, columns=["val1", "val2"], method="iqr", factor=1.5)
    assert mask_iqr[10] is True or mask_iqr[10] == 1
    assert mask_iqr[25] is True or mask_iqr[25] == 1
    assert len(cleaned_iqr) < len(df)
    assert cleaned_iqr["val1"].max() < 100.0

    cleaned_z, mask_z = filter_outliers(df, columns=["val1", "val2"], method="zscore", factor=3.0)
    assert mask_z[10] is True or mask_z[10] == 1
    assert mask_z[25] is True or mask_z[25] == 1


def test_weighted_ensemble_surrogate_fit_predict_uncertainty():
    """Verify WeightedEnsembleSurrogate fits, predicts, and quantifies epistemic uncertainty."""
    np.random.seed(42)
    X = np.random.uniform(0.5, 5.0, size=(60, 4))
    Y = np.column_stack([
        2.0 * X[:, 0] + 0.5 * X[:, 1],
        10.0 / (X[:, 2] + 0.1) + X[:, 3],
    ])

    m1 = RandomForestSurrogate(n_estimators=15, max_depth=4, random_state=42)
    m2 = XGBoostSurrogate(n_estimators=20, max_depth=3, random_state=42)
    m3 = LightGBMSurrogate(n_estimators=20, max_depth=3, random_state=42)

    # 1. Fit individual models
    for m in [m1, m2, m3]:
        m.fit(X, Y)

    scores = {
        m1.name: float(m1.score_r2(X, Y)),
        m2.name: float(m2.score_r2(X, Y)),
        m3.name: float(m3.score_r2(X, Y)),
    }

    # 2. Build ensemble from fitted models
    ensemble = WeightedEnsembleSurrogate.from_fitted_models([m1, m2, m3], scores=scores)
    assert ensemble.is_fitted is True
    assert ensemble.weights is not None
    assert np.isclose(np.sum(ensemble.weights), 1.0)

    # 3. Predict & uncertainty quantification
    X_test = np.random.uniform(0.5, 5.0, size=(10, 4))
    pred = ensemble.predict(X_test)
    assert pred.shape == (10, 2)

    mean_pred, unc_std = ensemble.predict_with_uncertainty(X_test)
    assert np.allclose(pred, mean_pred)
    assert unc_std.shape == (10, 2)
    assert np.all(unc_std >= 0.0)


def test_uncertainty_aware_problem_penalty():
    """Verify CompliantMechanismProblem penalizes objectives and constraints under uncertainty."""
    cfg = load_topology_config("configs/bridge_amplifier.yaml")
    gen = SyntheticCompliantGenerator(cfg, seed=42)
    df = gen.generate(n_samples=50)

    dataset = CompliantDataset.from_dataframe(df, cfg, random_state=42)
    X_tr, Y_tr = dataset.get_train_data(scaled=True)

    m1 = RandomForestSurrogate(n_estimators=10, random_state=42).fit(X_tr, Y_tr)
    m2 = XGBoostSurrogate(n_estimators=10, random_state=42).fit(X_tr, Y_tr)
    ensemble = WeightedEnsembleSurrogate.from_fitted_models(
        [m1, m2], scores={m1.name: 0.9, m2.name: 0.9}
    )

    # Problem without penalty
    prob_nominal = CompliantMechanismProblem(
        config=cfg,
        surrogate_model=ensemble,
        preprocessor=dataset.preprocessor,
        use_uncertainty_penalty=False,
    )

    # Problem with uncertainty penalty beta=2.0
    prob_robust = CompliantMechanismProblem(
        config=cfg,
        surrogate_model=ensemble,
        preprocessor=dataset.preprocessor,
        use_uncertainty_penalty=True,
        beta=2.0,
    )

    X_pop = np.tile(np.mean(cfg.bounds, axis=0), (5, 1))

    out_nominal = {}
    prob_nominal._evaluate(X_pop, out_nominal)

    out_robust = {}
    prob_robust._evaluate(X_pop, out_robust)

    # In pymoo, objectives are minimized (-F_j for maximize).
    # With penalty, robust objective to maximize is mu - beta*sigma, so pymoo objective is -(mu - beta*sigma) = -mu + beta*sigma.
    # Therefore out_robust["F"] should be >= out_nominal["F"]
    assert np.all(out_robust["F"] >= out_nominal["F"] - 1e-6)


def test_extrapolation_risk_metric():
    """Verify calculate_extrapolation_risk properly flags near vs out-of-distribution points."""
    np.random.seed(42)
    train_x = np.random.normal(loc=5.0, scale=1.0, size=(100, 3))

    # Point inside distribution
    inside_pt = np.array([5.1, 4.9, 5.0])
    risk_inside = calculate_extrapolation_risk(inside_pt, train_x)
    assert risk_inside["confidence_level"] == "High Confidence"
    assert risk_inside["confidence_percentage"] > 70.0
    assert risk_inside["risk_color"] == "emerald"

    # Far point outside distribution
    outside_pt = np.array([15.0, 20.0, -10.0])
    risk_outside = calculate_extrapolation_risk(outside_pt, train_x)
    assert risk_outside["confidence_level"] == "High Extrapolation Risk"
    assert risk_outside["confidence_percentage"] < 30.0
    assert risk_outside["risk_color"] == "rose"


def test_api_robustness_flow_with_uncertainty():
    """Test full API stepper with uncertainty penalty enabled in Step 3 and risk badge in Step 4."""
    # Step 1: Init data
    r1 = client.post(
        "/api/wizard/step1-data",
        data={"topology_name": "bridge_amplifier", "use_synthetic": True, "n_synthetic_samples": 40},
    )
    assert r1.status_code == 200
    sess_id = r1.json()["session_id"]

    # Step 2: Train
    r2 = client.post(
        "/api/wizard/step2-train",
        json={"session_id": sess_id, "cv_folds": 2, "scaler_type": "standard"},
    )
    assert r2.status_code == 200
    lboard = r2.json()["leaderboard"]
    # Check that WeightedEnsemble is part of candidates or leaderboard
    model_names = [m["model"] for m in lboard]
    assert "WeightedEnsemble" in model_names or len(model_names) >= 4

    # Step 3: Run optimization with use_uncertainty_penalty=True
    r3 = client.post(
        "/api/wizard/step3-optimize",
        json={
            "session_id": sess_id,
            "pop_size": 20,
            "generations": 10,
            "use_uncertainty_penalty": True,
            "beta": 1.5,
        },
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "success"
    assert r3.json()["pareto_summary"]["num_pareto_points"] > 0

    # Step 4: Verify extrapolation_risk present in results
    r4 = client.get(f"/api/wizard/step4-results?session_id={sess_id}")
    assert r4.status_code == 200
    res = r4.json()
    assert "extrapolation_risk" in res
    assert res["extrapolation_risk"] is not None
    assert "confidence_percentage" in res["extrapolation_risk"]
    assert "confidence_level_vi" in res["extrapolation_risk"]
