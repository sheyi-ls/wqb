#!/usr/bin/env python3
"""SPC API integration test: list + parse + optional single submit (never zero existing)."""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WQB_ROOT = Path(__file__).resolve().parents[1]
if str(WQB_ROOT) not in sys.path:
    sys.path.insert(0, str(WQB_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml
from requests import HTTPError

from wqb.api import WQBSession, parse_submission_markdown


def load_credentials() -> tuple[str, str]:
    email = os.environ.get("BRAIN_USER") or os.environ.get("WQ_BRAIN_EMAIL")
    password = os.environ.get("BRAIN_PASSWORD") or os.environ.get("WQ_BRAIN_PASSWORD")
    if email and password:
        return email.strip(), password.strip()
    cfg = yaml.safe_load((ROOT / "conf" / "config.yaml").read_text(encoding="utf-8"))
    acc = cfg["account"]
    return str(acc["username"]).strip(), str(acc["password"]).strip()


def snapshot_weights(subs: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for s in subs:
        sid = s.get("id")
        if sid is not None:
            out[str(sid)] = float(s.get("weight") or 0)
    return out


def main() -> int:
    email, password = load_credentials()
    wqbs = WQBSession((email, password))

    md_path = (
        ROOT
        / "competitions/ Systematic Predictions Challenge/submissions_50"
        / "SPC Submission V06 - Short Term Reversal Quality Gate.md"
    )
    date_suffix = f"wqb-test-{datetime.now().strftime('%y%m%d')}"

    before = wqbs.list_all_spc_submissions(log=None)
    before_weights = snapshot_weights(before)
    print(f"[PASS] list_all_spc_submissions count={len(before)}", flush=True)

    draft = parse_submission_markdown(md_path, date_suffix)
    payload = draft.to_payload()
    assert payload["name"] == f"Short Term Reversal Quality Gate {date_suffix}"
    assert "prompt" in payload and "sampleOutput" in payload
    print(f"[PASS] parse_submission_markdown name={payload['name']!r}", flush=True)

    submit_ok = False
    try:
        result = wqbs.submit_spc_markdown(md_path, date_suffix, log=None)
        sub = result["submission"]
        print(
            f"[PASS] submit_spc_markdown id={sub.get('id')} weight={sub.get('weight')}",
            flush=True,
        )
        submit_ok = True
    except HTTPError as exc:
        detail = ""
        if exc.response is not None:
            try:
                detail = exc.response.json().get("detail", "")
            except Exception:
                detail = exc.response.text[:200]
        if exc.response is not None and exc.response.status_code == 429:
            print(f"[SKIP] submit blocked by platform: {detail}", flush=True)
        else:
            raise

    after = wqbs.list_all_spc_submissions(log=None)
    after_weights = snapshot_weights(after)

    if submit_ok:
        new_ids = set(after_weights) - set(before_weights)
        if len(new_ids) != 1:
            print(f"[FAIL] expected 1 new submission, got {len(new_ids)}", flush=True)
            return 1
        new_id = next(iter(new_ids))
        new_sub = next(s for s in after if str(s.get("id")) == new_id)
        print(
            f"[PASS] created id={new_id} name={new_sub.get('name')!r} "
            f"weight={new_sub.get('weight')}",
            flush=True,
        )
    else:
        if before_weights != after_weights:
            print("[FAIL] submit skipped but submission weights changed", flush=True)
            return 1
        print("[PASS] existing submissions unchanged", flush=True)

    print("done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
