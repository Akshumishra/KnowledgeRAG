import abc
from typing import BinaryIO, AsyncGenerator


class BaseStorageProvider(abc.ABC):
    """
    Abstract interface for document storage (Local, S3, Azure, etc.).
    """

    @abc.abstractmethod
    async def upload_file(
        self, file: BinaryIO, filename: str, workspace_id: str
    ) -> str:
        """
        Upload a file and return its storage path/URI.
        """
        pass

    @abc.abstractmethod
    async def download_file(self, storage_path: str) -> bytes:
        """
        Download a file by its storage path.
        """
        pass

    @abc.abstractmethod
    async def delete_file(self, storage_path: str) -> bool:
        """
        Delete a file.
        """
        pass

    @abc.abstractmethod
    async def get_stream(self, storage_path: str) -> AsyncGenerator[bytes, None]:
        """
        Get an async generator yielding file chunks (useful for streaming large files).
        """
        pass
