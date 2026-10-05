import asyncio
from typing import Any, Awaitable, List, Optional


async def gather_tolerant(coros: List[Awaitable], limit: Optional[int] = None) -> List[Any]:
    """Run coroutines concurrently, returning either each result or the
    Exception it raised (never propagates a single failure to the caller —
    partial failure is expected and handled by callers, not this helper)."""
    if limit:
        semaphore = asyncio.Semaphore(limit)

        async def _bounded(coro):
            async with semaphore:
                return await coro

        coros = [_bounded(c) for c in coros]

    return await asyncio.gather(*coros, return_exceptions=True)
