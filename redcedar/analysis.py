"""Dataset analysis — PCA, Mutual Information, Resource Estimation."""


class AnalysisManager:
    """Run dataset analysis operations on the server."""

    def __init__(self, client):
        self._client = client

    def pca(self, dataset_id, verbose=False, on_progress=None):
        """Run PCA analysis on a dataset.

        Args:
            dataset_id: Dataset ID from the catalog (e.g., 'wdbc', 'iris').
            verbose: Print progress to stdout.
            on_progress: Callback(percent, message) for progress updates.

        Returns:
            Dict with variance_ratios, cumulative_variance, thresholds, etc.
        """
        if self._client.core:   # local mode: call the core directly
            return self._client._run_local(self._client.core.pca, dataset_id,
                                           verbose=verbose, on_progress=on_progress)
        return self._client._run_job(
            "/analysis/pca",
            "/analysis/pca/{job_id}/stream",
            body={"dataset_id": dataset_id},
            verbose=verbose,
            on_progress=on_progress,
        )

    def mi(self, dataset_id, verbose=False, on_progress=None):
        """Run Mutual Information feature importance analysis.

        Args:
            dataset_id: Dataset ID from the catalog.
            verbose: Print progress to stdout.
            on_progress: Callback(percent, message) for progress updates.

        Returns:
            Dict with ranked_features, cumulative_mi, thresholds, etc.
        """
        if self._client.core:   # local mode: call the core directly
            return self._client._run_local(self._client.core.mi, dataset_id,
                                           verbose=verbose, on_progress=on_progress)
        return self._client._run_job(
            "/analysis/mi",
            "/analysis/mi/{job_id}/stream",
            body={"dataset_id": dataset_id},
            verbose=verbose,
            on_progress=on_progress,
        )

    def qre(self, dataset_id, verbose=False, on_progress=None):
        """Run Quantum Resource Estimation.

        Args:
            dataset_id: Dataset ID from the catalog.
            verbose: Print progress to stdout.
            on_progress: Callback(percent, message) for progress updates.

        Returns:
            Dict with estimatedQubits, standardDeviation, plotData, etc.
        """
        if self._client.core:   # local mode: call the core directly
            return self._client._run_local(self._client.core.qre, dataset_id,
                                           verbose=verbose, on_progress=on_progress)
        return self._client._run_job(
            "/analysis/qre",
            "/analysis/qre/{job_id}/stream",
            body={"dataset_id": dataset_id},
            verbose=verbose,
            on_progress=on_progress,
        )
