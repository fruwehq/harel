#!/usr/bin/env python3
"""Black-box CLI conformance runner (SPEC §13.6).

Language-agnostic: it shells out to an implementation's ``harel`` binary as a
**subprocess** and checks each ``conformance/cli/<case>/cli.yaml`` step against a
fresh temporary store. Nothing about the implementation's language or internals is
assumed — only the standardized CLI surface, exit codes, and JSON shapes (SPEC §13).

Usage:
    python conformance/run_cli.py [--cmd "harel"] [--conformance-dir DIR] [CASE ...]

``--cmd`` is the command used to invoke the implementation's CLI, split with shell
quoting (e.g. ``"harel"``, ``"python -m harel"``, ``"node dist/cli.js"``). Optional
positional CASE names restrict the run to those ``cli/<case>`` directories.

Exit code is 0 iff every selected case passes.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _resolve_arg(case_dir: Path, arg: str) -> str:
    """A bare filename present in the case dir (e.g. machine.yaml) resolves to it."""
    if "/" not in arg and (case_dir / arg).exists():
        return str(case_dir / arg)
    return arg


class Mismatch(Exception):
    """A structural comparison failed."""


def _assert_subset(actual: Any, expected: Any, path: str = "") -> None:
    """`expected` is a structural subset of `actual` (extra actual keys allowed)."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise Mismatch(f"{path or '<root>'}: expected object, got {type(actual).__name__}")
        for k, v in expected.items():
            if k not in actual:
                raise Mismatch(f"{path}.{k}: missing key")
            _assert_subset(actual[k], v, f"{path}.{k}")
    elif isinstance(expected, list):
        if not isinstance(actual, list):
            raise Mismatch(f"{path}: expected list, got {type(actual).__name__}")
        if len(actual) != len(expected):
            raise Mismatch(f"{path}: list length {len(actual)} != {len(expected)}")
        for i, (a, e) in enumerate(zip(actual, expected, strict=False)):
            _assert_subset(a, e, f"{path}[{i}]")
    elif actual != expected:
        raise Mismatch(f"{path or '<root>'}: {actual!r} != {expected!r}")


def _run(cmd: list[str], store: str, argv: list[str], stdin: str | None) -> tuple[int, str]:
    proc = subprocess.run(
        [*cmd, "--store", store, *argv],
        input=stdin,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout


def _check_step(cmd: list[str], store: str, case_dir: Path, step: dict[str, Any]) -> None:
    expect = step.get("expect") or {}
    argv = [_resolve_arg(case_dir, a) for a in step["run"]]

    if "stdin" in step:
        # Batch/streaming mode (§13.7): feed NDJSON argv lines, read NDJSON results.
        lines = [json.dumps([_resolve_arg(case_dir, a) for a in cmdline]) for cmdline in step["stdin"]]
        rc, out = _run(cmd, store, argv, stdin="\n".join(lines) + "\n")
        if "exit" in expect and rc != expect["exit"]:
            raise Mismatch(f"process exit {rc} != {expect['exit']}")
        if "stream" in expect:
            got = [json.loads(ln) for ln in out.splitlines() if ln.strip()]
            if len(got) != len(expect["stream"]):
                raise Mismatch(f"stream length {len(got)} != {len(expect['stream'])}")
            for i, (a, e) in enumerate(zip(got, expect["stream"], strict=False)):
                _assert_subset(a, e, f"stream[{i}]")
        return

    rc, out = _run(cmd, store, argv, stdin=None)
    if "exit" in expect and rc != expect["exit"]:
        raise Mismatch(f"exit {rc} != {expect['exit']}")
    if "json" in expect:
        actual = json.loads(out) if out.strip() else None
        _assert_subset(actual, expect["json"])
    elif "stdout" in expect and out != expect["stdout"]:
        raise Mismatch("stdout mismatch")


def _run_case(cmd: list[str], case_dir: Path) -> str | None:
    """Run one case; return None on pass, else a failure reason."""
    spec = _load_yaml(case_dir / "cli.yaml")
    with tempfile.TemporaryDirectory(prefix="harel-cli-") as store:
        for i, step in enumerate(spec.get("steps", [])):
            try:
                _check_step(cmd, store, case_dir, step)
            except Mismatch as exc:
                return f"step {i} ({' '.join(map(str, step['run']))}): {exc}"
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Black-box harel CLI conformance runner")
    p.add_argument("--cmd", default="harel", help='invoke the impl CLI (default "harel")')
    p.add_argument(
        "--conformance-dir",
        default=str(Path(__file__).resolve().parent / "cli"),
        help="the conformance/cli directory",
    )
    p.add_argument("cases", nargs="*", help="restrict to these case names")
    args = p.parse_args(argv)

    cmd = shlex.split(args.cmd)
    cli_dir = Path(args.conformance_dir)
    selected = sorted(d for d in cli_dir.iterdir() if d.is_dir())
    if args.cases:
        wanted = set(args.cases)
        selected = [d for d in selected if d.name in wanted]
    if not selected:
        print("no CLI conformance cases selected", file=sys.stderr)
        return 2

    failures = 0
    for case_dir in selected:
        reason = _run_case(cmd, case_dir)
        if reason is None:
            print(f"PASS  cli/{case_dir.name}")
        else:
            failures += 1
            print(f"FAIL  cli/{case_dir.name}: {reason}")
    print(f"\n{len(selected) - failures}/{len(selected)} CLI cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
