"""Training — start, monitor, and get results."""

import re

from .settings import load_settings

# Uploaded datasets are identified by the UUID the server returns from /upload.
_UPLOAD_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class TrainingManager:
    """Run model training on the server."""

    def __init__(self, client):
        self._client = client

    def run(self, dataset_id, settings=None, verbose=False, on_progress=None,
            train_size=None, test_size=None, class_range=None):
        """Train a model on a dataset.

        Args:
            dataset_id: A CSV file path (uploaded first), a dataset ID from the
                        catalog (e.g., 'wdbc'), an ID returned by
                        datasets.upload(), or any OpenML dataset name.
            settings: Optional overrides — dict, .json path, or .toml path.
                      Only specified keys override server defaults.
            verbose: Print progress to stdout.
            on_progress: Callback(percent, message) for progress updates.
            train_size: Optional training set size (fraction or count).
            test_size: Optional test set size (fraction or count).
            class_range: Optional list of classes to use (e.g. ['0', '1']).
                         Not used for uploaded datasets.

        Returns:
            Dict with train_id, total_layers, elapsed_seconds, etc., plus
            history (training loss/accuracy per iteration, by layer) and
            validation (test results at the end of each layer, by layer).
        """
        params = load_settings(settings)
        dataset_id = self._client.datasets._as_id(dataset_id)
        ds = self._dataset_selection(dataset_id)
        if train_size is not None:
            ds["train_size"] = train_size
        if test_size is not None:
            ds["test_size"] = test_size
        if class_range is not None:
            ds["class_range"] = list(class_range)
        params["dataset_selection"] = ds

        events = []
        result = self._client._run_job(
            "/train",
            "/train/{job_id}/stream",
            body={"parameters": params, "user_id": "sdk"},
            verbose=verbose,
            on_progress=on_progress,
            events=events,
        )

        # The SSE summary doesn't include train_id, but callers need it
        # for inference and explainable calls. Add it from the POST response
        # which _run_job used internally.
        if result and "train_id" not in result:
            result["train_id"] = self._client._last_job_id

        # Per-layer training curves and test results, from the events sent during training
        history, validation = {}, {}
        for e in events:
            etype = e.get("_event", e.get("type"))
            if etype == "datapoint":
                history.setdefault(e["layer"], []).append(
                    {k: e[k] for k in ("iteration", "train_loss", "train_accuracy") if k in e})
            elif etype == "validation":
                validation[e["layer"]] = {k: v for k, v in e.items()
                                          if k not in ("type", "_event", "layer")}
        result["history"] = history
        result["validation"] = validation

        return result

    def evaluate(self, train_id, layer=None, verbose=False, on_progress=None, settings=None):
        """Score a trained model on the test rows held back from its training run.

        No data is passed: the server rebuilds the same split from the model's
        saved settings. For a prediction per row on new data, use inference.run().

        Args:
            train_id: Training job ID (from training.run() result).
            layer: Optional layer number to score (default: highest layer).
            verbose: Print progress to stdout.
            on_progress: Callback(percent, message) for progress updates.
            settings: Optional dict of runtime overrides (e.g. backend, parallelize).

        Returns:
            Dict with overall_accuracy, overall_loss, per_class results, etc.
        """
        body = {"train_id": train_id, "user_id": "sdk"}
        if layer is not None:
            body["layer"] = layer
        if settings:
            body["settings"] = settings
        return self._client._run_job(
            "/inference",
            "/inference/{job_id}/stream",
            body=body,
            verbose=verbose,
            on_progress=on_progress,
        )

    def analyze(self, train_id, layer=None, verbose=False, on_progress=None):
        """Replay a trained model's saved parameters on the test data, giving
        test accuracy and loss over the course of training.

        Args:
            train_id: Training job ID (from training.run() result).
            layer: Optional layer number (default: last layer).
            verbose: Print progress to stdout.
            on_progress: Callback(percent, message) for progress updates.

        Returns:
            Dict with accuracy_history, loss_history, num_checkpoints,
            final_accuracy, final_loss, etc.
        """
        body = {"train_id": train_id, "user_id": "sdk"}
        if layer is not None:
            body["layer"] = layer
        return self._client._run_job(
            "/analysis/training",
            "/analysis/training/{job_id}/stream",
            body=body,
            verbose=verbose,
            on_progress=on_progress,
        )

    def status(self, train_id):
        """Get a training job's status, progress and summary.

        Returns:
            Dict with train_id, status, progress, summary, error_message.
        """
        return self._client._get(f"/train/{train_id}/status")

    def stop(self, train_id):
        """Ask the server to stop a running training job. Layers that finished
        are kept. Call it from another thread or process, since training.run()
        blocks until the job ends; that call then raises RuntimeError.
        """
        return self._client._post(f"/train/{train_id}/stop")

    def _dataset_selection(self, dataset_id):
        """Build the dataset selection the server expects, as the web UI does:
        the catalog entry for catalog datasets, an upload reference for uploads,
        and an OpenML request for anything else."""
        for entry in self._client.datasets.list():
            if entry.get("id") == dataset_id:
                return dict(entry)
        if _UPLOAD_ID.match(dataset_id):
            return {"type": "upload", "id": dataset_id}
        return {"id": dataset_id, "source": "openml", "dataset_name": dataset_id}
