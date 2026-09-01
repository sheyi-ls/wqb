"""Data catalog API."""
from collections.abc import Generator, Iterable
from typing import Protocol

from requests import Response

from ..common.filter_range import FilterRange
from ..common.constants import (
    Region,
    Delay,
    Universe,
    InstrumentType,
    DataCategory,
    FieldType,
    DatasetsOrder,
    FieldsOrder,
)

__all__ = ['CatalogAPI']


class CatalogAPI(Protocol):
    def search_operators(self, *args, log: str | None = '', **kwargs) -> Response: ...

    def locate_dataset(self, dataset_id: str, *args, log: str | None = '', **kwargs) -> Response: ...

    def search_datasets_limited(
        self,
        region: Region,
        delay: Delay,
        universe: Universe,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response: ...

    def search_datasets(
        self,
        region: Region,
        delay: Delay,
        universe: Universe,
        *args,
        log: str | None = '',
        log_gap: int = 100,
        **kwargs,
    ) -> Generator[Response, None, None]: ...

    def locate_field(self, field_id: str, *args, log: str | None = '', **kwargs) -> Response: ...

    def search_fields_limited(
        self,
        region: Region,
        delay: Delay,
        universe: Universe,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response: ...

    def search_fields(
        self,
        region: Region,
        delay: Delay,
        universe: Universe,
        *args,
        log: str | None = '',
        log_gap: int = 100,
        **kwargs,
    ) -> Generator[Response, None, None]: ...
