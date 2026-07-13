"""Inference — classify test data using a trained model."""


class InferenceManager:
    """Run inference on trained models."""

    def __init__(self, client):
        self._client = client

    def run(self, train_id, verbose=False, on_progress=None):
        """Run inference on a trained model's test dataset.

        Args:
            train_id: Training job ID (from training.run() result).
            verbose: Print progress to stdout.
            on_progress: Callback(percent, message) for progress updates.

        Returns:
            Dict with overall_accuracy, overall_loss, per_class results, etc.
        """
        return self._client._run_job(
            "/inference",
            "/inference/{job_id}/stream",
            body={"train_id": train_id, "user_id": "sdk"},
            verbose=verbose,
            on_progress=on_progress,
        )

    def models(self):
        """List available trained models on the server.

        Returns:
            Dict with 'models' list containing model metadata.
        """
        return self._client._get("/inference/models")
