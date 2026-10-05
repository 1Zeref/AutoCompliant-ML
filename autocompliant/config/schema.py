"""Schema validation for compliant mechanism topologies and pipeline configuration."""

from typing import List, Optional, Literal, Tuple
import numpy as np
from pydantic import BaseModel, Field, model_validator


class InputParam(BaseModel):
    """Specification for a geometric design input variable."""
    name: str = Field(..., description="Full descriptive name of the parameter")
    symbol: str = Field(..., description="Short mathematical symbol, e.g., 't', 'w', 'l'")
    min: float = Field(..., description="Lower bound")
    max: float = Field(..., description="Upper bound")
    unit: str = Field(default="mm", description="Measurement unit")
    description: Optional[str] = None

    @model_validator(mode="after")
    def validate_bounds(self) -> "InputParam":
        if self.min >= self.max:
            raise ValueError(f"Lower bound 'min' ({self.min}) must be strictly less than 'max' ({self.max}) for input '{self.name}'.")
        return self


class OutputParam(BaseModel):
    """Specification for a mechanical response output characteristic."""
    name: str = Field(..., description="Full descriptive name of the output")
    symbol: str = Field(..., description="Short mathematical symbol, e.g., 'F1', 'F2', 'f'")
    objective: Literal["maximize", "minimize"] = Field(..., description="Optimization objective direction")
    unit: str = Field(default="", description="Measurement unit, e.g., 'ratio', 'um', 'Hz'")
    constraint_min: Optional[float] = Field(default=None, description="Lower inequality constraint threshold (Y >= min)")
    constraint_max: Optional[float] = Field(default=None, description="Upper inequality constraint threshold (Y <= max)")
    description: Optional[str] = None


class TopologyMeta(BaseModel):
    """Metadata identifying the mechanical topology."""
    name: str
    description: Optional[str] = None


class SurrogateConfig(BaseModel):
    """Hyperparameters and configuration for surrogate modeling."""
    test_size: float = Field(default=0.2, ge=0.05, le=0.5)
    random_state: int = Field(default=42)
    cv_folds: int = Field(default=5, ge=2)
    scaler: Literal["standard", "minmax", "robust"] = "standard"


class OptimizationConfig(BaseModel):
    """Genetic algorithm & NSGA-II solver settings."""
    algorithm: str = Field(default="NSGA-II")
    pop_size: int = Field(default=100, ge=10)
    n_generations: int = Field(default=100, ge=5)
    crossover_prob: float = Field(default=0.9, ge=0.0, le=1.0)
    mutation_prob: float = Field(default=0.1, ge=0.0, le=1.0)


class TopologyConfig(BaseModel):
    """Root configuration object representing an entire Compliant Mechanism problem."""
    topology: TopologyMeta
    inputs: List[InputParam] = Field(..., min_length=1)
    outputs: List[OutputParam] = Field(..., min_length=1)
    surrogate: SurrogateConfig = Field(default_factory=SurrogateConfig)
    optimization: OptimizationConfig = Field(default_factory=OptimizationConfig)

    @property
    def D_in(self) -> int:
        """Dimensionality of the geometric input space."""
        return len(self.inputs)

    @property
    def D_out(self) -> int:
        """Dimensionality of the mechanical output space."""
        return len(self.outputs)

    @property
    def input_names(self) -> List[str]:
        """List of input feature column names."""
        return [inp.name for inp in self.inputs]

    @property
    def input_symbols(self) -> List[str]:
        """List of input symbols."""
        return [inp.symbol for inp in self.inputs]

    @property
    def output_names(self) -> List[str]:
        """List of output target column names."""
        return [out.name for out in self.outputs]

    @property
    def output_symbols(self) -> List[str]:
        """List of output symbols."""
        return [out.symbol for out in self.outputs]

    @property
    def bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """Returns (lower_bounds, upper_bounds) as numpy arrays of shape (D_in,)."""
        lower = np.array([inp.min for inp in self.inputs], dtype=np.float64)
        upper = np.array([inp.max for inp in self.inputs], dtype=np.float64)
        return lower, upper
