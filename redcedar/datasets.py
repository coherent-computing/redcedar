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
