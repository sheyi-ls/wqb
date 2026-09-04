#!/usr/bin/env python3
"""
Smoke-test installed wqb + wqb.tools (see docs/capability-roadmap.md).

Confirms the wheel/venv install under site-packages — never adds the wqb source tree
to sys.path.

Sections map to capability-roadmap.md:
  install / helpers / session / catalog / alpha / simulation / spc  → wqb (wqb.api)
  tools.expr / tools.correlation / tools.analysis                    → wqb.tools.*

Excluded (submission / destructive SPC writes):
  WQBSession.submit
  create_spc_submission / patch_spc_submission / zero_spc_* / submit_spc_* / deploy_spc

Credentials: BRAIN_EMAIL + BRAIN_PASSWORD env vars, or conf/config.yaml in monorepo root.

Usage:
  source .venv/bin/activate
  python wqb/scripts/test_installed_capabilities.py
  python wqb/scripts/test_installed_capabilities.py --skip-simulate
  WQB_SKIP_SIMULATE=1 python wqb/scripts/test_installed_capabilities.py
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

import wqb as wqb_pkg
import yaml

from wqb.api import (
    DatetimeRange,
    FilterRange,
    WQBSession,
    build_regular_alpha,
    coerce_multi_targets,
    compact_sample_output,
    discover_submission_markdowns,
    parse_submission_markdown,
    simulation_ref_url,
    to_multi_alphas,
    wqb_logger,
)
from wqb.tools.analysis.api import default_monthly_submit_analysis
from wqb.tools.correlation.api import default_pnl_correlation
from wqb.tools.expr.api import (
    default_expression_analyze,
    default_expression_transform,
    default_expression_validate,
    parse_program,
    validation_result_to_dict,
)

EXPR = (
    "st1 = ts_zscore(ts_backfill(star_val_dividend_projection_fy12, 60), 250);"
    "group_scale(st1, sector)"
)
SIMPLE_EXPRS = ("rank(close)", "rank(open)")


@dataclass
class Case:
    section: str
    name: str
    fn: Callable[[], str]
    skip: bool = False
    skip_reason: str = ""


@dataclass
class Runner:
    wqbs: WQBSession
    alpha_ids: list[str] = field(default_factory=list)
    pnl_by_alpha: dict[str, dict] = field(default_factory=dict)
    results: list[tuple[str, str, bool, str, bool]] = field(default_factory=list)

    def record(self, section: str, name: str, ok: bool, detail: str = "", *, skipped: bool = False) -> None:
        self.results.append((section, name, ok, detail, skipped))
        if skipped:
            mark = "SKIP"
        else:
            mark = "PASS" if ok else "FAIL"
        line = f"[{mark}] {section} :: {name}"
        if detail:
            line += f" — {detail}"
        print(line, flush=True)

    def run(self, case: Case) -> None:
        if case.skip:
            self.record(case.section, case.name, True, case.skip_reason, skipped=True)
            return
        try:
            detail = case.fn() or ""
            self.record(case.section, case.name, True, str(detail))
        except Exception as exc:
            self.record(case.section, case.name, False, f"{type(exc).__name__}: {exc}")

    def ensure_alpha_ids(self, limit: int = 3) -> list[str]:
        if self.alpha_ids:
            return self.alpha_ids
        resp = self.wqbs.filter_alphas_limited(
            status="UNSUBMITTED",
            region="USA",
            delay=1,
            universe="TOP3000",
            limit=limit,
            order="-dateCreated",
            log=None,
        )
        items = resp.json().get("results") or []
        self.alpha_ids = [a["id"] for a in items if a.get("id")]
        return self.alpha_ids

    def ensure_pnl(self, alpha_id: str) -> dict:
        if alpha_id not in self.pnl_by_alpha:
            self.pnl_by_alpha[alpha_id] = self.wqbs.get_pnl(alpha_id, log=None).json()
        return self.pnl_by_alpha[alpha_id]


def _installed_wqb_path() -> str:
    spec = importlib.util.find_spec("wqb")
    return spec.origin if spec and spec.origin else "unknown"


def _assert_site_packages_install() -> str:
    origin = _installed_wqb_path()
    if "site-packages" not in origin.replace("\\", "/"):
        raise RuntimeError(
            f"wqb not loaded from site-packages (got {origin}); "
            "reinstall with: pip install dist/wqb-*.whl[correlation]"
        )
    return origin


def find_monorepo_root() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / "conf" / "config.yaml").is_file():
            return parent
    return None


def load_credentials() -> tuple[str, str]:
    email = (
        os.environ.get("BRAIN_USER")
        or os.environ.get("BRAIN_EMAIL")
        or os.environ.get("WQ_BRAIN_EMAIL")
        or os.environ.get("BRAIN_CREDENTIAL_EMAIL")
    )
    password = (
        os.environ.get("BRAIN_PASSWORD")
        or os.environ.get("WQ_BRAIN_PASSWORD")
        or os.environ.get("BRAIN_CREDENTIAL_PASSWORD")
    )
    if email and password:
        return email.strip(), password.strip()

    root = find_monorepo_root()
    if root is not None:
        cfg = yaml.safe_load((root / "conf" / "config.yaml").read_text(encoding="utf-8")) or {}
        acc = cfg.get("account") or {}
        email = acc.get("username")
        password = acc.get("password")
        if email and password:
            return str(email).strip(), str(password).strip()

    raise RuntimeError(
        "no BRAIN credentials: set BRAIN_EMAIL/BRAIN_PASSWORD or conf/config.yaml"
    )


def find_spc_markdown() -> Path | None:
    root = find_monorepo_root()
    if root is None:
        return None
    spc_dir = root / "competitions/ Systematic Predictions Challenge/submissions_50"
    if not spc_dir.is_dir():
        return None
    files = discover_submission_markdowns(spc_dir)
    return files[0] if files else None


def build_cases(runner: Runner, *, skip_simulate: bool) -> list[Case]:
    wqbs = runner.wqbs
    cases: list[Case] = []

    # --- install metadata ---
    cases.append(
        Case(
            "install",
            "site_packages_install",
            lambda: _assert_site_packages_install(),
        )
    )
    cases.append(
        Case(
            "install",
            "package_version",
            lambda: f"version={wqb_pkg.__version__}",
        )
    )

    # --- helpers (offline) ---
    cases.extend(
        [
            Case(
                "helpers",
                "build_regular_alpha",
                lambda: f"type={build_regular_alpha('rank(close)').get('type')}",
            ),
            Case(
                "helpers",
                "FilterRange",
                lambda: str(FilterRange.from_str("[1, inf)").to_params("is.sharpe")),
            ),
            Case(
                "helpers",
                "DatetimeRange",
                lambda: f"len={len(DatetimeRange(datetime(2024, 1, 1), datetime(2024, 1, 4), timedelta(days=1)))}",
            ),
            Case(
                "helpers",
                "to_multi_alphas",
                lambda: f"groups={len(list(to_multi_alphas([build_regular_alpha(e) for e in SIMPLE_EXPRS], 2)))}",
            ),
            Case(
                "helpers",
                "coerce_multi_targets",
                lambda: f"n={len(coerce_multi_targets(SIMPLE_EXPRS))}",
            ),
            Case(
                "helpers",
                "simulation_ref_url",
                lambda: simulation_ref_url("abc123"),
            ),
        ]
    )

    # --- wqb.tools.expr (offline) ---
    cases.extend(
        [
            Case(
                "tools.expr",
                "validate_expression (offline)",
                lambda: (
                    lambda r: f"valid={r.is_valid} errors={len(r.errors)}"
                )(default_expression_validate.validate_expression(EXPR, check_fields=False)),
            ),
            Case(
                "tools.expr",
                "validate_expression_batch",
                lambda: f"n={len(default_expression_validate.validate_expression_batch([EXPR, 'rank(close)', 'bad(!!!'], check_fields=False))}",
            ),
            Case(
                "tools.expr",
                "validate_expression_batch_json",
                lambda: (
                    lambda p: f"valid={p['valid_count']}/{p['total']}"
                )(
                    default_expression_validate.validate_expression_batch_json(
                        [EXPR, "rank(close)"], check_fields=False
                    )
                ),
            ),
            Case(
                "tools.expr",
                "validation_result_to_dict",
                lambda: str(
                    validation_result_to_dict(
                        default_expression_validate.validate_expression(
                            "rank(close)", check_fields=False
                        )
                    ).keys()
                ),
            ),
            Case(
                "tools.expr",
                "analyze_expression",
                lambda: (
                    lambda s: f"ops={s.unique_operator_count} fields={s.unique_field_count}"
                )(default_expression_analyze.analyze_expression(EXPR)),
            ),
            Case(
                "tools.expr",
                "count_unique_operators",
                lambda: f"n={default_expression_analyze.count_unique_operators(EXPR)}",
            ),
            Case(
                "tools.expr",
                "count_unique_fields",
                lambda: f"n={default_expression_analyze.count_unique_fields(EXPR)}",
            ),
            Case(
                "tools.expr",
                "extract_window_slots / apply_window_values",
                lambda: _test_window_slots(),
            ),
            Case(
                "tools.expr",
                "program_to_expression",
                lambda: _test_program_roundtrip(),
            ),
            Case(
                "tools.expr",
                "parse_program",
                lambda: f"stmts={len(parse_program('a = rank(close); rank(a)').statements)}",
            ),
        ]
    )

    # --- session ---
    cases.extend(
        [
            Case(
                "session",
                "auth_request",
                lambda: f"status={wqbs.auth_request(log=None).status_code}",
            ),
            Case(
                "session",
                "get_authentication",
                lambda: f"status={wqbs.get_authentication(log=None).status_code}",
            ),
            Case(
                "session",
                "head_authentication",
                lambda: f"status={wqbs.head_authentication(log=None).status_code}",
            ),
            Case(
                "session",
                "post_authentication",
                lambda: f"status={wqbs.post_authentication(log=None).status_code}",
            ),
            Case(
                "session",
                "delete_authentication + re-auth",
                lambda: _test_delete_and_reauth(wqbs),
            ),
        ]
    )

    # --- catalog ---
    cases.extend(
        [
            Case(
                "catalog",
                "search_operators",
                lambda: f"count={len(wqbs.search_operators(log=None).json())}",
            ),
            Case(
                "catalog",
                "locate_dataset",
                lambda: f"id={wqbs.locate_dataset('pv1', log=None).json().get('id')}",
            ),
            Case(
                "catalog",
                "search_datasets_limited",
                lambda: f"count={wqbs.search_datasets_limited('USA', 1, 'TOP3000', limit=5, log=None).json()['count']}",
            ),
            Case(
                "catalog",
                "search_datasets (first page)",
                lambda: _first_iterator_item(
                    wqbs.search_datasets("USA", 1, "TOP3000", limit=5, log=None),
                    key="id",
                ),
            ),
            Case(
                "catalog",
                "locate_field",
                lambda: f"id={wqbs.locate_field('open', log=None).json().get('id')}",
            ),
            Case(
                "catalog",
                "search_fields_limited",
                lambda: f"count={wqbs.search_fields_limited('USA', 1, 'TOP3000', dataset_id='pv1', limit=5, log=None).json()['count']}",
            ),
            Case(
                "catalog",
                "search_fields (first page)",
                lambda: _first_iterator_item(
                    wqbs.search_fields(
                        "USA", 1, "TOP3000", dataset_id="pv1", limit=5, log=None
                    ),
                    key="id",
                ),
            ),
        ]
    )

    # --- alpha query ---
    cases.append(
        Case(
            "alpha",
            "filter_alphas_limited",
            lambda: _test_filter_limited(runner),
        )
    )
    cases.append(
        Case(
            "alpha",
            "filter_alphas (first page)",
            lambda: _test_filter_iterator(runner),
        )
    )
    for name, fn in (
        ("locate_alpha", lambda: _test_locate_alpha(runner)),
        ("locate_alpha_brief", lambda: _test_locate_brief(runner)),
        ("get_pnl", lambda: _test_get_pnl(runner)),
        ("get_yearly_stats", lambda: _test_get_yearly(runner)),
        ("check", lambda: asyncio.run(_test_check(runner))),
        ("concurrent_check", lambda: asyncio.run(_test_concurrent_check(runner))),
        ("sc_check", lambda: _test_sc_check(runner)),
        ("sc_check_batch", lambda: _test_sc_batch(runner)),
        ("ppac_check", lambda: _test_ppac_check(runner)),
        ("ppac_check_batch", lambda: _test_ppac_batch(runner)),
        ("pc_check", lambda: _test_pc_check(runner)),
        ("patch_properties", lambda: _test_patch_roundtrip(runner)),
    ):
        cases.append(Case("alpha", name, fn, skip=not runner.alpha_ids, skip_reason="no alpha_id"))

    # --- tools.expr online field check ---
    cases.append(
        Case(
            "tools.expr",
            "validate_expression (check_fields)",
            lambda: (
                lambda r: f"valid={r.is_valid} errors={len(r.errors)}"
            )(
                default_expression_validate.validate_expression(
                    "rank(close)", check_fields=True, session=wqbs
                )
            ),
        )
    )

    # --- tools.correlation ---
    for name, fn in (
        ("corr_between_alphas", lambda: _test_corr_between_alphas(runner)),
        ("corr_between_pnls", lambda: _test_corr_between_pnls(runner)),
        ("corr_matrix_alphas", lambda: _test_corr_matrix_alphas(runner)),
        ("corr_matrix_pnls", lambda: _test_corr_matrix_pnls(runner)),
    ):
        cases.append(
            Case(
                "tools.correlation",
                name,
                fn,
                skip=len(runner.alpha_ids) < 2,
                skip_reason="need >=2 alpha_ids",
            )
        )

    # --- tools.analysis ---
    cases.extend(
        [
            Case(
                "tools.analysis",
                "aggregate_month_region (offline)",
                lambda: _test_aggregate_month_region(),
            ),
            Case(
                "tools.analysis",
                "monthly_submit_count_by_region_json",
                lambda: _test_monthly_submit_json(wqbs),
            ),
            Case(
                "tools.analysis",
                "format_pivot_table",
                lambda: f"lines={len(default_monthly_submit_analysis.format_pivot_table(_mini_monthly_result()).splitlines())}",
            ),
        ]
    )

    # --- simulation ---
    sim_skip = skip_simulate
    cases.extend(
        [
            Case(
                "simulation",
                "simulate",
                lambda: asyncio.run(_test_simulate(wqbs)),
                skip=sim_skip,
                skip_reason="--skip-simulate",
            ),
            Case(
                "simulation",
                "multi_simulate",
                lambda: asyncio.run(_test_multi_simulate(wqbs)),
                skip=sim_skip,
                skip_reason="--skip-simulate",
            ),
            Case(
                "simulation",
                "concurrent_simulate",
                lambda: asyncio.run(_test_concurrent_simulate(wqbs)),
                skip=sim_skip,
                skip_reason="--skip-simulate",
            ),
        ]
    )

    # --- SPC read-only ---
    md = find_spc_markdown()
    cases.extend(
        [
            Case(
                "spc",
                "list_spc_submissions",
                lambda: f"status={wqbs.list_spc_submissions(limit=5, log=None).status_code}",
            ),
            Case(
                "spc",
                "list_all_spc_submissions",
                lambda: f"count={len(wqbs.list_all_spc_submissions(log=None))}",
            ),
            Case(
                "spc",
                "parse_submission_markdown",
                lambda: _test_parse_spc_md(md),
                skip=md is None,
                skip_reason="no SPC markdown in monorepo",
            ),
            Case(
                "spc",
                "discover_submission_markdowns",
                lambda: _test_discover_spc_markdowns(),
                skip=find_monorepo_root() is None,
                skip_reason="monorepo root not found",
            ),
            Case(
                "spc",
                "compact_sample_output",
                lambda: f"len={len(compact_sample_output('{\"US1234567890|ABCD\": 0.1}'))}",
            ),
        ]
    )

    return cases


def _test_window_slots() -> str:
    slots = default_expression_transform.extract_window_slots(EXPR)
    ts_slots = [s for s in slots if s.value == 250]
    if not ts_slots:
        raise AssertionError("expected ts window slot 250")
    patched = default_expression_transform.apply_window_values(EXPR, {ts_slots[0].slot_id: 120})
    return f"slots={len(slots)} patched_has_120={'120' in patched}"


def _test_program_roundtrip() -> str:
    program = parse_program(EXPR)
    text = default_expression_transform.program_to_expression(program)
    return f"len={len(text)} has_group_scale={'group_scale' in text}"


def _first_iterator_item(pages, *, key: str) -> str:
    first = next(iter(pages))
    body = first.json()
    results = body.get("results") or []
    if not results:
        return "empty page"
    return f"{key}={results[0].get(key)}"


def _test_filter_limited(runner: Runner) -> str:
    ids = runner.ensure_alpha_ids()
    return f"count={len(ids)} first={ids[0] if ids else None}"


def _test_filter_iterator(runner: Runner) -> str:
    resp = next(
        iter(
            runner.wqbs.filter_alphas(
                status="UNSUBMITTED",
                region="USA",
                delay=1,
                universe="TOP3000",
                limit=3,
                order="-dateCreated",
                log=None,
            )
        )
    )
    n = len(resp.json().get("results") or [])
    return f"page_results={n}"


def _alpha_id(runner: Runner, idx: int = 0) -> str:
    ids = runner.ensure_alpha_ids()
    if not ids:
        raise RuntimeError("no alpha_id")
    return ids[idx]


def _test_locate_alpha(runner: Runner) -> str:
    aid = _alpha_id(runner)
    body = runner.wqbs.locate_alpha(aid, log=None).json()
    metrics = body.get("is") or {}
    return f"id={aid[:8]}… sharpe={metrics.get('sharpe')}"


def _test_locate_brief(runner: Runner) -> str:
    aid = _alpha_id(runner)
    brief = runner.wqbs.locate_alpha_brief(aid, log=None)
    return f"keys={sorted(brief.keys())[:5]}…"


def _test_get_pnl(runner: Runner) -> str:
    aid = _alpha_id(runner)
    body = runner.ensure_pnl(aid)
    return f"records={len(body.get('records') or [])}"


def _test_get_yearly(runner: Runner) -> str:
    aid = _alpha_id(runner)
    body = runner.wqbs.get_yearly_stats(aid, log=None).json()
    return f"records={len(body.get('records') or [])}"


async def _test_check(runner: Runner) -> str:
    aid = _alpha_id(runner)
    resp = await runner.wqbs.check(aid, log=None)
    return f"status={resp.status_code if resp else None}"


async def _test_concurrent_check(runner: Runner) -> str:
    ids = runner.ensure_alpha_ids()[:2]
    rows = await runner.wqbs.concurrent_check(ids, concurrency=2, log=None)
    codes = [
        r.status_code if hasattr(r, "status_code") else type(r).__name__ for r in rows
    ]
    return f"n={len(rows)} statuses={codes}"


def _test_sc_check(runner: Runner) -> str:
    aid = _alpha_id(runner)
    r = runner.wqbs.sc_check(aid, refresh_os_pool=False, log=None)
    return f"max={r.get('max_correlation')} pass={r.get('passes_check')}"


def _test_sc_batch(runner: Runner) -> str:
    ids = runner.ensure_alpha_ids()[:2] or [_alpha_id(runner)]
    rows = runner.wqbs.sc_check_batch(ids, workers=2, refresh_os_pool=False, log=None)
    return f"n={len(rows)}"


def _test_ppac_check(runner: Runner) -> str:
    aid = _alpha_id(runner)
    r = runner.wqbs.ppac_check(aid, refresh_os_pool=False, log=None)
    return f"ppac={r.get('ppac_correlation')} pass={r.get('passes_check')}"


def _test_ppac_batch(runner: Runner) -> str:
    aid = _alpha_id(runner)
    rows = runner.wqbs.ppac_check_batch([aid], workers=1, refresh_os_pool=False, log=None)
    return f"n={len(rows)}"


def _test_pc_check(runner: Runner) -> str:
    aid = _alpha_id(runner)
    r = runner.wqbs.pc_check(
        aid,
        max_wait_seconds=120,
        poll_interval=10,
        log=None,
    )
    return f"status={r.get('status')} max={r.get('max_correlation')}"


def _test_patch_roundtrip(runner: Runner) -> str:
    aid = _alpha_id(runner)
    before = runner.wqbs.locate_alpha(aid, log=None).json().get("favorite", False)
    runner.wqbs.patch_properties(aid, favorite=before, log=None)
    return f"favorite={before} unchanged"


def _test_corr_between_alphas(runner: Runner) -> str:
    a, b = runner.ensure_alpha_ids()[:2]
    corr = default_pnl_correlation.corr_between_alphas(
        runner.wqbs, a, b, years=4, log=None
    )
    return f"corr={corr:.4f}"


def _test_corr_between_pnls(runner: Runner) -> str:
    a, b = runner.ensure_alpha_ids()[:2]
    pnl_a = runner.ensure_pnl(a)
    pnl_b = runner.ensure_pnl(b)
    corr = default_pnl_correlation.corr_between_pnls(pnl_a, pnl_b, years=4)
    return f"corr={corr:.4f}"


def _test_corr_matrix_alphas(runner: Runner) -> str:
    ids = runner.ensure_alpha_ids()[:3]
    result = default_pnl_correlation.corr_matrix_alphas(
        runner.wqbs, ids, years=4, workers=2, log=None
    )
    return f"labels={len(result.labels)} skipped={len(result.skipped)}"


def _test_corr_matrix_pnls(runner: Runner) -> str:
    ids = runner.ensure_alpha_ids()[:2]
    pnls = [runner.ensure_pnl(i) for i in ids]
    result = default_pnl_correlation.corr_matrix_pnls(
        pnls, names=ids, years=4, workers=2
    )
    return f"labels={len(result.labels)} obs={result.observations}"


def _mini_monthly_result() -> dict[str, Any]:
    return {
        "months": ["2025-12"],
        "regions": ["USA"],
        "pivot": {"2025-12": {"USA": {"count": 1, "super_count": 0}}},
        "grand_total": {"count": 1, "super_count": 0},
    }


def _test_aggregate_month_region() -> str:
    rows = [
        {
            "id": "a1",
            "type": "REGULAR",
            "dateSubmitted": "2025-12-15T12:00:00Z",
            "region": "USA",
        }
    ]
    out = default_monthly_submit_analysis.aggregate_month_region(rows)
    json.dumps(out)
    return f"months={out['months']} total={out['grand_total']['count']}"


def _test_monthly_submit_json(wqbs: WQBSession) -> str:
    out = default_monthly_submit_analysis.monthly_submit_count_by_region_json(
        wqbs,
        start_date="2025-12-01",
        max_alphas=100,
        page_size=50,
        request_delay=0.2,
    )
    json.dumps(out)
    return f"total={out.get('total_alphas')} months={len(out.get('months') or [])}"


def _test_parse_spc_md(md: Path | None) -> str:
    assert md is not None
    draft = parse_submission_markdown(md, "cap-test")
    payload = draft.to_payload()
    return f"name={payload['name']!r} keys={sorted(payload.keys())}"


def _test_discover_spc_markdowns() -> str:
    root = find_monorepo_root()
    assert root is not None
    spc_dir = root / "competitions/ Systematic Predictions Challenge/submissions_50"
    files = discover_submission_markdowns(spc_dir) if spc_dir.is_dir() else []
    return f"count={len(files)}"


def _test_delete_and_reauth(wqbs: WQBSession) -> str:
    deleted = wqbs.delete_authentication(log=None).status_code
    reauth = wqbs.post_authentication(log=None).status_code
    return f"delete={deleted} reauth={reauth}"


async def _test_simulate(wqbs: WQBSession) -> str:
    target = build_regular_alpha("rank(close)", decay=0)
    resp = await wqbs.simulate(target, log=None)
    if resp is None:
        raise RuntimeError("simulate returned None")
    return f"status={resp.status_code}"


async def _test_multi_simulate(wqbs: WQBSession) -> str:
    result = await wqbs.multi_simulate(
        list(SIMPLE_EXPRS),
        settings={"decay": 0},
        fetch_alpha_details=False,
        log=None,
    )
    if result is None:
        raise RuntimeError("multi_simulate returned None")
    children = result.get("children") or []
    return f"children={len(children)}"


async def _test_concurrent_simulate(wqbs: WQBSession) -> str:
    targets = [build_regular_alpha(e, decay=0) for e in SIMPLE_EXPRS]
    rows = await wqbs.concurrent_simulate(targets, concurrency=2, log=None)
    codes = [
        r.status_code if hasattr(r, "status_code") else type(r).__name__ for r in rows
    ]
    return f"n={len(rows)} statuses={codes}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-simulate",
        action="store_true",
        help="skip simulate / multi_simulate / concurrent_simulate (slow)",
    )
    args = parser.parse_args()
    skip_simulate = args.skip_simulate or os.environ.get("WQB_SKIP_SIMULATE") == "1"

    email, password = load_credentials()
    logger = wqb_logger(name="wqb-capability-test")
    wqbs = WQBSession((email, password), logger=logger)

    runner = Runner(wqbs=wqbs)
    wqbs.auth_request(log=None)
    runner.ensure_alpha_ids()

    cases = build_cases(runner, skip_simulate=skip_simulate)

    print(f"wqb {wqb_pkg.__version__} @ {_installed_wqb_path()}", flush=True)
    print(f"cases={len(cases)} skip_simulate={skip_simulate}\n", flush=True)

    current_section = ""
    for case in cases:
        if case.section != current_section:
            current_section = case.section
            print(f"\n== {current_section} ==", flush=True)
        runner.run(case)

    passed = sum(1 for _, _, ok, _, skipped in runner.results if ok and not skipped)
    skipped = sum(1 for _, _, _, _, skipped in runner.results if skipped)
    failed = sum(1 for _, _, ok, _, skipped in runner.results if not ok and not skipped)
    print(
        f"\n{passed} passed, {skipped} skipped, {failed} failed "
        f"(total {len(runner.results)})",
        flush=True,
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
