"""Local mode — the Red Cedar core called directly, in this Python process, for development.

connect(local=True) imports redcedar_core (installed with `pip install -e .` in a
red-cedar folder). Each SDK call then runs the same function the server runs for
that job, in this thread: no server and no HTTP, so a debugger steps from the SDK
call straight into the Red Cedar code. Needs the Red Cedar dependencies (Qiskit or
CUDA-Q, numpy, scikit-learn) in this environment.
"""

import os
import re
import sys
import uuid


# SDK request path -> call of the matching redcedar_core function (body = the request body)
_JOBS = {
    "/analysis/pca": lambda core, body, on_event: core.pca(body["dataset_id"], on_event=on_event),
    "/analysis/mi": lambda core, body, on_event: core.mi(body["dataset_id"], on_event=on_event),
    "/analysis/qre": lambda core, body, on_event: core.qre(body["dataset_id"], on_event=on_event),
    # The SDK picks the train_id, so it is known (client._last_job_id) while training runs
    "/train": lambda core, body, on_event, job_id: core.train(
        body["parameters"], on_event=on_event, train_id=job_id),
    # evaluate (no data) or predict (data_id)
    "/inference": lambda core, body, on_event: (
        core.predict(body["train_id"], body["data_id"], layer=body.get("layer"),
                     settings=body.get("settings"), on_event=on_event)
        if body.get("data_id") else
        core.evaluate(body["train_id"], layer=body.get("layer"),
                      settings=body.get("settings"), on_event=on_event)),
    "/analysis/training": lambda core, body, on_event: core.replay(
        body["train_id"], layer=body.get("layer"), on_event=on_event),
    "/applications/explainable": lambda core, body, on_event: core.explain(
        body["train_id"], layer=body.get("layer"), settings=body.get("settings"), on_event=on_event),
}


class NotFound(Exception):
    """A request for something that doesn't exist (the server answers 404)."""


def _found(result):
    if result is None:
        raise NotFound("Training job not found")   # the server's message
    return result


def _stopped(stopping, train_id):
    if not stopping:
        raise NotFound("Training job not found")   # not running in this process
    return {"status": "stopping", "message": f"Stop requested for {train_id}."}


# Other requests: (path pattern, call); the pattern's groups are passed to the call
_GETS = [
    (r"/datasets", lambda core: core.datasets()),
    (r"/train/([^/]+)/status", lambda core, i: _found(core.training.status(i))),
    (r"/inference/models", lambda core: core.models()),
]
_POSTS = [
    (r"/train/([^/]+)/stop", lambda core, i: _stopped(core.training.stop(i), i)),
]
_FILES = {
    "/upload": lambda core, file_path: {"jobId": core.upload(file_path)},
}


class LocalCore:
    """The redcedar_core functions behind the SDK's requests."""

    def __init__(self, core_path=None):
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
        self.core = redcedar_core
        self.core_path = core_path

    def job(self, path):
        """(job_id, direct function) for this job request, or None. job_id is None
        when the core picks the id itself."""
        op = _JOBS.get(path)
        if not op:
            return None
        if path == "/train":
            job_id = str(uuid.uuid4())
            return job_id, lambda body, on_event: op(self.core, body, on_event, job_id)
        return None, lambda body, on_event: op(self.core, body, on_event)

    def file(self, path):
        """The direct function for a file upload request, or None."""
        op = _FILES.get(path)
        return (lambda file_path: op(self.core, file_path)) if op else None

    def call(self, method, path):
        """The direct function for a GET or POST request (other than a job), or None."""
        for pattern, op in (_GETS if method == "GET" else _POSTS):
            m = re.fullmatch(pattern, path)
            if m:
                return lambda: op(self.core, *m.groups())
        return None
