"""Inference — predictions on new data from a trained model."""

import csv
import os


class InferenceManager:
    """Use trained models."""

    def __init__(self, client):
        self._client = client

    def run(self, train_id, data, layer=None, output=None, verbose=False, on_progress=None,
            settings=None):
        """Make a prediction for each row of new data.

        The columns are matched to the model's inputs by name when the file and
        the training data both have a header row, and by position otherwise. If
        the rows also contain the target column, the result has an accuracy too.

        Args:
            train_id: Training job ID (from training.run() result).
            data: A CSV file path (uploaded first), or an ID from datasets.upload().
            layer: Optional layer number to use (default: highest layer).
            output: Optional CSV file path to write the input rows plus the
                    predictions to.
            verbose: Print progress to stdout.
            on_progress: Callback(percent, message) for progress updates.
            settings: Optional dict of runtime overrides (e.g. backend, parallelize).

        Returns:
            Dict with train_id, layer, task, rows, and predictions: one dict per
            row. Classification: 'prediction' (the label) and 'probabilities'
            (class label to probability); 'accuracy' when the target column is
            present. Regression: 'prediction' (a number); 'mean_absolute_error'
            when the target column is present.
        """
        data_path = os.fspath(data) if output and isinstance(data, (str, os.PathLike)) else None
        data_id = self._client.datasets._as_id(data)
        if self._client.core:   # local mode: call the core directly
            result = self._client._run_local(self._client.core.predict, train_id, data_id,
                                             layer=layer, settings=settings,
                                             verbose=verbose, on_progress=on_progress)
        else:
            body = {"train_id": train_id, "user_id": "sdk", "data_id": data_id}
            if layer is not None:
                body["layer"] = layer
            if settings:
                body["settings"] = settings
            result = self._client._run_job(
                "/inference",
                "/inference/{job_id}/stream",
                body=body,
                verbose=verbose,
                on_progress=on_progress,
            )
        if output:
            if not data_path:
                raise ValueError("output= needs data given as a CSV file path")
            _write_predictions(data_path, result["predictions"], output)
        return result

    def models(self):
        """List available trained models on the server.

        Returns:
            Dict with 'models' list containing model metadata.
        """
        if self._client.core:   # local mode: call the core directly
            return self._client.core.models()
        return self._client._get("/inference/models")


def _write_predictions(data_path, predictions, output):
    """Write the input rows plus a prediction column and one probability column
    per class. A file without a header row gets none in the output either."""
    with open(data_path, newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        rows = [r for r in csv.reader(f, dialect) if r]

    def is_number(v):
        try:
            float(v)
            return True
        except ValueError:
            return False

    has_header = all(not is_number(v) for v in rows[0])
    header, body = (rows[0], rows[1:]) if has_header else (None, rows)
    if len(body) != len(predictions):
        raise ValueError(f"{len(body)} rows in {data_path}, {len(predictions)} predictions")

    # Regression predictions have no class probabilities, so no probability columns
    classes = sorted({c for p in predictions for c in p.get("probabilities", {})})
    with open(output, "w", newline="") as f:
        w = csv.writer(f)
        if header:
            w.writerow(header + ["prediction"] + [f"probability_{c}" for c in classes])
        for row, p in zip(body, predictions):
            w.writerow(row + [p["prediction"]] + [p["probabilities"].get(c, 0.0) for c in classes])
