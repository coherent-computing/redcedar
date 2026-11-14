"""The SDK version in the documentation, read from pyproject.toml so it is set in one place:
in the footer of every page, and in page text that writes {{ sdk_version }} (2.0.0) or
{{ server_version }} (2.0, the server release the SDK goes with)."""
import pathlib
import re

_PYPROJECT = pathlib.Path(__file__).resolve().parents[2] / "pyproject.toml"
SDK_VERSION = re.search(r'^version\s*=\s*"([^"]+)"', _PYPROJECT.read_text(), re.MULTILINE).group(1)
SERVER_VERSION = ".".join(SDK_VERSION.split(".")[:2])


def on_config(config):
    config.copyright = f"Red Cedar SDK {SDK_VERSION} documentation"
    return config


def on_page_markdown(markdown, **kwargs):
    return markdown.replace("{{ sdk_version }}", SDK_VERSION).replace("{{ server_version }}", SERVER_VERSION)
