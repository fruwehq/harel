# Conformance suite

Language-neutral test cases that **every** harel engine implementation MUST pass.
This suite — not any single implementation — is the normative definition of
correct behavior. Format: see [`../SPEC.md`](../SPEC.md) §9. Machines MUST first
validate against [`../schema/machine.schema.json`](../schema/machine.schema.json).

Each `<case>/` directory contains:
- `machine.yaml` — one or more `---`-separated definitions (first is the root).
- `contracts/*.yaml` — optional, for contract-validation cases.
- `test.yaml` — the scenario (`steps:` of `send:` / `advance:` + `expect:`).

`cli/<case>/` cases instead hold a `cli.yaml` (steps of `run:`/`expect:`) that pin the
standard CLI surface (SPEC §13.6), run against a fresh temp store.

A harness loads the definitions, creates the root instance, and for each step
posts the event (or advances the virtual clock) and runs **all** instances to
quiescence before checking `expect`. See `01-guarded-leaf/` for the minimal shape.

This suite covers SPEC §9 end to end — cases `01`–`22` (engine semantics) plus
`cli/` (the §13.6 CLI surface):

| case | covers |
|---|---|
| 01 guarded-leaf · 02 hierarchy-bubbling · 03 initial-action · 04 defer | guards, ancestor handling, initial-transition actions, deferred-set |
| 05 esvs-scope · 06 payload-typing · 07 internal-external · 08 local-vs-external | scope/shadow/re-init, typed payloads, transition kinds + ordering |
| 09 orthogonal · 10 history-deep · 11 history-shallow · 12 guarded-list | regions + `done`, history, first-match-wins |
| 13 spawn-publish · 14 subscription · 15 external-env-refresh | spawn + directed/subscribed publish + scope, `external`/`env`/`refresh` |
| 16 timer · 17 fault-handled · 18 fault-unhandled · 19/20 contract pass/fail | timers, faults + dead-letter, static contracts |
| 21 snapshot-roundtrip · 22 migration | snapshot round-trip, safe-point migration |
| cli/01 turnstile · cli/02 stream | validate/new/state/send/list + JSON shapes, and batch/streaming mode (§13.6/§13.7) |

Expected outputs are derived from the spec (PSiCC semantics) since no engine exists
yet; the first implementation co-validates them, and any mismatch is resolved by a PR
(suite bug or spec ambiguity). Add cases for genuine gaps found during implementation.
The suite — not any single implementation — is what makes multi-language engines
trustworthy.

**Running CLI cases (black box).** `run_cli.py` shells out to any implementation's
binary as a subprocess (SPEC §13.6) — language-agnostic:

```sh
python conformance/run_cli.py --cmd "harel"          # or "python -m harel", "node …"
python conformance/run_cli.py --cmd "harel" 01-turnstile   # one case
```

Engine cases (`01`–`22`) are driven directly through each implementation's own harness.
