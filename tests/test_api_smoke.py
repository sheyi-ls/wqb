#!/usr/bin/env python3
"""Smoke-test wqb APIs (excluding simulate)."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WQB_ROOT = Path(__file__).resolve().parents[1]
if str(WQB_ROOT) not in sys.path:
    sys.path.insert(0, str(WQB_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml

from wqb.api import FilterRange, WQBSession, build_regular_alpha, wqb_logger


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

    cfg_path = ROOT / "conf" / "config.yaml"
    if cfg_path.is_file():
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        acc = cfg.get("account") or {}
        email = acc.get("username")
        password = acc.get("password")
        if email and password:
            return str(email).strip(), str(password).strip()

    raise RuntimeError("no BRAIN credentials in env or conf/config.yaml")


def main() -> int:
    email, password = load_credentials()
    logger = wqb_logger(name="wqb-api-test")
    wqbs = WQBSession((email, password), logger=logger)

    results: list[tuple[str, bool, str]] = []
    alpha_id: str | None = None

    def record(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))
        mark = "PASS" if ok else "FAIL"
        line = f"[{mark}] {name}"
        if detail:
            line += f" — {detail}"
        print(line, flush=True)

    def run(name: str, fn):
        try:
            detail = fn() or ""
            record(name, True, str(detail) if detail else "")
        except Exception as exc:
            record(name, False, f"{type(exc).__name__}: {exc}")

    # --- session ---
    run("auth_request", lambda: f"status={wqbs.auth_request().status_code}")
    run("get_authentication", lambda: f"status={wqbs.get_authentication(log=None).status_code}")
    run("head_authentication", lambda: f"status={wqbs.head_authentication(log=None).status_code}")

    # --- catalog ---
    run(
        "search_operators",
        lambda: f"count={len(wqbs.search_operators(log=None).json())}",
    )
    run(
        "locate_dataset(pv1)",
        lambda: f"id={wqbs.locate_dataset('pv1', log=None).json().get('id')}",
    )
    run(
        "search_datasets_limited",
        lambda: (
            f"count={wqbs.search_datasets_limited('USA', 1, 'TOP3000', limit=5, log=None).json()['count']}"
        ),
    )
    run(
        "locate_field(open)",
        lambda: f"id={wqbs.locate_field('open', log=None).json().get('id')}",
    )
    run(
        "search_fields_limited",
        lambda: (
            f"count={wqbs.search_fields_limited('USA', 1, 'TOP3000', dataset_id='pv1', limit=5, log=None).json()['count']}"
        ),
    )

    # --- alpha query ---
    def filter_alphas():
        nonlocal alpha_id
        resp = wqbs.filter_alphas_limited(
            status="UNSUBMITTED",
            region="USA",
            delay=1,
            universe="TOP3000",
            limit=3,
            order="-dateCreated",
            log=None,
        )
        data = resp.json()
        items = data.get("results") or []
        if items:
            alpha_id = items[0]["id"]
        return f"count={data.get('count')} first={alpha_id}"

    run("filter_alphas_limited", filter_alphas)

    if alpha_id:

        def locate_alpha():
            body = wqbs.locate_alpha(alpha_id, log=None).json()
            is_metrics = body.get("is") or {}
            return f"sharpe={is_metrics.get('sharpe')} fitness={is_metrics.get('fitness')}"

        run(f"locate_alpha({alpha_id[:8]}…)", locate_alpha)

        run(
            "locate_alpha_brief",
            lambda: f"keys={list(wqbs.locate_alpha_brief(alpha_id, log=None).keys())}",
        )

        def test_pnl():
            body = wqbs.get_pnl(alpha_id, log=None).json()
            records = body.get("records") or []
            schema = (body.get("schema") or {}).get("properties") or []
            names = [p.get("name") for p in schema]
            return f"records={len(records)} cols={names}"

        run("get_pnl", test_pnl)

        def test_yearly_stats():
            body = wqbs.get_yearly_stats(alpha_id, log=None).json()
            records = body.get("records") or []
            schema = (body.get("schema") or {}).get("properties") or []
            names = [p.get("name") for p in schema]
            return f"records={len(records)} cols={names}"

        run("get_yearly_stats", test_yearly_stats)

        async def run_check():
            resp = await wqbs.check(alpha_id, log=None)
            if resp is None:
                return "resp=None"
            return f"status={resp.status_code}"

        run(
            "check",
            lambda: asyncio.run(run_check()),
        )

        run(
            "sc_check",
            lambda: (
                lambda r: f"max={r.get('max_correlation')} pass={r.get('passes_check')}"
            )(wqbs.sc_check(alpha_id, refresh_os_pool=True, log=None)),
        )

        run(
            "ppac_check",
            lambda: (
                lambda r: f"ppac={r.get('ppac_correlation')} pass={r.get('passes_check')} pool={r.get('pool_size')}"
            )(wqbs.ppac_check(alpha_id, refresh_os_pool=False, log=None)),
        )

        def test_sc_batch():
            resp = wqbs.filter_alphas_limited(
                status="UNSUBMITTED",
                region="USA",
                delay=1,
                universe="TOP3000",
                limit=2,
                order="-dateCreated",
                log=None,
            )
            ids = [a["id"] for a in (resp.json().get("results") or [])[:2]]
            if not ids:
                ids = [alpha_id]
            rows = wqbs.sc_check_batch(
                ids,
                workers=2,
                refresh_os_pool=False,
                log=None,
            )
            return f"n={len(rows)} workers=2"

        run("sc_check_batch", test_sc_batch)

        run(
            "ppac_check_batch",
            lambda: (
                lambda rows: f"n={len(rows)}"
            )(
                wqbs.ppac_check_batch(
                    [alpha_id],
                    workers=1,
                    refresh_os_pool=False,
                    log=None,
                )
            ),
        )

        run(
            "pc_check",
            lambda: (
                lambda r: f"status={r.get('status')} max={r.get('max_correlation')}"
            )(
                wqbs.pc_check(
                    alpha_id,
                    max_wait_seconds=120,
                    poll_interval=10,
                    log=None,
                )
            ),
        )
    else:
        for name in (
            "locate_alpha",
            "locate_alpha_brief",
            "get_pnl",
            "get_yearly_stats",
            "check",
            "sc_check",
            "ppac_check",
            "sc_check_batch",
            "ppac_check_batch",
            "pc_check",
        ):
            record(name, False, "skipped: no alpha_id from filter")

    # patch: read favorite then set back (no net change if already false)
    if alpha_id:
        def patch_roundtrip():
            before = wqbs.locate_alpha(alpha_id, log=None).json().get("favorite", False)
            wqbs.patch_properties(alpha_id, favorite=before, log=None)
            return f"favorite={before} (unchanged)"

        run("patch_properties", patch_roundtrip)

    # --- helpers (non-HTTP) ---
    run(
        "build_regular_alpha",
        lambda: f"type={build_regular_alpha('rank(close)').get('type')}",
    )
    run(
        "FilterRange",
        lambda: FilterRange.from_str("[1, inf)").to_params("is.sharpe"),
    )

    # --- summary ---
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{passed}/{len(results)} passed, {failed} failed", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
