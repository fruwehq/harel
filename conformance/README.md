# Conformance suite

Language-neutral test cases that **every** harel engine implementation MUST pass.
This suite — not any single implementation — is the normative definition of
correct behavior. Format: see [`../SPEC.md`](../SPEC.md) §9. Machines MUST first
validate against [`../schema/machine.schema.json`](../schema/machine.schema.json).

Each `<case>/` directory contains:
- `machine.yaml` — one or more `---`-separated definitions (first is the root).
- `contracts/*.yaml` — optional, for contract-validation cases.
- `test.yaml` — the scenario (`steps:` of `send:` / `advance:` + `expect:`).

A harness loads the definitions, creates the root instance, and for each step
posts the event (or advances the virtual clock) and runs **all** instances to
quiescence before checking `expect`. See `01-guarded-leaf/` for the minimal shape.

The implementing agent should expand this suite to cover everything listed in
SPEC §9: hierarchy, orthogonal regions + region order, shallow/deep history,
CEL guards, structured actions, typed-payload accept/reject, defer (deferred-set +
edge-triggered reinsertion, no busy-loop), timers via the virtual clock,
spawn/send/emit/broadcast/stop + FIFO, action faults (`on_error` present/absent +
dead-letter), termination + child cleanup, contracts, and snapshot round-trip +
migration. The suite is the deliverable that makes multi-language implementations
trustworthy.
