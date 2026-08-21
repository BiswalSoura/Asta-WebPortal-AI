import shutil
from pathlib import Path
from uuid import UUID


class LocalDocumentStorage:
    def __init__(
        self,
        base_path: str | Path,
    ) -> None:
        self.base_path = Path(base_path)

    def store(
        self,
        source_path: Path,
        document_id: UUID,
        version_number: int,
    ) -> str:
        destination_directory = (
            self.base_path
            / str(document_id)
            / f"v{version_number}"
        )

        destination_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = (
            destination_directory
            / source_path.name
        )

        shutil.copy2(
            source_path,
            destination,
        )

        return destination.as_posix()

    @staticmethod
    def delete(
        stored_path: str,
    ) -> None:
        path = Path(stored_path)

        if path.exists() and path.is_file():
            path.unlink()