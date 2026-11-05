"""Core client — HTTP requests, SSE streaming, authentication."""

import os
import sys
import json
import time
import requests

from .datasets import DatasetManager
from .analysis import AnalysisManager
from .training import TrainingManager
from .inference import InferenceManager
from .explainable import ExplainableManager


def connect(url=None, api_key=None, local=False):
    """Create a RedCedarClient connected to the server.

    Args:
        url: Server URL. Defaults to REDCEDAR_URL env var or http://127.0.0.1:8002
             (the port run_server uses).
        api_key: API key. Defaults to REDCEDAR_API_KEY env var.
        local: For development with the Red Cedar source. True calls the Red Cedar
               core (redcedar_core, installed with `pip install -e .` in a
               red-cedar folder) directly in this process, so a debugger steps into
               the Red Cedar code. Or the path of a red-cedar folder to use.

    Returns:
        RedCedarClient instance.
    """
    if local:
        from .local import import_core
        return RedCedarClient(None, None, core=import_core(None if local is True else local))
    url = url or os.environ.get("REDCEDAR_URL", "http://127.0.0.1:8002")
    api_key = api_key or os.environ.get("REDCEDAR_API_KEY", "")
    return RedCedarClient(url, api_key)


def _raise_for_status(resp):
    """Like resp.raise_for_status(), but the message includes the server's reason
    ('detail' from the Red Cedar server, 'error' from the gateway)."""
    if resp.ok:
        return
    try:
        body = resp.json()
        reason = body.get("detail") or body.get("error") if isinstance(body, dict) else None
    except ValueError:
        reason = None
    msg = f"{resp.status_code} {resp.reason}"
    if reason:
        msg += f": {reason}"
    raise requests.HTTPError(msg, response=resp)


