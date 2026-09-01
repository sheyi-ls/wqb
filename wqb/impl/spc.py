"""SPC competition HTTP implementation."""
from pathlib import Path
from typing import Any

from requests import Response

from ..common.spc import (
    SpcSubmissionDraft,
    discover_submission_markdowns,
    parse_submission_markdown,
)
from ..common.urls import URL_SPC_SUBMISSIONS

__all__ = ['SpcMixin']


class SpcMixin:
    def list_spc_submissions(
        self,
        *args,
        limit: int = 50,
        offset: int = 0,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        url = URL_SPC_SUBMISSIONS
        params = {'limit': limit, 'offset': offset}
        resp = self.get(url, params=params, *args, **kwargs)
        if log is not None:
            self.logger.info(f"{self}.list_spc_submissions(...) [{url}]: {log}")
        return resp

    def list_all_spc_submissions(
        self,
        *args,
        limit: int = 50,
        log: str | None = '',
        **kwargs,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        offset = 0
        while True:
            resp = self.list_spc_submissions(
                *args,
                limit=limit,
                offset=offset,
                log=None,
                **kwargs,
            )
            resp.raise_for_status()
            payload = resp.json()
            batch = payload.get('results') or payload.get('items') or []
            if not batch:
                break
            results.extend(batch)
            if len(batch) < limit:
                break
            offset += limit
        if log is not None:
            self.logger.info(
                f"{self}.list_all_spc_submissions(...) [count={len(results)}]: {log}"
            )
        return results

    def create_spc_submission(
        self,
        payload: dict[str, Any],
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        resp = self.post(URL_SPC_SUBMISSIONS, json=payload, *args, **kwargs)
        if log is not None:
            self.logger.info(
                f"{self}.create_spc_submission(...) [{payload.get('name')!r}]: {log}"
            )
        return resp

    def patch_spc_submission(
        self,
        submission_id: str,
        payload: dict[str, Any],
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        url = f'{URL_SPC_SUBMISSIONS}/{submission_id}'
        resp = self.patch(url, json=payload, *args, **kwargs)
        if log is not None:
            self.logger.info(f"{self}.patch_spc_submission(...) [{url}]: {log}")
        return resp

    def zero_spc_submission(
        self,
        submission_id: str,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response | None:
        for sub in self.list_all_spc_submissions(*args, log=None, **kwargs):
            if str(sub.get('id')) != str(submission_id):
                continue
            if float(sub.get('weight') or 0) == 0:
                if log is not None:
                    self.logger.info(
                        f"{self}.zero_spc_submission(...) [already 0 id={submission_id}]: {log}"
                    )
                return None
            return self.patch_spc_submission(
                submission_id,
                {'weight': 0},
                *args,
                log=log,
                **kwargs,
            )
        raise ValueError(f'SPC submission not found: {submission_id}')

    def zero_all_spc_submissions(
        self,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> list[dict[str, Any]]:
        updated: list[dict[str, Any]] = []
        for sub in self.list_all_spc_submissions(*args, log=None, **kwargs):
            sub_id = sub.get('id')
            if sub_id is None:
                continue
            if float(sub.get('weight') or 0) == 0:
                continue
            self.patch_spc_submission(str(sub_id), {'weight': 0}, *args, log=None, **kwargs)
            updated.append(sub)
        if log is not None:
            self.logger.info(
                f"{self}.zero_all_spc_submissions(...) [zeroed={len(updated)}]: {log}"
            )
        return updated

    def submit_spc_markdown(
        self,
        path: Path | str,
        date_suffix: str,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> dict[str, Any]:
        draft = parse_submission_markdown(path, date_suffix)
        resp = self.create_spc_submission(draft.to_payload(), *args, log=log, **kwargs)
        resp.raise_for_status()
        body = resp.json()
        return {
            'source_file': str(draft.source_file),
            'name': draft.name,
            'submission': body,
        }

    def submit_spc_dir(
        self,
        spc_dir: Path | str,
        date_suffix: str,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for path in discover_submission_markdowns(spc_dir):
            results.append(
                self.submit_spc_markdown(path, date_suffix, *args, log=log, **kwargs)
            )
        return results

    def deploy_spc(
        self,
        spc_dir: Path | str,
        date_suffix: str,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> dict[str, Any]:
        zeroed = self.zero_all_spc_submissions(*args, log=log, **kwargs)
        created = self.submit_spc_dir(spc_dir, date_suffix, *args, log=log, **kwargs)
        return {'zeroed': zeroed, 'created': created}
