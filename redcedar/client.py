"""Core client — HTTP requests, SSE streaming, authentication."""

import os
import sys
import json
import time
import threading
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


class _ProgressLine:
    """A job's verbose output: one line, rewritten on each progress update, with a dot
    added while the job is quiet so it's clear it's still working. The dots come every
    2 seconds at first, every 5 after 20 seconds and every 10 after a minute, counted
    from the last update."""

    def __init__(self, out=None):
        self._out = out or sys.stdout
        self._lock = threading.Lock()
        self._text = ""
        self._ndots = 0
        self._width = 0   # characters on the current line
        self._restart()
        self._stop = threading.Event()
        threading.Thread(target=self._dots, daemon=True).start()

    def _restart(self):
        self._since = time.monotonic()
        self._next = self._since + 2

    def _draw(self):
        """Write the whole line again, text and dots. Jupyter treats \\r as overwriting
        the line from its start, so the line is always redrawn rather than added to;
        trailing spaces clear what's left of a longer line."""
        s = self._text + "." * self._ndots
        print(f"\r{s}{' ' * max(self._width - len(s), 0)}", end="", flush=True, file=self._out)
        self._width = len(s)

    def _dots(self):
        while not self._stop.wait(0.5):
            with self._lock:
                now = time.monotonic()
                if now >= self._next:
                    self._ndots += 1
                    self._draw()
                    quiet = now - self._since
                    self._next = now + (2 if quiet < 20 else 5 if quiet < 60 else 10)

    def update(self, text):
        """Rewrite the line with new text; the dots start again."""
        with self._lock:
            self._text, self._ndots = text, 0
            self._draw()
            self._restart()

    def message(self, text):
        """A line of its own (a log line, an error), below the progress line."""
        with self._lock:
            if self._width:
                print(file=self._out)
            print(text, flush=True, file=self._out)
            self._text, self._ndots, self._width = "", 0, 0
            self._restart()

    def close(self):
        self._stop.set()
        with self._lock:
            if self._width:
                print(file=self._out)
                self._text, self._ndots, self._width = "", 0, 0


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
        to the same handler as a server job's: progress, log lines (verbose="log"), and the
        other events into the events list. Returns the job's result."""
        out = sys.stdout   # while the job runs, print() goes to its log
        line = _ProgressLine(out) if verbose else None
        on_event = lambda e: self._handle_event(e, verbose, on_progress, events, line)  # noqa: E731
        try:
            return self._local_call(fn, *args, on_event=on_event, **kwargs)
        finally:
            if line:
                line.close()

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

    def _open_stream(self, path, line=None):
        """Open a job's SSE stream. A queued job has no stream until it starts
        (the server answers 404), so wait for it to start."""
        waiting = False
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
            if line and not waiting:
                line.update("  Waiting in queue...")
            waiting = True
            time.sleep(2)

    def _stream_sse(self, path, line=None):
        """Consume an SSE stream, yielding parsed events."""
        resp = self._open_stream(path, line)

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

        line = _ProgressLine() if verbose else None
        try:
            for event in self._stream_sse(stream_path.format(job_id=job_id), line):
                self._handle_event(event, verbose, on_progress, events, line)
                etype = event.get("_event", event.get("type", ""))
                if etype == "done":
                    return event.get("summary", event)
                elif etype == "error":
                    raise RuntimeError(event.get("message", "Job failed"))
                elif etype == "stopped":
                    raise RuntimeError(event.get("message", "Job stopped"))
        finally:
            if line:
                line.close()

        raise RuntimeError("SSE stream ended without done/error event")

    def _handle_event(self, event, verbose, on_progress, events, line=None):
        """Report one job event: progress and messages (verbose; the server's log lines
        only with verbose="log"), the on_progress callback, and the other events into
        the events list. line is the job's _ProgressLine when verbose."""
        etype = event.get("_event", event.get("type", ""))

        if etype == "progress":
            pct = event.get("percent", 0)
            msg = event.get("message", "")
            if verbose:
                line.update(f"  [{pct:3d}%] {msg}")
            if on_progress:
                on_progress(pct, msg)

        elif etype == "done":
            if verbose:
                line.update("  [100%] Done.")
                line.close()

        elif etype == "log":
            if verbose == "log":
                msg = event.get("message", "")
                if msg:
                    line.message(f"  {msg}")

        elif etype == "error":
            if verbose:
                line.message(f"  ERROR: {event.get('message', 'Job failed')}")

        elif etype == "stopped":
            if verbose:
                line.message(f"  {event.get('message', 'Job stopped')}")

        else:
            # A training layer's test result
            if etype == "validation" and verbose:
                acc, loss = event.get("test_accuracy"), event.get("test_loss")
                if acc is not None:
                    line.message(f"  Layer {event.get('layer')}: test accuracy {acc:.1%}")
                elif loss is not None:
                    line.message(f"  Layer {event.get('layer')}: test loss {loss:.4f}")
            if events is not None:
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
