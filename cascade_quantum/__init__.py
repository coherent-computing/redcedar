"""Cascade Quantum — Python client for the Cascade Quantum ML server."""

__version__ = "0.1.0"

from .client import connect, CascadeClient

__all__ = ["connect", "CascadeClient", "__version__"]
