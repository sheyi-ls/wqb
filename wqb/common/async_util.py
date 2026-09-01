import asyncio
from collections.abc import Awaitable, Coroutine, Iterable
from typing import Any

__all__ = ['concurrent_await']

async def concurrent_await(
    awaitables: Iterable[Awaitable[Any]],
    *,
    concurrency: int | asyncio.Semaphore | None = None,
    return_exceptions: bool = False,
) -> Coroutine[None, None, list[Any | BaseException]]:
    """
    Returns a `Coroutine` object that awaits an iterable series of
    `Awaitable` objects with a concurrency limit that controls the
    maximum number of `Awaitable` objects that can be awaited at the
    same time.

    Parameters
    ----------
    awaitables: Iterable[Awaitable[Any]]
        The iterable series of `Awaitable` objects.
    concurrency: int | asyncio.Semaphore | None = None
        The maximum number of `Awaitable` objects that can be awaited at
        the same time. If *int | asyncio.Semaphore*, the concurrency
        limit is set to it. If *None*, there is no concurrency limit.
    return_exceptions: bool = False
        Whether to return exceptions instead of raising them.

    Returns
    -------
    Coroutine[None, None, list[Any | BaseException]]
        A `Coroutine` object that awaits `Awaitable` objects
        concurrently.
    """
    if concurrency is None:
        return await asyncio.gather(*awaitables)
    if isinstance(concurrency, int):
        concurrency = asyncio.Semaphore(value=concurrency)

    async def semaphore_wrapper(
        awaitable: Awaitable[Any],
    ) -> Coroutine[None, None, Any]:
        """
        Wraps an `Awaitable` object with `concurrency`.

        Parameters
        ----------
        awaitable: Awaitable[Any]
            The `Awaitable` object to be wrapped.

        Returns
        -------
        Coroutine[None, None, Any]
            A `Coroutine` object that awaits the wrapped `Awaitable`
            object.
        """
        async with concurrency:
            result = await awaitable
        return result

    return await asyncio.gather(
        *(semaphore_wrapper(awaitable) for awaitable in awaitables),
        return_exceptions=return_exceptions,
    )

