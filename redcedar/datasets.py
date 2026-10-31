"""Dataset listing and selection."""


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
