"""Dataset listing and selection."""

import os


class DatasetManager:
    """Access the dataset catalog on the server."""

    def __init__(self, client):
        self._client = client

    def list(self):
        """List all available datasets in the catalog.

        Returns:
            List of dataset dicts with id, name, description, rows, columns, classes.
        """
        if self._client.core:   # local mode: call the core directly
            return self._client.core.datasets()
        return self._client._get("/datasets")

    def upload(self, file_path, kind="training"):
        """Upload a CSV file to the server for training.

        The last column is the target (class label); a header row is optional.
        A samples file identical to one you already uploaded (same name and contents)
        is not stored again: you get the earlier file's ID.

        Args:
            file_path: Path to a local .csv file.
            kind: 'training' (a training dataset, the default) or 'samples' (rows for
                a trained model to classify or predict, as inference.run() uploads them).

        Returns:
            The dataset ID to pass to training.run() (or inference.run()).
        """
        if self._client.core:
            return self._client._local_call(self._client.core.upload, file_path, kind)
        return self._client._post_file("/upload", file_path, params={"kind": kind})["jobId"]

    def uploads(self, kind="training"):
        """List your uploaded files of one kind, newest first.

        Every CSV file passed to training.run() by path is uploaded as a training
        dataset, and one passed to inference.run() as a samples file; each stays on the
        server until you delete it.

        Args:
            kind: 'training' (the default) or 'samples'.

        Returns:
            List of dicts with id (the dataset ID), name, created_at, file_size, rows,
            columns, problem (why training can't use the file, or None), task
            ('classification' or 'regression'), target (the target column's name),
            classes, and models (the number of trained models that need the file).
        """
        if self._client.core:
            return self._client._local_call(self._client.core.uploads, kind)
        return self._client._get(f"/uploads?kind={kind}")

    def delete_upload(self, dataset_id):
        """Delete one of your uploaded files.

        A model trained on the file needs it: evaluation, predictions, training analysis
        and explainable AI read the training data again. Delete those models first, or
        keep the file while you use them.

        Args:
            dataset_id: The file's ID (from upload() or uploads()).
        """
        if self._client.core:
            return self._client._local_call(self._client.core.delete_upload, dataset_id)
        return self._client._delete(f"/uploads/{dataset_id}")

    def _as_id(self, data, kind="training"):
        """A CSV file path is uploaded (as kind) and replaced by its dataset ID; anything
        else (a catalog ID or an upload ID) is returned as it is."""
        if isinstance(data, os.PathLike) or (isinstance(data, str) and os.path.isfile(data)):
            return self.upload(os.fspath(data), kind)
        # IDs never end in .csv, so this is a file path that doesn't exist
        if isinstance(data, str) and data.lower().endswith(".csv"):
            raise FileNotFoundError(f"No such file: {data}")
        return data
