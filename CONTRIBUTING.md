# Contributing to harel

**harel** is the normative **specification** repository. It holds the prose spec
(`SPEC.md`), the machine JSON Schema (`schema/`), and examples (`examples/`) — text
only. There is **no test or implementation code here** and **no CI**; the executable
correctness target lives in [`fruwehq/harel-conformance`](https://github.com/fruwehq/harel-conformance),
and the Python reference implementation in [`fruwehq/harel-python`](https://github.com/fruwehq/harel-python).

## How the repos split

| repository | holds | CI |
|---|---|---|
| `harel` (this one) | `SPEC.md`, `schema/`, `examples/` — the prose normative text | none |
| [`harel-conformance`](https://github.com/fruwehq/harel-conformance) | the language-agnostic suite: engine cases (`conformance/01..NN`) and the black-box CLI runner (`conformance/cli/*`, `conformance/run_cli.py`) | none |
| [`harel-python`](https://github.com/fruwehq/harel-python) | the Python reference implementation; correct iff it passes the conformance suite | `test (ubuntu-24.04)`, required |

A behavior change usually spans all three: normative text here, the matching
conformance case in `harel-conformance`, and the implementation in `harel-python`.
Open one PR **per repo** (one issue → one PR). Where prose and the suite disagree,
**the suite wins** (SPEC §2) and a bug is filed against this document.

## Workflow

1. Branch from `main`, open a Pull Request, and **squash-merge** — `main` stays linear.
2. Resolve all review threads before merging.
3. **Never push to `main` directly.**
4. **No AI/assistant attribution anywhere** — not in commits, PR bodies, comments, or
   docs (no `Co-Authored-By:`, no "Generated with…"). Commits and PRs read as the
   author's own work.
5. Spec edits should reference the SPEC section(s) they touch and link the related
   `harel-conformance` / `harel-python` issues.

## Versioning

This repository carries the synchronized version in `VERSION` (currently `0.0.1`) and a
matching line at the top of `SPEC.md`.

> harel, harel-conformance, and harel-python share one synchronized SemVer version
> (currently pre-1.0 `0.0.x`). A release tags all three `vX.Y.Z` in lockstep; an
> implementation declares "implements harel spec vX.Y.Z" and pins the conformance suite
> at that tag.

## License

Contributions are made under the project's [MIT license](LICENSE).
