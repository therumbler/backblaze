import sys
import asyncio
import threading
import time
import typing

from httpx import AsyncClient, Client

from .base import Base

from .models.auth import AuthModel
from .models.bucket import BucketModel

from .http.awaiting import AwaitingHTTP
from .http.blocking import BlockingHTTP

from .bucket.awaiting import AwaitingBucket
from .bucket.blocking import BlockingBucket

from .settings import BucketSettings


__version__ = "0.0.1"
__url__ = "https://backblaze.readthedocs.io/en/latest/"
__description__ = "Wrapper for Backblaze's B2."
__author__ = "WardPearce"
__author_email__ = "wardpearce@protonmail.com"
__license__ = "GPL-3.0 License"


class Awaiting(Base, AwaitingHTTP):
    def __init__(self, *args, **kwargs) -> None:
        if not sys.version_info[1] >= 7:
            sys.exit("Python 3.7 & above is required.")

        super().__init__(*args, **kwargs)

        self._client = AsyncClient()

    async def close(self) -> None:
        """Closes any underlying TCP sessions.
        """

        await self._client.aclose()

    async def create_bucket(self, settings: BucketSettings
                            ) -> (BucketModel, AwaitingBucket):
        """Used to create a bucket.

        Parameters
        ----------
        settings: BucketSettings
            Holds bucket settings.

        Returns
        -------
        BucketModel
            Holds details on a bucket.
        AwaitingBucket
            Used to interact with a bucket.
        """

        data = BucketModel(await self._post(
            url=self._routes.bucket.create,
            json=settings.payload
        ))

        return data, self.bucket(data.bucket_id)

    async def buckets(self, type: list = ["all"]
                      ) -> typing.AsyncGenerator[BucketModel, AwaitingBucket]:
        """Lists buckets.

        Parameters
        ----------
        type : list, optional
            Used to filter bucket types, by default ["all"]

        Yields
        -------
        BucketModel
            Holds details on bucket.
        AwaitingBucket
            Used for interacting with bucket.
        """

        data = await self._post(
            url=self._routes.bucket.list,
            json={"bucketTypes": type}
        )

        for bucket in data["buckets"]:
            yield BucketModel(bucket), self.bucket(bucket["bucketId"])

    def bucket(self, bucket_id: str) -> AwaitingBucket:
        """Used to interact with a bucket.

        Parameters
        ----------
        bucket_id : str
            ID of Bucket.

        Returns
        -------
        AwaitingBucket
        """

        return AwaitingBucket(self, bucket_id)

    async def __authorize_background(self) -> None:
        """Used to refresh auth tokens every 23.5 hours.
        """

        self._running_task = True

        await asyncio.sleep(self._refresh_seconds)
        await self.authorize()

        self._running_task = False

    async def authorize(self) -> AuthModel:
        """Used to authorize B2 account.

        Returns
        -------
        AuthModel
            Holds data on account auth.
        """

        resp = await self._client.get(url=self._auth_url, auth=self._auth)
        resp.raise_for_status()

        data = AuthModel(resp.json())

        self.account_id = data.account_id

        self._format_routes(
            data.api_url,
            data.download_url
        )

        self._client.headers["Authorization"] = data.auth_token

        if not self._running_task:
            asyncio.create_task(self.__authorize_background())

        return data


class Blocking(Base, BlockingHTTP):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._client = Client()

    def close(self) -> None:
        """Closes any underlying TCP sessions.
        """

        self._client.close()

    def create_bucket(self, settings: BucketSettings
                      ) -> (BucketModel, BlockingBucket):
        """Used to create a bucket.

        Parameters
        ----------
        settings: BucketSettings
            Holds bucket settings.

        Returns
        -------
        BucketModel
            Holds details on a bucket.
        BlockingBucket
            Used to interact with a bucket.
        """

        data = BucketModel(self._post(
            url=self._routes.bucket.create,
            json=settings.payload,
        ))

        return data, self.bucket(data.bucket_id)

    def buckets(self, type: list = ["all"]
                ) -> typing.Generator[BucketModel, BlockingBucket, None]:
        """Lists buckets.

        Parameters
        ----------
        type : list, optional
            Used to filter bucket types, by default ["all"]

        Yields
        -------
        BucketModel
            Holds details on bucket.
        BlockingBucket
            Used for interacting with bucket.
        """

        data = self._post(
            url=self._routes.bucket.list,
            json={"bucketTypes": type}
        )

        for bucket in data["buckets"]:
            yield BucketModel(bucket), self.bucket(bucket["bucketId"])

    def bucket(self, bucket_id: str) -> BlockingBucket:
        """Used to interact with a bucket.

        Parameters
        ----------
        bucket_id : str
            ID of Bucket.

        Returns
        -------
        BlockingBucket
        """

        return BlockingBucket(self, bucket_id)

    def __authorize_background(self) -> None:
        """Used to refresh auth tokens every 23.5 hours.
        """

        self._running_task = True

        time.sleep(self._refresh_seconds)
        self.authorize()

        self._running_task = False

    def authorize(self) -> AuthModel:
        """Used to authorize B2 account.

        Returns
        -------
        AuthModel
            Holds data on account auth.
        """

        resp = self._client.get(self._auth_url, auth=self._auth)
        resp.raise_for_status()

        data = AuthModel(resp.json())

        self.account_id = data.account_id

        self._format_routes(
            data.api_url,
            data.download_url
        )

        self._client.headers["Authorization"] = data.auth_token

        if not self._running_task:
            threading.Thread(target=self.__authorize_background)

        return data
