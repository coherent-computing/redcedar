"""Local mode — the Red Cedar core called directly, in this Python process, for development.

connect(local=True) imports redcedar_core (installed with `pip install -e .` in a
red-cedar folder). Each SDK call then calls the matching redcedar_core function, the
same function the server runs for that job, in this thread: no server and no HTTP, so
a debugger steps from the SDK call straight into the Red Cedar code. Each SDK method
has the two branches side by side: `if self._client.core:` calls the core, otherwise
the request goes to the server. Needs the Red Cedar dependencies (Qiskit or CUDA-Q,
numpy, scikit-learn) in this environment.
"""

import os
import sys


def import_core(core_path=None):
    """Import redcedar_core: installed (pip install -e), or from the red-cedar folder
    given here or in REDCEDAR_CORE_PATH."""
    core_path = core_path or os.environ.get("REDCEDAR_CORE_PATH")
    if core_path:
        core_path = os.path.abspath(core_path)
        if core_path not in sys.path:
            sys.path.insert(0, core_path)
    try:
        import redcedar_core
    except ImportError as e:
        raise ImportError("Local mode needs redcedar_core: run `pip install -e .` in the "
                          f"red-cedar folder (or pass local='path/to/red-cedar'): {e}") from e
    return redcedar_core
