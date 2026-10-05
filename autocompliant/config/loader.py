"""Loader utilities for parsing and instantiating topology YAML configurations."""

from pathlib import Path
from typing import Union
import yaml

from autocompliant.config.schema import TopologyConfig


def load_topology_config(config_path: Union[str, Path]) -> TopologyConfig:
    """Load, parse, and validate a topology YAML configuration file.

    Args:
        config_path: File path to the YAML configuration.

    Returns:
        TopologyConfig: Fully validated configuration object.

    Raises:
        FileNotFoundError: If the specified configuration file does not exist.
        ValueError: If YAML parsing fails or configuration schema validation fails.
    """
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found at: {path.resolve()}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML parsing error in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML root structure in {path}: Expected a mapping/dictionary.")

    return TopologyConfig.model_validate(data)
