"""Local mode — the Red Cedar server inside this Python process, for development.

connect(local=True) starts the server from a red-cedar source folder in a
background thread, on a free port on 127.0.0.1, and connects to it. The SDK then
works exactly as with a separate server, and a debugger attached to this process
stops at breakpoints in the Red Cedar code. Needs the Red Cedar dependencies
(Qiskit or CUDA-Q, numpy, scikit-learn, FastAPI, uvicorn) in this environment.
"""

import os
import secrets
import socket
import sys
import threading
import time

_local = None   # (url, api_key) once started; one local server per process


def start_local_server(core_path=None):
    """Start the server once per process and return its (url, api_key)."""
    global _local
    if _local:
        return _local

    core_path = core_path or os.environ.get("REDCEDAR_CORE_PATH")
    if core_path:
        core_path = os.path.abspath(core_path)
        if not os.path.isfile(os.path.join(core_path, "server", "main.py")):
            raise FileNotFoundError(f"No Red Cedar server found in {core_path}")
        if core_path not in sys.path:
            sys.path.insert(0, core_path)

    # The server needs a key; a local one is made up for this process.
    os.environ.setdefault("BACKEND_API_KEY", secrets.token_urlsafe(24))
    api_key = os.environ["BACKEND_API_KEY"]

    try:
        import uvicorn
        from server.main import app
    except ImportError as e:
        raise ImportError("Local mode needs the red-cedar folder (local='path/to/red-cedar' or "
                          f"REDCEDAR_CORE_PATH) and its dependencies: {e}") from e

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    server.install_signal_handlers = lambda: None   # not the main thread
    thread = threading.Thread(target=server.run, daemon=True, name="redcedar-local-server")
    thread.start()

    deadline = time.time() + 60
    while not server.started:
        if not thread.is_alive() or time.time() > deadline:
            raise RuntimeError("The local Red Cedar server did not start")
        time.sleep(0.1)

    _local = (f"http://127.0.0.1:{port}", api_key)
    return _local
