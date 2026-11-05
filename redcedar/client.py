"""Core client — HTTP requests, SSE streaming, authentication."""

import os
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
        url: Server URL. Defaults to REDCEDAR_URL env var or http://localhost:8002
             (the port run_server uses).
        api_key: API key. Defaults to REDCEDAR_API_KEY env var.
        local: For development with the Red Cedar source. True (or the path of a
               red-cedar folder) starts the server inside this Python process, so
               breakpoints in the Red Cedar code work. The folder defaults to the
               REDCEDAR_CORE_PATH env var, or must already be importable.

    Returns:
        RedCedarClient instance.
    """
    if local:
        from .local import start_local_server
        url, api_key = start_local_server(None if local is True else local)
        return RedCedarClient(url, api_key)
    url = url or os.environ.get("REDCEDAR_URL", "http://localhost:8002")
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

    def __init__(self, url, api_key):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self._last_job_id = None
        self.datasets = DatasetManager(self)
        self.analysis = AnalysisManager(self)
        self.training = TrainingManager(self)
        self.inference = InferenceManager(self)
        self.explainable = ExplainableManager(self)

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["x-api-key"] = self.api_key
        return h

    def _get(self, path):
        resp = requests.get(f"{self.url}{path}", headers=self._headers())
        _raise_for_status(resp)
        return resp.json()

    def _post(self, path, body=None):
        resp = requests.post(
            f"{self.url}{path}",
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
                f"{self.url}{path}",
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
                f"{self.url}{path}",
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
            etype = event.get("_event", event.get("type", ""))

            if etype == "progress":
                pct = event.get("percent", 0)
                msg = event.get("message", "")
                if verbose:
                    print(f"\r  [{pct:3d}%] {msg}", end="", flush=True)
                if on_progress:
                    on_progress(pct, msg)

            elif etype == "done":
                if verbose:
                    print(f"\r  [100%] Done.{'':40}")
                return event.get("summary", event)

            elif etype == "log":
                if verbose:
                    msg = event.get("message", "")
                    if msg:
                        print(f"  {msg}")

            elif etype == "error":
                msg = event.get("message", "Job failed")
                if verbose:
                    print(f"\n  ERROR: {msg}")
                raise RuntimeError(msg)

            elif etype == "stopped":
                msg = event.get("message", "Job stopped")
                if verbose:
                    print(f"\n  {msg}")
                raise RuntimeError(msg)

            elif events is not None:
                events.append(event)

        raise RuntimeError("SSE stream ended without done/error event")

    def status(self):
        """Check server health."""
        try:
            resp = requests.get(f"{self.url}/", headers=self._headers(), timeout=5)
            return {"ok": resp.status_code == 200}
        except requests.ConnectionError:
            return {"ok": False, "error": "Cannot reach server"}
