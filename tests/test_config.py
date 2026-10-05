"""Unit tests for config schema and loader in AutoCompliant-ML (Loop 1 Gate)."""

import pytest
import numpy as np
from pathlib import Path
from pydantic import ValidationError

from autocompliant.config.loader import load_topology_config
from autocompliant.config.schema import TopologyConfig, InputParam, OutputParam, TopologyMeta


def test_load_bridge_amplifier_config():
    """Verify loading and properties of the default bridge amplifier topology."""
    config_path = Path("configs/bridge_amplifier.yaml")
    assert config_path.exists(), "configs/bridge_amplifier.yaml must exist."

    config = load_topology_config(config_path)

    # Dimensionality assertions
    assert config.D_in == 5, f"Expected D_in=5, got {config.D_in}"
    assert config.D_out == 3, f"Expected D_out=3, got {config.D_out}"

    # Verify input names and symbols
    assert "hinge_thickness_t" in config.input_names
    assert config.input_symbols == ["t", "w", "l", "theta", "r"]

    # Verify output names and symbols
    assert "safety_factor" in config.output_names
    assert config.output_symbols == ["F1", "F2", "f"]

    # Verify bounds
    lower, upper = config.bounds
    assert isinstance(lower, np.ndarray)
    assert isinstance(upper, np.ndarray)
    assert lower.shape == (5,)
    assert upper.shape == (5,)
    assert np.all(lower < upper), "All lower bounds must be strictly less than upper bounds."

    # Verify constraints
    f1_param = next(out for out in config.outputs if out.symbol == "F1")
    assert f1_param.constraint_min == 1.5, "F1 safety factor constraint_min should be 1.5."


def test_load_scott_russell_config():
    """Verify loading of alternative topology (Scott-Russell)."""
    config_path = Path("configs/scott_russell.yaml")
    assert config_path.exists(), "configs/scott_russell.yaml must exist."

    config = load_topology_config(config_path)
    assert config.D_in == 4
    assert config.D_out == 2
    assert config.topology.name == "Scott_Russell_Mechanism"


def test_invalid_bounds_raises_error():
    """Ensure validation fails if lower bound is >= upper bound."""
    with pytest.raises(ValidationError) as exc_info:
        InputParam(name="test_param", symbol="x", min=5.0, max=2.0)
    assert "strictly less than" in str(exc_info.value)


def test_missing_file_raises_error():
    """Ensure FileNotFoundError is raised for non-existent file path."""
    with pytest.raises(FileNotFoundError):
        load_topology_config("configs/non_existent_file.yaml")


def test_empty_inputs_raises_error():
    """Ensure topology requires at least one input and output."""
    with pytest.raises(ValidationError):
        TopologyConfig(
            topology=TopologyMeta(name="invalid"),
            inputs=[],
            outputs=[OutputParam(name="out", symbol="y", objective="maximize")]
        )
