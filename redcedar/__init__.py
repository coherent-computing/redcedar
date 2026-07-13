"""Red Cedar — Python client for the Red Cedar quantum ML server."""

__version__ = "0.1.0"

from .client import connect, RedCedarClient

__all__ = ["connect", "RedCedarClient", "__version__"]
