"""Training — start, monitor, and get results."""

from .settings import load_settings


class TrainingManager:
    """Run model training on the server."""

    def __init__(self, client):
        self._client = client

    def run(self, dataset_id, settings=None, verbose=False, on_progress=None):
        """Train a model on a dataset.

        Args:
            dataset_id: Dataset ID from the catalog (e.g., 'wdbc').
            settings: Optional overrides — dict, .json path, or .toml path.
                      Only specified keys override server defaults.
            verbose: Print progress to stdout.
            on_progress: Callback(percent, message) for progress updates.

        Returns:
            Dict with train_id, total_layers, elapsed_seconds, etc.
        """
        params = load_settings(settings)
        params["dataset_selection"] = {
            "id": dataset_id,
            "source": "openml",
            "dataset_name": dataset_id,
        }

        result = self._client._run_job(
            "/train",
            "/train/{job_id}/stream",
            body={"parameters": params, "user_id": "sdk"},
            verbose=verbose,
            on_progress=on_progress,
        )

        # The SSE summary doesn't include train_id, but callers need it
        # for inference and explainable calls. Add it from the POST response
        # which _run_job used internally.
        if result and "train_id" not in result:
            result["train_id"] = self._client._last_job_id

        return result
