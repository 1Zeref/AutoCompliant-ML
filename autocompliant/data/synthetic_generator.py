"""High-fidelity synthetic compliant mechanism analytical data generator."""

from typing import Optional, Tuple
import numpy as np
import pandas as pd

from autocompliant.config.schema import TopologyConfig


class SyntheticCompliantGenerator:
    """Analytical benchmark data generator based on compliant mechanism mechanics.

    Employs analytical flexure hinge compliance formulation (Paros & Weisbord)
    and bridge-type mechanical kinematic amplification principles.
    """

    def __init__(self, config: TopologyConfig, seed: Optional[int] = 42):
        """Initialize generator with topology configuration."""
        self.config = config
        self.rng = np.random.RandomState(seed)

    def generate(self, n_samples: int = 500, noise_std: float = 0.01) -> pd.DataFrame:
        """Generate synthetic dataset matching the topology's input/output schema.

        Args:
            n_samples: Number of sample configurations to generate.
            noise_std: Standard deviation of relative Gaussian measurement noise.

        Returns:
            pd.DataFrame containing input feature columns and target output columns.
        """
        lower_bounds, upper_bounds = self.config.bounds
        D_in = self.config.D_in

        # Sample uniform design space across parameter bounds
        X = self.rng.uniform(lower_bounds, upper_bounds, size=(n_samples, D_in))

        if self.config.topology.name == "Bridge_Type_Amplifier" and D_in == 5:
            # Inputs: t, w, l, theta, r
            t = X[:, 0]
            w = X[:, 1]
            l = X[:, 2]
            theta = X[:, 3]
            r = X[:, 4]

            theta_rad = np.radians(theta)

            # 1. Output Displacement F2 (um)
            # Theoretical kinematic amplification: A_amp ~ 1 / tan(theta) with elastic compliance loss
            compliance_loss = 1.0 - (0.05 * (t / 1.0) ** 2.0 / (l / 25.0))
            compliance_loss = np.clip(compliance_loss, 0.4, 0.98)
            amp_ratio = (1.0 / np.tan(theta_rad)) * compliance_loss
            input_displacement = 10.0  # standard 10 um piezo actuator input
            F2 = amp_ratio * input_displacement

            # 2. Safety Factor F1 (Static factor S = sigma_yield / sigma_vonMises)
            # Stress concentration Kt at circular flexure hinge
            Kt = 1.0 + 0.85 * np.sqrt(t / r)
            nominal_stress = 320.0 * (t / 0.8) / ((l / 25.0) ** 1.8 * np.sin(theta_rad) + 0.05)
            von_mises = Kt * nominal_stress
            sigma_yield = 880.0  # Ti-6Al-4V yield strength (MPa)
            F1 = sigma_yield / (von_mises + 1e-5)
            F1 = np.clip(F1, 0.5, 6.0)

            # 3. First Resonant Frequency f (Hz)
            # f1 ~ sqrt(K_eff / M_eff), stiffness scales with t^1.5, inversely with l^1.2
            stiffness_term = (t / 0.8) ** 1.5 * np.sqrt(w / 10.0)
            mass_term = (l / 25.0) ** 1.2
            f = 420.0 + 1350.0 * (stiffness_term / mass_term) * (1.0 + 0.1 * np.cos(theta_rad))

            Y = np.column_stack([F1, F2, f])
        else:
            # Generalized non-linear benchmark formulation for arbitrary topologies
            # Ensures positive physical values, smooth non-linear interaction, and high learnability
            Y_list = []
            for j in range(self.config.D_out):
                center = (lower_bounds + upper_bounds) / 2.0
                span = (upper_bounds - lower_bounds) / 2.0
                X_norm = (X - center) / span

                # Non-linear combination of quadratic, sinusoidal and cross terms
                linear_part = np.sum(X_norm * (0.8 / (j + 1)), axis=1)
                quad_part = 0.5 * np.sum(X_norm**2, axis=1)
                cross_part = 0.3 * (X_norm[:, 0] * X_norm[:, -1])
                target = 10.0 * (j + 1) + 5.0 * (linear_part + quad_part + cross_part)
                Y_list.append(np.abs(target) + 1.0)
            Y = np.column_stack(Y_list)

        # Add slight realistic measurement noise
        if noise_std > 0:
            noise = self.rng.normal(0, noise_std, size=Y.shape)
            Y = Y * (1.0 + noise)

        # Assemble into DataFrame with configured column names
        data_dict = {}
        for idx, name in enumerate(self.config.input_names):
            data_dict[name] = X[:, idx]
        for idx, name in enumerate(self.config.output_names):
            data_dict[name] = Y[:, idx]

        return pd.DataFrame(data_dict)
