"""Optimization and Multi-Criteria Decision Making package for AutoCompliant-ML."""

from autocompliant.optimization.problem import CompliantMechanismProblem
from autocompliant.optimization.nsga2_solver import NSGA2Solver, OptimizationResult
from autocompliant.optimization.mcdm import topsis_select_best_tradeoff, calculate_extrapolation_risk

__all__ = [
    "CompliantMechanismProblem",
    "NSGA2Solver",
    "OptimizationResult",
    "topsis_select_best_tradeoff",
    "calculate_extrapolation_risk",
]
