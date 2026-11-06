"""Explainable AI — identify which features drive classification."""


class ExplainableManager:
    """Run explainable AI analysis on trained models."""

    def __init__(self, client):
        self._client = client

    def run(self, train_id, verbose=False, on_progress=None, settings=None):
        """Run explainable AI analysis on a trained model.

        Constructs quantum circuits to identify which input
        features are most important for classification decisions.

        Args:
            train_id: Training job ID (from training.run() result).
            verbose: Print progress to stdout; "log" also prints the server's log for the job.
            on_progress: Callback(percent, message) for progress updates.
            settings: Optional dict of runtime overrides (e.g. backend, parallelize).

        Returns:
            Dict with qubit_map (feature importance per qubit),
            distributions, convergence values, feature_indices, etc.
        """
        if self._client.core:   # local mode: call the core directly
            return self._client._run_local(self._client.core.explain, train_id, settings=settings,
                                           verbose=verbose, on_progress=on_progress)
        body = {"train_id": train_id, "user_id": "sdk"}
        if settings:
            body["settings"] = settings
        return self._client._run_job(
            "/applications/explainable",
            "/applications/explainable/{job_id}/stream",
            body=body,
            verbose=verbose,
            on_progress=on_progress,
        )
