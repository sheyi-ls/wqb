"""Simulation API mixin for WQBSession."""
import asyncio
import itertools
from collections.abc import Awaitable, Callable, Coroutine, Iterable, Sized
from typing import Any

from requests import Response

from ..common.constants import GET, POST, LOCATION, RETRY_AFTER, Alpha, MultiAlpha
from ..common.async_util import concurrent_await
from ..common.simulation_helpers import coerce_multi_targets, simulation_ref_url
from ..common.urls import URL_SIMULATIONS

__all__ = ['SimulationMixin']


class SimulationMixin:
    async def retry(
        self,
        method: str,
        url: str,
        *args,
        max_tries: int | Iterable[Any] = itertools.repeat(None),
        max_key_errors: int = 1,
        max_value_errors: int = 1,
        delay_key_error: float = 2.0,
        delay_value_error: float = 2.0,
        on_start: Callable[[dict[str, Any]], None] | None = None,
        on_finish: Callable[[dict[str, Any]], None] | None = None,
        on_success: Callable[[dict[str, Any]], None] | None = None,
        on_failure: Callable[[dict[str, Any]], None] | None = None,
        log: str | None = '',
        **kwargs,
    ) -> Coroutine[None, None, Response | None]:
        if isinstance(max_tries, int):
            max_tries = range(max_tries)
        tries = 0
        resp = None
        key_errors = 0
        value_errors = 0
        if log is not None:
            self.logger.info(f"{self}.retry(...) [start {max_tries}]: {log}")
        if on_start is not None:
            on_start(locals())
        for tries, _ in enumerate(max_tries, start=1):
            resp = self.request(method, url, *args, **kwargs)
            try:
                await asyncio.sleep(float(resp.headers[RETRY_AFTER]))
            except KeyError as e:
                key_errors += 1
                if max_key_errors <= key_errors:
                    if log is not None:
                        self.logger.info(
                            f"{self}.retry(...) [{key_errors} key_errors]: {log}"
                        )
                    if on_success is not None:
                        on_success(locals())
                    break
                await asyncio.sleep(delay_key_error)
            except ValueError as e:
                value_errors += 1
                if max_value_errors <= value_errors:
                    if log is not None:
                        self.logger.info(
                            f"{self}.retry(...) [{value_errors} value_errors]: {log}"
                        )
                    if on_success is not None:
                        on_success(locals())
                    break
                await asyncio.sleep(delay_value_error)
        else:
            self.logger.warning(
                '\n'.join(
                    (
                        f"{self}.retry(...) [max {tries} tries ran out]",
                        f"self.request(method, url, *args, **kwargs):",
                        f"    method: {method}",
                        f"    url: {url}",
                        f"    args: {args}",
                        f"    kwargs: {kwargs}",
                        f"{resp}:",
                        f"    status_code: {resp.status_code}",
                        f"    reason: {resp.reason}",
                        f"    url: {resp.url}",
                        f"    elapsed: {resp.elapsed}",
                        f"    headers: {resp.headers}",
                        f"    text: {resp.text}",
                    )
                )
            )
            if on_failure is not None:
                on_failure(locals())
        if log is not None:
            self.logger.info(f"{self}.retry(...) [finish {tries} tries]: {log}")
        if on_finish is not None:
            on_finish(locals())
        return resp

    async def simulate(
        self,
        target: Alpha | MultiAlpha,
        *args,
        max_tries: int | Iterable[Any] = range(600),
        on_nolocation: Callable[[dict[str, Any]], None] | None = None,
        log: str | None = '',
        retry_log: str | None = None,
        **kwargs,
    ) -> Coroutine[None, None, Response | None]:
        resp = self.post(
            URL_SIMULATIONS,
            json=target,
            expected=self.expected_location,
            max_tries=60,
            delay_unexpected=5.0,
        )
        try:
            url = resp.headers[LOCATION]
        except KeyError as e:
            self.logger.warning(
                '\n'.join(
                    (
                        f"{self}.simulate(...) [",
                        f"    {repr(e)}",
                        f"    {target}",
                        f"]:",
                        f"{resp}:",
                        f"    status_code: {resp.status_code}",
                        f"    reason: {resp.reason}",
                        f"    url: {resp.url}",
                        f"    elapsed: {resp.elapsed}",
                        f"    headers: {resp.headers}",
                        f"    text: {resp.text}",
                    )
                )
            )
            if on_nolocation is not None:
                on_nolocation(locals())
            return None
        resp = await self.retry(
            GET, url, *args, max_tries=max_tries, log=retry_log, **kwargs
        )
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.simulate(...) [",
                        f"    {url}",
                        # f"    {target}",
                        f"]: {log}",
                    )
                )
            )
        return resp

    async def multi_simulate(
        self,
        targets: MultiAlpha | Iterable[Alpha | str],
        *args,
        settings: dict[str, Any] | None = None,
        fetch_alpha_details: bool = False,
        max_tries: int | Iterable[Any] = range(600),
        max_parent_tries: int | Iterable[Any] = range(200),
        on_nolocation: Callable[[dict[str, Any]], None] | None = None,
        log: str | None = '',
        retry_log: str | None = None,
        **kwargs,
    ) -> Coroutine[None, None, dict[str, Any] | None]:
        """
        Run a BRAIN multisimulation: one POST with 2-10 alphas, then poll
        parent and child simulation URLs until each alpha completes.

        Parameters
        ----------
        targets: MultiAlpha | Iterable[Alpha | str]
            Either pre-built REGULAR alpha dicts or expression strings.
            Strings are converted via `build_regular_alpha` using *settings*.
        settings: dict[str, Any] | None = None
            Shared settings for expression-string targets. See
            `build_regular_alpha` for supported keys.
        fetch_alpha_details: bool = False
            When *True*, fetch each completed alpha from `/alphas/{id}`.
        max_tries: int | Iterable[Any] = range(600)
            Retry budget for each child simulation poll.
        max_parent_tries: int | Iterable[Any] = range(200)
            Retry budget while waiting for parent ``children`` to appear.
        on_nolocation: Callable | None = None
            Callback when the POST response has no ``Location`` header.
        log: str | None = ''
            Log message suffix. *None* disables logging.
        retry_log: str | None = None
            Log suffix passed to internal `retry` calls.
        kwargs
            Forwarded to child-simulation `retry` GET requests.

        Returns
        -------
        dict[str, Any] | None
            ``location``, ``parent``, and ``children`` entries. Each child
            contains ``location``, ``simulation``, ``alpha_id``, and
            optionally ``alpha`` when *fetch_alpha_details* is *True*.
            Returns *None* when POST fails to return a location header.

        Notes
        -----
        Unlike `simulate`, this method is intended for multisimulation
        batches and always waits for every child simulation to finish.
        Use `concurrent_simulate` when you need multiple independent
        simulation slots in parallel.
        """
        multi = coerce_multi_targets(targets, settings=settings)
        resp = self.post(
            URL_SIMULATIONS,
            json=multi,
            expected=self.expected_location,
            max_tries=60,
            delay_unexpected=5.0,
        )
        try:
            location = resp.headers[LOCATION]
        except KeyError:
            self.logger.warning(
                '\n'.join(
                    (
                        f"{self}.multi_simulate(...) [no Location header]",
                        f"    {multi}",
                        f"{resp}:",
                        f"    status_code: {resp.status_code}",
                        f"    text: {resp.text}",
                    )
                )
            )
            if on_nolocation is not None:
                on_nolocation({'target': multi, 'resp': resp})
            return None

        parent_resp, child_refs = await self._wait_multi_simulation_children(
            location,
            expected_children=len(multi),
            max_parent_tries=max_parent_tries,
            retry_log=retry_log,
            log=log,
        )
        if parent_resp is None:
            return None

        children: list[dict[str, Any]] = []
        for idx, child_ref in enumerate(child_refs, start=1):
            child_url = simulation_ref_url(child_ref)
            child_resp = await self.retry(
                GET,
                child_url,
                *args,
                max_tries=max_tries,
                log=retry_log,
                **kwargs,
            )
            child_entry: dict[str, Any] = {
                'index': idx,
                'location': child_url,
                'simulation': None,
                'alpha_id': None,
                'alpha': None,
                'error': None,
            }
            if child_resp is None:
                child_entry['error'] = 'child simulation polling timed out'
            else:
                child_data = child_resp.json()
                child_entry['simulation'] = child_data
                child_entry['alpha_id'] = child_data.get('alpha')
                if child_entry['alpha_id'] and fetch_alpha_details:
                    alpha_resp = self.locate_alpha(
                        child_entry['alpha_id'],
                        log=None,
                    )
                    if alpha_resp.ok:
                        child_entry['alpha'] = alpha_resp.json()
                    else:
                        child_entry['error'] = (
                            f"failed to fetch alpha details: {alpha_resp.status_code}"
                        )
            children.append(child_entry)

        result = {
            'location': location,
            'parent': parent_resp.json(),
            'children': children,
            'total_requested': len(multi),
            'total_completed': sum(1 for c in children if c.get('alpha_id')),
        }
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.multi_simulate(...) [",
                        f"    {location}",
                        f"    completed {result['total_completed']}/{result['total_requested']}",
                        f"]: {log}",
                    )
                )
            )
        return result

    async def _wait_multi_simulation_children(
        self,
        location: str,
        *,
        expected_children: int,
        max_parent_tries: int | Iterable[Any] = range(200),
        retry_log: str | None = None,
        log: str | None = '',
    ) -> Coroutine[None, None, tuple[Response | None, list[str]]]:
        if isinstance(max_parent_tries, int):
            max_parent_tries = range(max_parent_tries)
        parent_resp: Response | None = None
        child_refs: list[str] = []
        for _ in max_parent_tries:
            parent_resp = self.get(location)
            if not parent_resp.ok:
                await asyncio.sleep(5.0)
                continue
            child_refs = parent_resp.json().get('children', [])
            if child_refs:
                break
            try:
                await asyncio.sleep(float(parent_resp.headers[RETRY_AFTER]))
            except KeyError:
                await asyncio.sleep(5.0)
        if not child_refs:
            self.logger.warning(
                f"{self}._wait_multi_simulation_children(...) "
                f"[no children after polling parent {location}]"
            )
            return None, []
        if log is not None:
            self.logger.info(
                f"{self}._wait_multi_simulation_children(...) "
                f"[{len(child_refs)}/{expected_children} children]: {log}"
            )
        return parent_resp, child_refs

    async def concurrent_simulate(
        self,
        targets: Iterable[Alpha | MultiAlpha],
        concurrency: int | asyncio.Semaphore,
        *args,
        return_exceptions: bool = False,
        log: str | None = '',
        log_gap: int = 100,
        **kwargs,
    ) -> Coroutine[None, None, list[Response | BaseException]]:
        if not isinstance(targets, Sized):
            targets = list(targets)
        if log is None:
            log_gap = 0
        if isinstance(concurrency, int):
            concurrency = asyncio.Semaphore(value=concurrency)
        total = len(targets)
        if log is not None:
            self.logger.info(
                f"{self}.concurrent_simulate(...) [start {total}, {concurrency._value}]: {log}"
            )
        resp = await concurrent_await(
            (
                self.simulate(
                    target,
                    *args,
                    log=(
                        f"{idx}/{total} = {int(100*idx/total)}%"
                        if 0 != log_gap and 0 == idx % log_gap
                        else None
                    ),
                    **kwargs,
                )
                for idx, target in enumerate(targets, start=1)
            ),
            concurrency=concurrency,
            return_exceptions=return_exceptions,
        )
        if log is not None:
            self.logger.info(
                f"{self}.concurrent_simulate(...) [finish {total}, {concurrency._value}]: {log}"
            )
        return resp
