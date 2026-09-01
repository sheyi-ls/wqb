"""Data catalog API mixin for WQBSession."""
from collections.abc import Generator, Iterable

from requests import Response

from ..common.constants import (
    EQUITY,
    Region,
    Delay,
    Universe,
    InstrumentType,
    DataCategory,
    FieldType,
    DatasetsOrder,
    FieldsOrder,
)
from ..common.filter_range import FilterRange
from ..common.urls import (
    URL_DATAFIELDS,
    URL_DATAFIELDS_FIELDID,
    URL_DATASETS,
    URL_DATASETS_DATASETID,
    URL_OPERATORS,
)

__all__ = ['CatalogMixin']


class CatalogMixin:
    def search_operators(
        self,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        """
        Sends a GET request to `URL_OPERATORS`.

        Parameters
        ----------
        log: str | None = ''
            The message to be appended. If *None*, logging is disabled.

        Returns
        -------
        Response
            A `Response` object.

        Notes
        -----
        `args` and `kwargs` are passed to `Session.get`.

        Examples
        --------
        >>> wqbs = wqb.WQBSession(('<email>', '<password>'))
        >>> resp = wqbs.search_operators()
        >>> resp.ok
        True
        """
        url = URL_OPERATORS
        resp = self.get(url, *args, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.search_operators(...) [",
                        f"    {url}",
                        f"]: {log}",
                    )
                )
            )
        return resp

    def locate_dataset(
        self,
        dataset_id: str,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        """
        Sends a GET request to
        `URL_DATASETS_DATASETID.format(dataset_id)`.

        Parameters
        ----------
        dataset_id: str
            The dataset ID.
        log: str | None = ''
            The message to be appended. If *None*, logging is disabled.

        Returns
        -------
        Response
            A `Response` object.

        Notes
        -----
        `args` and `kwargs` are passed to `Session.get`.

        Examples
        --------
        >>> wqbs = wqb.WQBSession(('<email>', '<password>'))
        >>> resp = wqbs.locate_dataset('pv1')
        >>> resp.ok
        True
        """
        url = URL_DATASETS_DATASETID.format(dataset_id)
        resp = self.get(url, *args, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.locate_dataset(...) [",
                        f"    {url}",
                        f"]: {log}",
                    )
                )
            )
        return resp

    def search_datasets_limited(
        self,
        region: Region,
        delay: Delay,
        universe: Universe,
        *args,
        instrument_type: InstrumentType = EQUITY,
        search: str | None = None,
        category: DataCategory | None = None,
        theme: bool | None = None,
        coverage: FilterRange | None = None,
        value_score: FilterRange | None = None,
        alpha_count: FilterRange | None = None,
        user_count: FilterRange | None = None,
        order: DatasetsOrder | None = None,
        limit: int = 50,
        offset: int = 0,
        others: Iterable[str] | None = None,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        limit = min(max(limit, 1), 50)
        offset = min(max(offset, 0), 10000 - limit)
        params = [
            f"region={region}",
            f"delay={delay}",
            f"universe={universe}",
        ]
        params.append(f"instrumentType={instrument_type}")
        if search is not None:
            params.append(f"search={search}")
        if category is not None:
            params.append(f"category={category}")
        if theme is not None:
            params.append(f"theme={'true' if theme else 'false'}")
        if coverage is not None:
            params.append(coverage.to_params('coverage'))
        if value_score is not None:
            params.append(value_score.to_params('valueScore'))
        if alpha_count is not None:
            params.append(alpha_count.to_params('alphaCount'))
        if user_count is not None:
            params.append(user_count.to_params('userCount'))
        if order is not None:
            params.append(f"order={order}")
        params.append(f"limit={limit}")
        params.append(f"offset={offset}")
        if others is not None:
            params.extend(others)
        url = URL_DATASETS + '?' + '&'.join(params)
        resp = self.get(url, *args, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.search_datasets_limited(...) [",
                        f"    {url}",
                        f"]: {log}",
                    )
                )
            )
        return resp

    def search_datasets(
        self,
        region: Region,
        delay: Delay,
        universe: Universe,
        *args,
        limit: int = 50,
        offset: int = 0,
        log: str | None = '',
        log_gap: int = 100,
        **kwargs,
    ) -> Generator[Response, None, None]:
        if log is None:
            log_gap = 0
        count = self.search_datasets_limited(
            region, delay, universe, *args, limit=1, offset=offset, log=log, **kwargs
        ).json()['count']
        offsets = range(offset, count, limit)
        if log is not None:
            self.logger.info(f"{self}.search_datasets(...) [start {offsets}]: {log}")
        total = len(offsets)
        for idx, offset in enumerate(offsets, start=1):
            yield self.search_datasets_limited(
                region,
                delay,
                universe,
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
            self.logger.info(f"{self}.search_datasets(...) [finish {offsets}]: {log}")

    def locate_field(
        self,
        field_id: str,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        url = URL_DATAFIELDS_FIELDID.format(field_id)
        resp = self.get(url, *args, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.locate_field(...) [",
                        f"    {url}",
                        f"]: {log}",
                    )
                )
            )
        return resp

    def search_fields_limited(
        self,
        region: Region,
        delay: Delay,
        universe: Universe,
        *args,
        instrument_type: InstrumentType = EQUITY,
        dataset_id: str | None = None,
        search: str | None = None,
        category: DataCategory | None = None,
        theme: bool | None = None,
        coverage: FilterRange | None = None,
        type: FieldType | None = None,
        alpha_count: FilterRange | None = None,
        user_count: FilterRange | None = None,
        order: FieldsOrder | None = None,
        limit: int = 50,
        offset: int = 0,
        others: Iterable[str] | None = None,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        limit = min(max(limit, 1), 50)
        offset = min(max(offset, 0), 10000 - limit)
        params = [
            f"region={region}",
            f"delay={delay}",
            f"universe={universe}",
        ]
        params.append(f"instrumentType={instrument_type}")
        if dataset_id is not None:
            params.append(f"dataset.id={dataset_id}")
        if search is not None:
            params.append(f"search={search}")
        if category is not None:
            params.append(f"category={category}")
        if theme is not None:
            params.append(f"theme={'true' if theme else 'false'}")
        if coverage is not None:
            params.append(coverage.to_params('coverage'))
        if type is not None:
            params.append(f"type={type}")
        if alpha_count is not None:
            params.append(alpha_count.to_params('alphaCount'))
        if user_count is not None:
            params.append(user_count.to_params('userCount'))
        if order is not None:
            params.append(f"order={order}")
        params.append(f"limit={limit}")
        params.append(f"offset={offset}")
        if others is not None:
            params.extend(others)
        url = URL_DATAFIELDS + '?' + '&'.join(params)
        resp = self.get(url, *args, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.search_fields_limited(...) [",
                        f"    {url}",
                        f"]: {log}",
                    )
                )
            )
        return resp

    def search_fields(
        self,
        region: Region,
        delay: Delay,
        universe: Universe,
        *args,
        limit: int = 50,
        offset: int = 0,
        log: str | None = '',
        log_gap: int = 100,
        **kwargs,
    ) -> Generator[Response, None, None]:
        if log is None:
            log_gap = 0
        count = self.search_fields_limited(
            region, delay, universe, *args, limit=1, offset=offset, log=log, **kwargs
        ).json()['count']
        offsets = range(offset, count, limit)
        if log is not None:
            self.logger.info(f"{self}.search_fields(...) [start {offsets}]: {log}")
        total = len(offsets)
        for idx, offset in enumerate(offsets, start=1):
            yield self.search_fields_limited(
                region,
                delay,
                universe,
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
            self.logger.info(f"{self}.search_fields(...) [finish {offsets}]: {log}")
