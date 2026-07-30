import os
import uuid
from collections.abc import AsyncGenerator

import aiofiles
from fastapi import UploadFile
from src.core.config import settings
from src.providers.storage.base import BaseStorageProvider


class LocalStorageProvider(BaseStorageProvider):
    def __init__(self):
        self.upload_dir = settings.upload_dir
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir, exist_ok=True)

    async def upload_file(
        self, file: UploadFile, filename: str, workspace_id: str
    ) -> str:
        workspace_dir = os.path.join(self.upload_dir, workspace_id)
        os.makedirs(workspace_dir, exist_ok=True)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(workspace_dir, unique_filename)

        async with aiofiles.open(file_path, "wb") as out_file:
            while True:
                content = file.read(1024 * 1024)
                if not content:
                    break
                await out_file.write(content)

        return file_path

    async def download_file(self, path: str) -> bytes:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete_file(self, path: str) -> bool:
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    async def get_stream(self, path: str) -> AsyncGenerator[bytes, None]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        async with aiofiles.open(path, "rb") as f:
            while chunk := await f.read(1024 * 1024):
                yield chunk
