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
        return self._client._get("/datasets")

    def upload(self, file_path):
        """Upload a CSV file to the server for training.

        The last column is the target (class label); a header row is optional.

        Args:
            file_path: Path to a local .csv file.

        Returns:
            The dataset ID to pass to training.run().
        """
        return self._client._post_file("/upload", file_path)["jobId"]

    def _as_id(self, data):
        """A CSV file path is uploaded and replaced by its dataset ID; anything
        else (a catalog ID or an upload ID) is returned as it is."""
        if isinstance(data, os.PathLike) or (isinstance(data, str) and os.path.isfile(data)):
            return self.upload(os.fspath(data))
        # IDs never end in .csv, so this is a file path that doesn't exist
        if isinstance(data, str) and data.lower().endswith(".csv"):
            raise FileNotFoundError(f"No such file: {data}")
        return data
