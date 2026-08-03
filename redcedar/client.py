"""Core client — HTTP requests, SSE streaming, authentication."""

import os
import json
import requests

from .datasets import DatasetManager
from .analysis import AnalysisManager
from .training import TrainingManager
from .inference import InferenceManager
from .explainable import ExplainableManager


def connect(url=None, api_key=None):
    """Create a RedCedarClient connected to the server.

    Args:
        url: Server URL. Defaults to REDCEDAR_URL env var or http://localhost:8000.
        api_key: API key. Defaults to REDCEDAR_API_KEY env var.

    Returns:
        RedCedarClient instance.
    """
    url = url or os.environ.get("REDCEDAR_URL", "http://localhost:8000")
    api_key = api_key or os.environ.get("REDCEDAR_API_KEY", "")
    return RedCedarClient(url, api_key)


class RedCedarClient:
    """Main client for interacting with the Red Cedar server."""

    def __init__(self, url, api_key):
        self.url = url.rstrip("/")
        self.api_key = api_key
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
        resp.raise_for_status()
        return resp.json()

    def _post(self, path, body=None):
        resp = requests.post(
            f"{self.url}{path}",
            headers=self._headers(),
            json=body or {},
        )
        resp.raise_for_status()
        return resp.json()

    def _stream_sse(self, path):
        """Consume an SSE stream, yielding parsed events."""
        resp = requests.get(
            f"{self.url}{path}",
            headers=self._headers(),
            stream=True,
        )
        resp.raise_for_status()

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

    def _run_job(self, post_path, stream_path, body=None, verbose=False, on_progress=None):
        """Start a job via POST, consume SSE until done. Returns summary."""
        result = self._post(post_path, body)
        job_id = result.get("job_id") or result.get("train_id")
        if not job_id:
            return result

        for event in self._stream_sse(stream_path.format(job_id=job_id)):
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

            elif etype == "error":
                msg = event.get("message", "Job failed")
                if verbose:
                    print(f"\n  ERROR: {msg}")
                raise RuntimeError(msg)

        raise RuntimeError("SSE stream ended without done/error event")

    def status(self):
        """Check server health."""
        try:
            resp = requests.get(f"{self.url}/", headers=self._headers(), timeout=5)
            return {"ok": resp.status_code == 200}
        except requests.ConnectionError:
            return {"ok": False, "error": "Cannot reach server"}
