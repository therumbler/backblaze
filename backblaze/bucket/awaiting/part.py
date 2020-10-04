from aiofile import AIOFile, Reader
from hashlib import sha1
from typing import AsyncGenerator

from ..base import BasePart

from ...models.file import PartModel, FileModel

from ...settings import CopyPartSettings


class AwaitingParts(BasePart):
    async def list(self, limit: int = 100) -> AsyncGenerator[PartModel, int]:
        """Used to list parts.

        Yields
        -------
        PartModel
        int
            Next part number.
        limit : int
            Part limit.
        """

        data = await self.context._post(
            json={
                "fileId": self._file.file_id,
                "startPartNumber":
                self.part_number if self.part_number > 0 else 1,
                "maxPartCount": limit
            },
            include_account=False,
            url=self.context._routes.file.list_parts
        )

        for part in data["parts"]:
            yield PartModel(part), data["nextPartNumber"]

    async def copy(self, settings: CopyPartSettings) -> PartModel:
        """Used to copy a part.

        Parameters
        ----------
        settings : CopyPartSettings

        Returns
        -------
        PartModel
        """

        return PartModel(await self.context._post(
            url=self.context._routes.file.copy_part,
            json={
                "sourceFileId": self._file.file_id,
                "partNumber":
                self.part_number if self.part_number > 0 else 1,
                **settings.payload
            },
            include_account=False,
        ))

    async def data(self, data: bytes) -> PartModel:
        """Uploads a part.

        Parameters
        ----------
        data : bytes

        Returns
        -------
        PartModel
            Holds details on upload part.
        """

        self.part_number += 1

        upload = await self._file.upload_url()

        sha1_str = sha1(data).hexdigest()
        self.sha1s_append(sha1_str)

        return PartModel(
            await self.context._post(
                headers={
                    "Content-Length": str(len(data)),
                    "X-Bz-Part-Number": str(self.part_number),
                    "X-Bz-Content-Sha1": sha1_str,
                    "Authorization": upload.authorization_token
                },
                include_account=False,
                url=upload.upload_url,
                data=data
            )
        )

    async def file(self, pathway: str) -> None:
        """Used to upload a file in parts.

        Parameters
        ----------
        pathway : str
            Local file pathway.
        """

        async with AIOFile(pathway, "rb") as afp:
            async for chunk in Reader(afp,
                                      chunk_size=self.context.chunk_size):
                await self.data(chunk)

    async def finish(self) -> FileModel:
        """Used to complete a part upload.

        Returns
        -------
        FileModel
            Holds details on uploaded file.
        """

        return FileModel(
            await self.context._post(
                url=self.context._routes.file.finish_large,
                json={
                    "fileId": self._file.file_id,
                    "partSha1Array": self.sha1s
                },
                include_account=False
            )
        )