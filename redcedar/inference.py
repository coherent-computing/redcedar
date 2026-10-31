"""Inference — classify test data using a trained model."""


class InferenceManager:
    """Run inference on trained models."""

    def __init__(self, client):
        self._client = client

    def run(self, train_id, layer=None, verbose=False, on_progress=None, settings=None):
        """Run inference on a trained model's test dataset.

        Args:
            train_id: Training job ID (from training.run() result).
            layer: Optional layer number to run inference on (default: highest layer).
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

    def models(self):
        """List available trained models on the server.

        Returns:
            Dict with 'models' list containing model metadata.
        """
        return self._client._get("/inference/models")
