"""SPC competition API."""
from pathlib import Path
from typing import Any, Protocol

from requests import Response

from ..common.spc import SpcSubmissionDraft

__all__ = ['SpcAPI']


class SpcAPI(Protocol):
    def list_spc_submissions(
        self,
        *args,
        limit: int = 50,
        offset: int = 0,
        log: str | None = '',
        **kwargs,
    ) -> Response: ...

    def list_all_spc_submissions(
        self,
        *args,
        limit: int = 50,
        log: str | None = '',
        **kwargs,
    ) -> list[dict[str, Any]]: ...

    def create_spc_submission(
        self,
        payload: dict[str, Any],
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response: ...

    def patch_spc_submission(
        self,
        submission_id: str,
        payload: dict[str, Any],
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response: ...

    def zero_spc_submission(
        self,
        submission_id: str,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response | None: ...

    def zero_all_spc_submissions(
        self,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> list[dict[str, Any]]: ...

    def submit_spc_markdown(
        self,
        path: Path | str,
        date_suffix: str,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> dict[str, Any]: ...

    def submit_spc_dir(
        self,
        spc_dir: Path | str,
        date_suffix: str,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> list[dict[str, Any]]: ...

    def deploy_spc(
        self,
        spc_dir: Path | str,
        date_suffix: str,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> dict[str, Any]: ...
