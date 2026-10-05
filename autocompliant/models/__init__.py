"""Multi-Output Surrogate Model Zoo for AutoCompliant-ML."""

from autocompliant.models.base import BaseSurrogateModel
from autocompliant.models.gpr_model import MultiOutputGPR
from autocompliant.models.gbm_model import XGBoostSurrogate, LightGBMSurrogate, RandomForestSurrogate
from autocompliant.models.dnn_model import AdaptiveMLPSurrogate
from autocompliant.models.baseline_models import PolynomialRSMSurrogate

__all__ = [
    "BaseSurrogateModel",
    "MultiOutputGPR",
    "XGBoostSurrogate",
    "LightGBMSurrogate",
    "RandomForestSurrogate",
    "AdaptiveMLPSurrogate",
    "PolynomialRSMSurrogate",
]
