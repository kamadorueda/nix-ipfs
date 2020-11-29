# Standard library
import aiohttp
import aiofiles
import contextlib
from uuid import uuid4 as uuid
from typing import (
    AsyncIterable,
    Optional,
)

# Third party libraries
from starlette.datastructures import (
    Headers,
)
from starlette.responses import (
    StreamingResponse,
)

# local libraries
from nix_ipfs_node import (
    config,
)


@contextlib.asynccontextmanager
async def request(
    *,
    headers: Optional[dict] = None,
    method: str,
    url: str,
) -> aiohttp.ClientResponse:
    connector = aiohttp.TCPConnector(verify_ssl=False)
    timeout = aiohttp.ClientTimeout(connect=None, total=60, sock_connect=None, sock_read=None)

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        trust_env=True,
    ) as session:
        async with session.request(
            headers=headers,
            method=method,
            url=url,
        ) as response:
            response.raise_for_status()
            yield response


async def iterate_response_chunks(
    *,
    chunk_size: int = 1024,
    response: aiohttp.ClientResponse,
) -> AsyncIterable[bytes]:
    while True:
        if chunk := await response.content.read(chunk_size):
            yield chunk
        else:
            break


async def iterate_file_chunks(
    *,
    chunk_size: int = 1024,
    path: str,
) -> AsyncIterable[bytes]:
    async with aiofiles.open(path, 'rb') as handle:
        while True:
            if chunk := await handle.read(chunk_size):
                yield chunk
            else:
                break


@contextlib.asynccontextmanager
async def stream_response_to_tmp_file(
    *,
    chunk_size: int = 1024,
    response: aiohttp.ClientResponse,
) -> str:
    async with config.ephemeral_file() as path:
        async with aiofiles.open(path, 'wb') as handle:
            async for chunk in iterate_response_chunks(
                chunk_size=chunk_size,
                response=response,
            ):
                await handle.write(chunk)

        yield path


async def stream_from_tmp_file(
    *,
    chunk_size: int = 1024,
    path: str,
) -> StreamingResponse:
    return StreamingResponse(
        content=iterate_file_chunks(
            chunk_size=chunk_size,
            path=path,
        ),
        media_type='application/octet-stream',
    )


async def stream_from_substituter(
    headers: Headers,
    method: str,
    url: str,
) -> StreamingResponse:

    async def generate_content():
        async with request(
            headers=headers,
            method=method,
            url=url,
        ) as response:
            yield response.status

            async for chunk in iterate_response_chunks(response=response):
                yield chunk

    content_generator = generate_content()
    status_code = await content_generator.asend(None)

    return StreamingResponse(
        content=content_generator,
        media_type='application/octet-stream',
        status_code=status_code,
    )


async def coordinator_delete(hash: str) -> bool:
    async with request(
        method='DELETE',
        url=config.build_coordinator_url(
            hash=hash,
            host=config.SUBSTITUTER_NETLOC,
            path='api/host/{host}/hash/{hash}',
        ),
    ) as response:
        response.raise_for_status()
        result = await response.json()

        return result['success'] == True


async def coordinator_get(hash: str) -> Optional[str]:
    async with request(
        method='GET',
        url=config.build_coordinator_url(
            hash=hash,
            host=config.SUBSTITUTER_NETLOC,
            path='api/host/{host}/hash/{hash}',
        ),
    ) as response:
        response.raise_for_status()
        result = await response.json()

        return result['cid']


async def coordinator_post(hash: str, cid: str) -> bool:
    async with request(
        method='POST',
        url=config.build_coordinator_url(
            cid=cid,
            hash=hash,
            host=config.SUBSTITUTER_NETLOC,
            path='api/host/{host}/hash/{hash}/cid/{cid}',
        ),
    ) as response:
        response.raise_for_status()
        result = await response.json()

        return result['success'] == True
