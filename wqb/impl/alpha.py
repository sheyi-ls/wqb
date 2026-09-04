"""Alpha API mixin for WQBSession."""
import asyncio
import sys
from collections.abc import Coroutine, Generator, Iterable, Sized
from pathlib import Path
from typing import Any

from requests import Response

from ..common.async_util import concurrent_await

from ..common.constants import (
    GET,
    POST,
    Null,
    Region,
    Delay,
    Universe,
    InstrumentType,
    Status,
    AlphaType,
    AlphaCategory,
    Language,
    Color,
    Neutralization,
    UnitHandling,
    NanHandling,
    Pasteurization,
    AlphasOrder,
)
from ..common.filter_range import FilterRange
from ..common.urls import (
    URL_ALPHAS_ALPHAID,
    URL_ALPHAS_ALPHAID_CHECK,
    URL_ALPHAS_ALPHAID_PNL,
    URL_ALPHAS_ALPHAID_SUBMIT,
    URL_ALPHAS_ALPHAID_YEARLY_STATS,
    URL_USERS_SELF_ALPHAS,
)
from ..common.wait_get import wait_get

__all__ = ['AlphaMixin']


class AlphaMixin:
    def locate_alpha(
        self,
        alpha_id: str,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        url = URL_ALPHAS_ALPHAID.format(alpha_id)
        resp = self.get(url, *args, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.locate_alpha(...) [",
                        f"    {url}",
                        f"]: {log}",
                    )
                )
            )
        return resp

    def locate_alpha_brief(
        self,
        alpha_id: str,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> dict[str, Any]:
        """Return trimmed alpha payload: settings, regular code, and is metrics."""
        resp = self.locate_alpha(alpha_id, *args, log=log, **kwargs)
        resp.raise_for_status()
        body = resp.json()
        regular = body.get('regular') or {}
        code = regular.get('code') if isinstance(regular, dict) else regular
        return {
            'id': body.get('id', alpha_id),
            'settings': body.get('settings') or {},
            'regular': code,
            'is': body.get('is') or {},
        }

    def get_pnl(
        self,
        alpha_id: str,
        *args,
        max_retries: int = 10,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        """Fetch alpha PnL recordset (``GET /alphas/{id}/recordsets/pnl``)."""
        url = URL_ALPHAS_ALPHAID_PNL.format(alpha_id)
        resp = wait_get(self, url, *args, max_retries=max_retries, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.get_pnl(...) [",
                        f"    {url}",
                        f"]: {log}",
                    )
                )
            )
        return resp

    def get_yearly_stats(
        self,
        alpha_id: str,
        *args,
        max_retries: int = 10,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        """Fetch alpha yearly-stats recordset (``GET /alphas/{id}/recordsets/yearly-stats``)."""
        url = URL_ALPHAS_ALPHAID_YEARLY_STATS.format(alpha_id)
        resp = wait_get(self, url, *args, max_retries=max_retries, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.get_yearly_stats(...) [",
                        f"    {url}",
                        f"]: {log}",
                    )
                )
            )
        return resp

    def filter_alphas_limited(
        self,
        *args,
        name: str | None = None,
        competition: bool | None = None,
        type: AlphaType | None = None,
        language: Language | None = None,
        date_created: FilterRange | None = None,
        favorite: bool | None = None,
        date_submitted: FilterRange | None = None,
        start_date: FilterRange | None = None,
        status: Status | None = None,
        category: AlphaCategory | None = None,
        color: Color | None = None,
        tag: str | None = None,
        hidden: bool | None = None,
        region: Region | None = None,
        instrument_type: InstrumentType | None = None,
        universe: Universe | None = None,
        delay: Delay | None = None,
        decay: FilterRange | None = None,
        neutralization: Neutralization | None = None,
        truncation: FilterRange | None = None,
        unit_handling: UnitHandling | None = None,
        nan_handling: NanHandling | None = None,
        pasteurization: Pasteurization | None = None,
        sharpe: FilterRange | None = None,
        returns: FilterRange | None = None,
        pnl: FilterRange | None = None,
        turnover: FilterRange | None = None,
        drawdown: FilterRange | None = None,
        margin: FilterRange | None = None,
        fitness: FilterRange | None = None,
        book_size: FilterRange | None = None,
        long_count: FilterRange | None = None,
        short_count: FilterRange | None = None,
        sharpe60: FilterRange | None = None,
        sharpe125: FilterRange | None = None,
        sharpe250: FilterRange | None = None,
        sharpe500: FilterRange | None = None,
        os_is_sharpe_ratio: FilterRange | None = None,
        pre_close_sharpe: FilterRange | None = None,
        pre_close_sharpe_ratio: FilterRange | None = None,
        self_correlation: FilterRange | None = None,
        prod_correlation: FilterRange | None = None,
        order: AlphasOrder | None = None,
        limit: int = 100,
        offset: int = 0,
        others: Iterable[str] | None = None,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        limit = min(max(limit, 1), 100)
        offset = min(max(offset, 0), 10000 - limit)
        params = []
        if name is not None:
            params.append(f"name{name if name[0] in '~=' else '~' + name}")
        if competition is not None:
            params.append(f"competition={'true' if competition else 'false'}")
        if type is not None:
            params.append(f"type={type}")
        if language is not None:
            params.append(f"settings.language={language}")
        if date_created is not None:
            params.append(date_created.to_params('dateCreated'))
        if favorite is not None:
            params.append(f"favorite={'true' if favorite else 'false'}")
        if date_submitted is not None:
            params.append(date_submitted.to_params('dateSubmitted'))
        if start_date is not None:
            params.append(start_date.to_params('os.startDate'))
        if status is not None:
            params.append(f"status={status}")
        if category is not None:
            params.append(f"category={category}")
        if color is not None:
            params.append(f"color={color}")
        if tag is not None:
            params.append(f"tag={tag}")
        if hidden is not None:
            params.append(f"hidden={'true' if hidden else 'false'}")
        if region is not None:
            params.append(f"settings.region={region}")
        if instrument_type is not None:
            params.append(f"settings.instrumentType={instrument_type}")
        if universe is not None:
            params.append(f"settings.universe={universe}")
        if delay is not None:
            params.append(f"settings.delay={delay}")
        if decay is not None:
            params.append(decay.to_params('settings.decay'))
        if neutralization is not None:
            params.append(f"settings.neutralization={neutralization}")
        if truncation is not None:
            params.append(truncation.to_params('settings.truncation'))
        if unit_handling is not None:
            params.append(f"settings.unitHandling={unit_handling}")
        if nan_handling is not None:
            params.append(f"settings.nanHandling={nan_handling}")
        if pasteurization is not None:
            params.append(f"settings.pasteurization={pasteurization}")
        if sharpe is not None:
            params.append(sharpe.to_params('is.sharpe'))
        if returns is not None:
            params.append(returns.to_params('is.returns'))
        if pnl is not None:
            params.append(pnl.to_params('is.pnl'))
        if turnover is not None:
            params.append(turnover.to_params('is.turnover'))
        if drawdown is not None:
            params.append(drawdown.to_params('is.drawdown'))
        if margin is not None:
            params.append(margin.to_params('is.margin'))
        if fitness is not None:
            params.append(fitness.to_params('is.fitness'))
        if book_size is not None:
            params.append(book_size.to_params('is.bookSize'))
        if long_count is not None:
            params.append(long_count.to_params('is.longCount'))
        if short_count is not None:
            params.append(short_count.to_params('is.shortCount'))
        if sharpe60 is not None:
            params.append(sharpe60.to_params('os.sharpe60'))
        if sharpe125 is not None:
            params.append(sharpe125.to_params('os.sharpe125'))
        if sharpe250 is not None:
            params.append(sharpe250.to_params('os.sharpe250'))
        if sharpe500 is not None:
            params.append(sharpe500.to_params('os.sharpe500'))
        if os_is_sharpe_ratio is not None:
            params.append(os_is_sharpe_ratio.to_params('os.osISSharpeRatio'))
        if pre_close_sharpe is not None:
            params.append(pre_close_sharpe.to_params('os.preCloseSharpe'))
        if pre_close_sharpe_ratio is not None:
            params.append(pre_close_sharpe_ratio.to_params('os.preCloseSharpeRatio'))
        if self_correlation is not None:
            params.append(self_correlation.to_params('is.selfCorrelation'))
        if prod_correlation is not None:
            params.append(prod_correlation.to_params('is.prodCorrelation'))
        if order is not None:
            params.append(f"order={order}")
        params.append(f"limit={limit}")
        params.append(f"offset={offset}")
        if others is not None:
            params.extend(others)
        url = URL_USERS_SELF_ALPHAS + '?' + '&'.join(params)
        url = url.replace('+', '%2B')  # TODO: Can be improved.
        resp = self.get(url, *args, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.filter_alphas_limited(...) [",
                        f"    {url}",
                        f"]: {log}",
                    )
                )
            )
        return resp

    def filter_alphas(
        self,
        *args,
        limit: int = 100,
        offset: int = 0,
        log: str | None = '',
        log_gap: int = 100,
        **kwargs,
    ) -> Generator[Response, None, None]:
        if log is None:
            log_gap = 0
        count = self.filter_alphas_limited(
            *args, limit=1, offset=offset, log=log, **kwargs
        ).json()['count']
        offsets = range(offset, count, limit)
        if log is not None:
            self.logger.info(f"{self}.filter_alphas(...) [start {offsets}]: {log}")
        total = len(offsets)
        for idx, offset in enumerate(offsets, start=1):
            yield self.filter_alphas_limited(
                *args,
                limit=limit,
                offset=offset,
                log=(
                    f"{idx}/{total} = {int(100*idx/total)}%"
                    if 0 != log_gap and 0 == idx % log_gap
                    else None
                ),
                **kwargs,
            )
        if log is not None:
            self.logger.info(f"{self}.filter_alphas(...) [finish {offsets}]: {log}")

    def patch_properties(
        self,
        alpha_id: str,
        *args,
        favorite: bool | None = None,
        hidden: bool | None = None,
        name: str | Null | None = None,
        category: AlphaCategory | Null | None = None,
        tags: str | Iterable[str] | Null | None = None,
        color: Color | Null | None = None,
        regular_description: str | Null | None = None,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        url = URL_ALPHAS_ALPHAID.format(alpha_id)
        properties = {}
        if favorite is not None:
            properties['favorite'] = favorite
        if hidden is not None:
            properties['hidden'] = hidden
        if name is not None:
            properties['name'] = None if isinstance(name, Null) else name
        if category is not None:
            properties['category'] = None if isinstance(category, Null) else category
        if tags is not None:
            properties['tags'] = (
                []
                if isinstance(tags, Null)
                else [tags] if isinstance(tags, str) else list(tags)
            )
        if color is not None:
            properties['color'] = None if isinstance(color, Null) else color
        if regular_description is not None:
            properties['regular'] = {}
            properties['regular']['description'] = (
                None if isinstance(regular_description, Null) else regular_description
            )
        resp = self.patch(url, json=properties, *args, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.patch_properties(...) [",
                        f"    {url}",
                        f"    {properties}",
                        f"]: {log}",
                    )
                )
            )
        return resp

    async def check(
        self,
        alpha_id: str,
        *args,
        max_tries: int | Iterable[Any] = range(600),
        log: str | None = '',
        retry_log: str | None = None,
        **kwargs,
    ) -> Coroutine[None, None, Response | None]:
        url = URL_ALPHAS_ALPHAID_CHECK.format(alpha_id)
        resp = await self.retry(
            GET, url, *args, max_tries=max_tries, log=retry_log, **kwargs
        )
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.check(...) [",
                        f"    {url}",
                        f"]: {log}",
                    )
                )
            )
        return resp

    async def concurrent_check(
        self,
        alpha_ids: Iterable[str],
        concurrency: int | asyncio.Semaphore,
        *args,
        return_exceptions: bool = False,
        log: str | None = '',
        log_gap: int = 100,
        **kwargs,
    ) -> Coroutine[None, None, list[Response | BaseException]]:
        if not isinstance(alpha_ids, Sized):
            alpha_ids = list(alpha_ids)
        if log is None:
            log_gap = 0
        if isinstance(concurrency, int):
            concurrency = asyncio.Semaphore(value=concurrency)
        total = len(alpha_ids)
        if log is not None:
            self.logger.info(
                f"{self}.concurrent_check(...) [start {total}, {concurrency._value}]: {log}"
            )
        resp = await concurrent_await(
            (
                self.check(
                    alpha_id,
                    *args,
                    log=(
                        f"{idx}/{total} = {int(100*idx/total)}%"
                        if 0 != log_gap and 0 == idx % log_gap
                        else None
                    ),
                    **kwargs,
                )
                for idx, alpha_id in enumerate(alpha_ids, start=1)
            ),
            concurrency=concurrency,
            return_exceptions=return_exceptions,
        )
        if log is not None:
            self.logger.info(
                f"{self}.concurrent_check(...) [finish {total}, {concurrency._value}]: {log}"
            )
        return resp

    def sc_check(
        self,
        alpha_id: str,
        *,
        threshold: float = 0.7,
        correlation_type: str = 'self',
        cache_dir: 'str | Path | None' = None,
        refresh_os_pool: bool = True,
        log: str | None = '',
    ) -> dict[str, Any]:
        """
        Local self-correlation check (no platform SC quota).

        See ``wqb.correlation.sc_check`` for details.
        """
        from pathlib import Path as _Path

        from .correlation import DEFAULT_OS_CACHE_DIR, sc_check as _sc_check

        result = _sc_check(
            self,
            alpha_id,
            threshold=threshold,
            correlation_type=correlation_type,  # type: ignore[arg-type]
            cache_dir=_Path(cache_dir) if cache_dir is not None else DEFAULT_OS_CACHE_DIR,
            refresh_os_pool=refresh_os_pool,
        )
        if log is not None:
            self.logger.info(
                f"{self}.sc_check(...) [{alpha_id}] "
                f"max={result.get('max_correlation')} pass={result.get('passes_check')}: {log}"
            )
        return result

    def sc_check_batch(
        self,
        alpha_ids: Iterable[str],
        *,
        threshold: float = 0.7,
        correlation_type: str = 'self',
        cache_dir: 'str | Path | None' = None,
        refresh_os_pool: bool = True,
        workers: int = 5,
        return_exceptions: bool = False,
        log: str | None = '',
    ) -> list[dict[str, Any] | BaseException]:
        """Batch local SC; OS pool synced once. See ``sc_check_batch`` in correlation."""
        from pathlib import Path as _Path

        from .correlation import DEFAULT_OS_CACHE_DIR, sc_check_batch as _sc_check_batch

        results = _sc_check_batch(
            self,
            alpha_ids,
            threshold=threshold,
            correlation_type=correlation_type,  # type: ignore[arg-type]
            cache_dir=_Path(cache_dir) if cache_dir is not None else DEFAULT_OS_CACHE_DIR,
            refresh_os_pool=refresh_os_pool,
            workers=workers,
            return_exceptions=return_exceptions,
        )
        if log is not None:
            ok = sum(1 for r in results if isinstance(r, dict))
            self.logger.info(
                f"{self}.sc_check_batch(...) [n={len(results)} ok={ok} workers={workers}]: {log}"
            )
        return results

    def ppac_check(
        self,
        alpha_id: str,
        *,
        threshold: float = 0.5,
        cache_dir: 'str | Path | None' = None,
        refresh_os_pool: bool = True,
        log: str | None = '',
    ) -> dict[str, Any]:
        """
        Local PPAC check: max correlation vs Power Pool OS alphas only.

        See ``impl.correlation.ppac_check`` for details.
        """
        from pathlib import Path as _Path

        from .correlation import DEFAULT_OS_CACHE_DIR, ppac_check as _ppac_check

        result = _ppac_check(
            self,
            alpha_id,
            threshold=threshold,
            cache_dir=_Path(cache_dir) if cache_dir is not None else DEFAULT_OS_CACHE_DIR,
            refresh_os_pool=refresh_os_pool,
        )
        if log is not None:
            self.logger.info(
                f"{self}.ppac_check(...) [{alpha_id}] "
                f"ppac={result.get('ppac_correlation')} pass={result.get('passes_check')}: {log}"
            )
        return result

    def ppac_check_batch(
        self,
        alpha_ids: Iterable[str],
        *,
        threshold: float = 0.5,
        cache_dir: 'str | Path | None' = None,
        refresh_os_pool: bool = True,
        workers: int = 5,
        return_exceptions: bool = False,
        log: str | None = '',
    ) -> list[dict[str, Any] | BaseException]:
        """Batch local PPAC; OS pool synced once. See ``ppac_check_batch`` in correlation."""
        from pathlib import Path as _Path

        from .correlation import DEFAULT_OS_CACHE_DIR, ppac_check_batch as _ppac_check_batch

        results = _ppac_check_batch(
            self,
            alpha_ids,
            threshold=threshold,
            cache_dir=_Path(cache_dir) if cache_dir is not None else DEFAULT_OS_CACHE_DIR,
            refresh_os_pool=refresh_os_pool,
            workers=workers,
            return_exceptions=return_exceptions,
        )
        if log is not None:
            ok = sum(1 for r in results if isinstance(r, dict))
            self.logger.info(
                f"{self}.ppac_check_batch(...) [n={len(results)} ok={ok} workers={workers}]: {log}"
            )
        return results

    def pc_check(
        self,
        alpha_id: str,
        *,
        threshold: float = 0.7,
        max_wait_seconds: float = 3600,
        poll_interval: float = 30,
        log: str | None = '',
    ) -> dict[str, Any]:
        """
        Production-correlation check via ``GET /alphas/{id}/correlations/prod``.

        See ``wqb.correlation.pc_check`` for details.
        """
        from .correlation import pc_check as _pc_check

        result = _pc_check(
            self,
            alpha_id,
            threshold=threshold,
            max_wait_seconds=max_wait_seconds,
            poll_interval=poll_interval,
            log=log,
        )
        if log is not None:
            self.logger.info(
                f"{self}.pc_check(...) [{alpha_id}] "
                f"max={result.get('max_correlation')} status={result.get('status')}: {log}"
            )
        return result

    async def submit(
        self,
        alpha_id: str,
        *args,
        max_tries: int | Iterable[Any] = range(600),
        log: str | None = '',
        retry_log: str | None = None,
        **kwargs,
    ) -> Coroutine[None, None, Response | None]:
        url = URL_ALPHAS_ALPHAID_SUBMIT.format(alpha_id)
        resp = await self.retry(
            POST, url, *args, max_tries=max_tries, log=retry_log, **kwargs
        )
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.submit(...) [",
                        f"    {url}",
                        f"]: {log}",
                    )
                )
            )
        return resp
