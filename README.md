# harel

A **language-agnostic statechart engine**. Machines are declared once in YAML and
run by an implementation in *any* language; all implementations agree because they
are validated against a shared, normative **conformance test suite**.

Named for David Harel, who invented statecharts. In the Harel / UML state-machine
lineage, following the run-to-completion and hierarchical-state-machine semantics
of Miro Samek's *Practical Statecharts in C/C++ — Quantum Programming for Embedded
Systems* (PSiCC); the outermost state is `top`, per the book. Successor in spirit to
`cns_statemachine` (a Ruby HSM with a YAML format), whose vocabulary it keeps —
`top`, `esvs`, `on_events`, `transition_to`, `defer`, `publish` — replacing raw
guards/actions with CEL + structured actions.

- **Hierarchical states** (nesting, entry/exit, shallow/deep history)
- **Orthogonal regions** (concurrent, synchronous, within one instance)
- **Active objects** — each machine instance owns an event queue; instances are
  **spawned dynamically** and **communicate only by publishing events** (directed or
  by subscription) over a pluggable bus
- **`esvs`** (extended-state variables) declared **inside states**, hierarchically
  scoped — not a global blob; `external` esvs are seeded by the host, with an `env`
  event + `refresh` to react when the source changes
- **Guards in [CEL](https://cel.dev/)** (Google's Common Expression Language —
  open, sandboxed, non-Turing-complete, with Go/C++/Java/Rust/TS/Python runtimes);
  **structured actions** (`assign`/`publish`/`refresh`/`spawn`/`stop`) whose computed
  values are CEL. Host scripting languages remain pluggable.
- **Strictly typed** events and esvs, validated at load and delivery time
- **`defer`**, **timers** (via an injected clock), and faults via an **`error` event**
- **Contracts** — a machine can declare it satisfies an interface (required
  events/states/spawns), checkable statically
- **Versioned definitions + migrations** — long-lived instances pin to the version
  they started on and migrate forward only at a safe point (hot-swap)

Status: **specification**. See [`SPEC.md`](SPEC.md). The JSON Schema for machine
YAML is in [`schema/`](schema/); worked examples in [`examples/`](examples/);
the cross-language test suite in [`conformance/`](conformance/).

Not coupled to any application; downstream users provide their own bus/queue/clock/
store adapters (a simple in-memory default ships for tests) and machine YAML. A
natural downstream use case is **constraining LLM agents** to a well-maintained
state: the only way to advance is to publish a typed event that passes a guard, so
an agent cannot reach an invalid configuration or skip a required step. That hosting
layer is a separate product and out of scope for this engine spec.
