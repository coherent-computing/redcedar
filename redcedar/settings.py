"""Settings loading from dict, JSON, or TOML files."""

import json
import os


def load_settings(source):
    """Load settings overrides from a dict, JSON file, or TOML file.

    Settings are flattened into a single dict of key-value pairs that
    get merged into server defaults by build_settings().

    Args:
        source: One of:
            - dict: used directly
            - str ending in .json: parsed as JSON
            - str ending in .toml: parsed as TOML (requires Python 3.11+ or tomli)

    Returns:
        Flat dict of setting overrides.
    """
    if source is None:
        return {}

    if isinstance(source, dict):
        return source

    if isinstance(source, str):
        if not os.path.exists(source):
            raise FileNotFoundError(f"Settings file not found: {source}")

        if source.endswith(".json"):
            with open(source) as f:
                return json.load(f)

        if source.endswith(".toml"):
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib
                except ImportError:
                    raise ImportError(
                        "TOML support requires Python 3.11+ or 'pip install tomli'"
                    )
            with open(source, "rb") as f:
                raw = tomllib.load(f)
            # Flatten nested TOML sections into flat key-value pairs
            flat = {}
            for key, value in raw.items():
                if isinstance(value, dict):
                    flat.update(value)
                # Skip top-level metadata (name, description, author, created)
            return flat

    raise ValueError(f"Settings must be a dict, .json path, or .toml path. Got: {type(source)}")
