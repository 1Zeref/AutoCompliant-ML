"""Multi-Objective Evolutionary Algorithm (NSGA-II) solver for compliant mechanisms."""

import time
from typing import Optional
import numpy as np
import pandas as pd
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.optimize import minimize

from autocompliant.optimization.problem import CompliantMechanismProblem


class OptimizationResult:
    """Encapsulates the Pareto optimal front and design decision matrix."""

    def __init__(
        self,
        X_pareto: np.ndarray,
        F_pareto: np.ndarray,
        Y_pareto: np.ndarray,
        problem: CompliantMechanismProblem,
        runtime_sec: float,
        n_gen: int,
    ):
        self.X_pareto = X_pareto
        self.F_pareto = F_pareto
        self.Y_pareto = Y_pareto
        self.problem = problem
        self.config = problem.config
        self.runtime_sec = runtime_sec
        self.n_gen = n_gen

    @property
    def n_pareto(self) -> int:
        return len(self.X_pareto) if self.X_pareto is not None else 0

    def to_dataframe(self) -> pd.DataFrame:
        """Export Pareto solutions into a pandas DataFrame."""
        if self.n_pareto == 0:
            return pd.DataFrame()

        data = {}
        for idx, name in enumerate(self.config.input_names):
            data[name] = self.X_pareto[:, idx]
        for idx, name in enumerate(self.config.output_names):
            data[name] = self.Y_pareto[:, idx]

        return pd.DataFrame(data)

    def to_csv(self, path: str) -> None:
        """Save Pareto set to CSV."""
        df = self.to_dataframe()
        df.to_csv(path, index=False)


class NSGA2Solver:
    """NSGA-II Evolutionary Algorithm Solver with simulated binary crossover & polynomial mutation."""

    def __init__(
        self,
        pop_size: int = 100,
        n_generations: int = 100,
        crossover_prob: float = 0.9,
        mutation_prob: float = 0.1,
        seed: int = 42,
    ):
        self.pop_size = pop_size
        self.n_generations = n_generations
        self.crossover_prob = crossover_prob
        self.mutation_prob = mutation_prob
        self.seed = seed

    def solve(self, problem: CompliantMechanismProblem) -> OptimizationResult:
        """Run evolutionary multi-objective optimization."""
        algorithm = NSGA2(
            pop_size=self.pop_size,
            sampling=FloatRandomSampling(),
            crossover=SBX(prob=self.crossover_prob, eta=15),
            mutation=PM(prob=self.mutation_prob, eta=20),
            eliminate_duplicates=True,
        )

        t0 = time.perf_counter()
        res = minimize(
            problem,
            algorithm,
            ("n_gen", self.n_generations),
            seed=self.seed,
            verbose=False,
        )
        runtime = time.perf_counter() - t0

        if res.X is None or len(res.X) == 0:
            if hasattr(res, "pop") and res.pop is not None and len(res.pop) > 0:
                X_pop = res.pop.get("X")
                F_pop = res.pop.get("F")
                if X_pop is not None and len(X_pop) > 0:
                    res.X = np.atleast_2d(X_pop[: min(10, len(X_pop))])
                    res.F = np.atleast_2d(F_pop[: min(10, len(F_pop))])

        if res.X is None or len(res.X) == 0:
            return OptimizationResult(
                X_pareto=np.empty((0, problem.n_var)),
                F_pareto=np.empty((0, problem.n_obj)),
                Y_pareto=np.empty((0, problem.config.D_out)),
                problem=problem,
                runtime_sec=runtime,
                n_gen=self.n_generations,
            )

        X_pareto = np.atleast_2d(res.X)
        F_pareto = np.atleast_2d(res.F)

        # Compute full physical responses for all Pareto solutions
        X_scaled = problem.preprocessor.transform_x(X_pareto)
        Y_scaled = problem.surrogate_model.predict(X_scaled)
        Y_pareto = problem.preprocessor.inverse_transform_y(Y_scaled)

        return OptimizationResult(
            X_pareto=X_pareto,
            F_pareto=F_pareto,
            Y_pareto=Y_pareto,
            problem=problem,
            runtime_sec=runtime,
            n_gen=self.n_generations,
        )