class RedCedarClient:
    """Main client for interacting with the Red Cedar server."""

    def __init__(self, url, api_key, core=None):
        self.url = url.rstrip("/") if url else None
        self.api_key = api_key
        # Local mode (connect(local=True)): the redcedar_core module. Each SDK call then
        # calls its core function directly instead of sending a request to a server.
        self.core = core
        self._last_job_id = None
        self._server_version = None
        self.datasets = DatasetManager(self)
        self.analysis = AnalysisManager(self)
        self.training = TrainingManager(self)
        self.inference = InferenceManager(self)
        self.explainable = ExplainableManager(self)

    def _server(self, path=""):
        """The server URL. Local mode has no server: every SDK call has a direct one."""
        if self.url is None:
            raise NotImplementedError(f"Local mode has no direct call for {path}")
        return self.url

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["x-api-key"] = self.api_key
        return h

    def _local_call(self, fn, *args, **kwargs):
        """Call a redcedar_core function (local mode). Something not found, or a bad
        request, raises requests.HTTPError with the server's message, as in server mode."""
        try:
            return fn(*args, **kwargs)
        except FileNotFoundError as e:
            raise requests.HTTPError(f"404 Not Found: {e}") from e
        except ValueError as e:
            raise requests.HTTPError(f"400 Bad Request: {e}") from e

    def _run_local(self, fn, *args, verbose=False, on_progress=None, events=None, **kwargs):
        """Run a redcedar_core job function in this thread (local mode). Its events go
        to the same handler as a server job's: progress, log lines (verbose), and the
        other events into the events list. Returns the job's result."""
        out = sys.stdout   # while the job runs, print() goes to its log
        on_event = lambda e: self._handle_event(e, verbose, on_progress, events, out=out)  # noqa: E731
        return self._local_call(fn, *args, on_event=on_event, **kwargs)

    def _get(self, path):
        resp = requests.get(f"{self._server(path)}{path}", headers=self._headers())
        _raise_for_status(resp)
        return resp.json()

    def _post(self, path, body=None):
        resp = requests.post(
            f"{self._server(path)}{path}",
            headers=self._headers(),
            json=body or {},
        )
        _raise_for_status(resp)
        return resp.json()

    def _post_file(self, path, file_path):
        """Upload a file as multipart form data (field name 'file')."""
        headers = {"x-api-key": self.api_key} if self.api_key else {}
        with open(file_path, "rb") as f:
            resp = requests.post(
                f"{self._server(path)}{path}",
                headers=headers,
                files={"file": (os.path.basename(file_path), f)},
            )
        _raise_for_status(resp)
        return resp.json()

    def _open_stream(self, path, verbose=False):
        """Open a job's SSE stream. A queued job has no stream until it starts
        (the server answers 404), so wait for it to start."""
        while True:
            resp = requests.get(
                f"{self._server(path)}{path}",
                headers=self._headers(),
                stream=True,
            )
            if resp.status_code != 404:
                _raise_for_status(resp)
                return resp
            resp.close()

            # Also launches the next queued job on servers that only do so on a request.
            qs = self._get("/jobs/status")
            if not qs.get("total"):
                # Nothing queued or running, so the job is gone
                _raise_for_status(resp)
            if verbose:
                print("\r  Waiting in queue...", end="", flush=True)
            time.sleep(2)

    def _stream_sse(self, path, verbose=False):
        """Consume an SSE stream, yielding parsed events."""
        resp = self._open_stream(path, verbose)

        event_type = "message"
        data_buf = ""

        for line in resp.iter_lines(decode_unicode=True):
            if line is None:
                continue
            if line == "":
                # End of event
                if data_buf:
                    try:
                        parsed = json.loads(data_buf)
                        parsed["_event"] = event_type
                        yield parsed
                    except json.JSONDecodeError:
                        pass
                event_type = "message"
                data_buf = ""
            elif line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data_buf = line[6:]

    def _run_job(self, post_path, stream_path, body=None, verbose=False, on_progress=None,
                 events=None):
        """Start a job via POST, consume SSE until done. Returns summary.

        If events is a list, every other event the job sends (e.g. training
        datapoints and validation results) is appended to it."""
        result = self._post(post_path, body)
        job_id = result.get("job_id") or result.get("train_id")
        self._last_job_id = job_id
        if not job_id:
            return result

        # Trigger server-side queue cleanup and job launch before connecting
        # to SSE. Without this, stale queue entries from prior jobs block
        # new jobs from starting and training_state is never populated.
        try:
            self._get("/jobs/status")
        except Exception:
            pass

        for event in self._stream_sse(stream_path.format(job_id=job_id), verbose):
            self._handle_event(event, verbose, on_progress, events)
            etype = event.get("_event", event.get("type", ""))
            if etype == "done":
                return event.get("summary", event)
            elif etype == "error":
                raise RuntimeError(event.get("message", "Job failed"))
            elif etype == "stopped":
                raise RuntimeError(event.get("message", "Job stopped"))

        raise RuntimeError("SSE stream ended without done/error event")

    def _handle_event(self, event, verbose, on_progress, events, out=None):
        """Report one job event: progress and messages (verbose), the on_progress
        callback, and the other events into the events list."""
        etype = event.get("_event", event.get("type", ""))

        if etype == "progress":
            pct = event.get("percent", 0)
            msg = event.get("message", "")
            if verbose:
                print(f"\r  [{pct:3d}%] {msg}", end="", flush=True, file=out)
            if on_progress:
                on_progress(pct, msg)

        elif etype == "done":
            if verbose:
                print(f"\r  [100%] Done.{'':40}", file=out)

        elif etype == "log":
            if verbose:
                msg = event.get("message", "")
                if msg:
                    print(f"  {msg}", file=out)

        elif etype == "error":
            if verbose:
                print(f"\n  ERROR: {event.get('message', 'Job failed')}", file=out)

        elif etype == "stopped":
            if verbose:
                print(f"\n  {event.get('message', 'Job stopped')}", file=out)

        elif events is not None:
            events.append(event)

    def status(self):
        """Check the server, and which versions are in use.

        Returns:
            Dict with 'ok', 'server_version' (None if the server doesn't report
            one) and 'sdk_version' (this package's version; its major.minor
            follows the server's), plus 'error' when 'ok' is False. In local
            mode, server_version is the version of the Red Cedar code in use.
        """
        from . import __version__
        if self.core:
            return {"ok": True, "server_version": self.core.version(), "sdk_version": __version__}
        try:
            resp = requests.get(f"{self._server('/health')}/health", headers=self._headers(), timeout=5)
        except requests.ConnectionError:
            return {"ok": False, "server_version": None, "sdk_version": __version__,
                    "error": "Cannot reach server"}
        try:
            body = resp.json()
        except ValueError:
            body = {}
        if not isinstance(body, dict):
            body = {}
        # Through the gateway (/api/health) the server's answer is under "backend"
        server = body.get("backend", body)
        if not isinstance(server, dict):
            server = {}
        ok = resp.status_code == 200 and server.get("status") == "ok"
        result = {"ok": ok, "server_version": server.get("version"), "sdk_version": __version__}
        if not ok:
            result["error"] = server.get("error") or f"HTTP {resp.status_code}"
        return result

    @property
    def server_version(self):
        """The version of the server this client is connected to (asked once)."""
        if self._server_version is None:
            self._server_version = self.status().get("server_version")
        return self._server_version
