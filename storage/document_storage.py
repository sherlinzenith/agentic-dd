from pathlib import Path


class LocalDocumentStorage:
    """
    Local development storage for uploaded documents.

    Production implementation can later use S3-compatible storage
    without changing the document processing layer.
    """

    def __init__(self, root: str = "storage/uploads"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        file_name: str,
        content: bytes,
        project_id: str,
    ) -> str:
        project_dir = self.root / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        destination = project_dir / file_name
        destination.write_bytes(content)

        return str(destination)

    def exists(self, storage_key: str) -> bool:
        return Path(storage_key).exists()

    def get_path(self, storage_key: str) -> Path:
        path = Path(storage_key)

        if not path.exists():
            raise FileNotFoundError(
                f"Stored document not found: {storage_key}"
            )

        return path
