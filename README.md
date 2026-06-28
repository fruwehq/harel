# harel

A **language-agnostic statechart engine**. Machines are declared once in YAML and
run by an implementation in *any* language; all implementations agree because they
are validated against a shared, normative **conformance test suite**.

Named for David Harel, who invented statecharts. In the Harel / UML state-machine
lineage, following the run-to-completion and hierarchical-state-machine semantics
of Miro Samek's *Practical Statecharts in C/C++ — Quantum Programming for Embedded
Systems* (PSiCC). Successor in spirit to `cns_statemachine` (a well-tested
Java/XML+Groovy version); harel replaces XML+Groovy with YAML + CEL.

- **Hierarchical states** (nesting, entry/exit, shallow/deep history)
- **Orthogonal regions** (concurrent, synchronous, within one instance)
- **Active objects** — each machine instance owns an event queue; instances are
  **spawned dynamically** and **communicate only by posting events**
- **Guards in [CEL](https://cel.dev/)** (Google's Common Expression Language —
  open, sandboxed, non-Turing-complete, with Go/C++/Java/Rust/TS/Python runtimes);
  **structured actions** whose argument values are CEL expressions. Host scripting
  languages (Groovy/JS/…) remain pluggable.
- **Strictly typed** context and event payloads, validated at load and post time
- **`defer`**, **timers** (via an injected clock), and **`on_error` faults**
- **Contracts** — a machine can declare it satisfies an interface (required
  signals/states/spawns), checkable statically
- **Versioned definitions + migrations** — long-lived instances pin to the version
  they started on and migrate forward only at a safe point (hot-swap)

Status: **specification**. See [`SPEC.md`](SPEC.md). The JSON Schema for machine
YAML is in [`schema/`](schema/); worked examples in [`examples/`](examples/);
the cross-language test suite in [`conformance/`](conformance/).

Not coupled to any application; downstream users (e.g. eve) provide their own
storage/clock/action adapters and machine YAML. A natural downstream use case is
**constraining LLM agents** to a well-maintained state: the only way to advance is
to emit a typed event that passes a guard, so an agent cannot reach an invalid
configuration or skip a required step. That hosting layer is a separate product
and out of scope for this engine spec.
