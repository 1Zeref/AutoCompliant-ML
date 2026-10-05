"""Pymoo Problem formulation for multi-objective compliant mechanism optimization."""

from typing import List, Optional, Tuple
import numpy as np
from pymoo.core.problem import Problem

from autocompliant.config.schema import TopologyConfig
from autocompliant.data.preprocessor import AdaptivePreprocessor
from autocompliant.models.base import BaseSurrogateModel


class CompliantMechanismProblem(Problem):
    """Adaptive Multi-Objective Optimization Problem evaluated via surrogate models.

    Directly bridges the Config Schema, Surrogate Model Zoo, and Pymoo NSGA-II solver.
    """

    def __init__(
        self,
        config: TopologyConfig,
        surrogate_model: BaseSurrogateModel,
        preprocessor: AdaptivePreprocessor,
        use_uncertainty_penalty: bool = False,
        beta: float = 1.0,
    ):
        self.config = config
        self.surrogate_model = surrogate_model
        self.preprocessor = preprocessor
        self.use_uncertainty_penalty = use_uncertainty_penalty
        self.beta = float(beta)

        lower_bounds, upper_bounds = config.bounds
        n_var = config.D_in

        # Identify objectives (default: maximize F2 and maximize f)
        self.obj_indices: List[Tuple[int, str]] = []
        for idx, out in enumerate(config.outputs):
            if out.symbol in ["F2", "f"] or out.name in ["output_displacement", "resonant_frequency"]:
                self.obj_indices.append((idx, out.objective))

        # Fallback if specific symbols not present: optimize all non-constrained or first 2
        if not self.obj_indices:
            for idx, out in enumerate(config.outputs):
                if out.constraint_min is None and out.constraint_max is None:
                    self.obj_indices.append((idx, out.objective))
        if not self.obj_indices:
            self.obj_indices = [(i, config.outputs[i].objective) for i in range(min(2, config.D_out))]

        n_obj = len(self.obj_indices)

        # Identify inequality constraints: g(x) <= 0
        self.constraints: List[Tuple[int, str, float]] = []
        for idx, out in enumerate(config.outputs):
            if out.constraint_min is not None:
                self.constraints.append((idx, "min", float(out.constraint_min)))
            if out.constraint_max is not None:
                self.constraints.append((idx, "max", float(out.constraint_max)))

        n_constr = len(self.constraints)

        super().__init__(
            n_var=n_var,
            n_obj=n_obj,
            n_ieq_constr=n_constr,
            xl=lower_bounds,
            xu=upper_bounds,
        )

    def _evaluate(self, X: np.ndarray, out: dict, *args, **kwargs) -> None:
        """Batch evaluate the entire population simultaneously using surrogate inference."""
        # 1. Transform inputs into surrogate model feature space
        X_scaled = self.preprocessor.transform_x(X)

        # 2. Batch inference with optional uncertainty quantification
        if self.use_uncertainty_penalty:
            Y_scaled, std_scaled = self.surrogate_model.predict_with_uncertainty(X_scaled)
        else:
            Y_scaled = self.surrogate_model.predict(X_scaled)
            std_scaled = None

        # 3. Inverse transform mean into physical mechanical units
        Y = self.preprocessor.inverse_transform_y(Y_scaled)

        # Compute physical uncertainty std if available
        # Note: scale factor can be approximated using preprocessor scale_
        std_physical = None
        if std_scaled is not None and hasattr(self.preprocessor.scaler_y, "scale_"):
            scales = getattr(self.preprocessor.scaler_y, "scale_", None)
            if scales is not None:
                std_physical = std_scaled * scales
            else:
                std_physical = std_scaled
        elif std_scaled is not None:
            std_physical = std_scaled

        # 4. Formulate objective functions (pymoo minimizes all objectives)
        # To maximize F_j: minimize - (mu_j - beta * sigma_j)
        # To minimize F_j: minimize (mu_j + beta * sigma_j)
        F_list = []
        for idx, direction in self.obj_indices:
            values = Y[:, idx]
            penalty = (self.beta * std_physical[:, idx]) if (std_physical is not None and self.use_uncertainty_penalty) else 0.0

            if direction == "maximize":
                # Robust objective: maximize (values - penalty) => minimize -(values - penalty)
                F_list.append(-(values - penalty))
            else:
                # Robust objective: minimize (values + penalty) => minimize (values + penalty)
                F_list.append(values + penalty)
        out["F"] = np.column_stack(F_list)

        # 5. Formulate inequality constraints g(x) <= 0
        if self.n_ieq_constr > 0:
            G_list = []
            for idx, bound_type, threshold in self.constraints:
                values = Y[:, idx]
                sigma = std_physical[:, idx] if (std_physical is not None and self.use_uncertainty_penalty) else 0.0

                if bound_type == "min":
                    # Conservative constraint: (values - beta * sigma) >= threshold
                    # <=> threshold - (values - beta * sigma) <= 0
                    g = threshold - (values - self.beta * sigma)
                else:
                    # Conservative constraint: (values + beta * sigma) <= threshold
                    # <=> (values + beta * sigma) - threshold <= 0
                    g = (values + self.beta * sigma) - threshold
                G_list.append(g)
            out["G"] = np.column_stack(G_list)

        # Attach physical responses for downstream Pareto analysis
        out["Y_physical"] = Y

