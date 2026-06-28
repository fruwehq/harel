# harel — specification

Status: **draft v1**. Normative unless a section says "informative."
Keywords MUST / SHOULD / MAY per RFC 2119.

## 0. References

- Miro Samek, *Practical Statecharts in C/C++ — Quantum Programming for Embedded
  Systems* (PSiCC). The canonical hierarchical-state-machine (HSM) dispatch and
  transition algorithm. **Implementers SHOULD follow PSiCC's RTC/LCA algorithm.**
- David Harel, *Statecharts: A Visual Formalism for Complex Systems* (orthogonal
  regions, hierarchy, history).
- UML 2.x State Machines (terminology; behavioral semantics where not overridden).
- CEL — Google Common Expression Language (<https://cel.dev/>), the guard /
  expression language (§6).
- `cns_statemachine` (prior art; XML + Groovy guards/actions). harel uses YAML +
  CEL + structured actions.

## 1. Goals

1. **One definition, many runtimes.** A machine is defined once in YAML; an engine
   in any language runs it. Cross-language agreement is guaranteed by the
   conformance suite (§9), which is the ultimate arbiter of correct behavior.
2. **Full statechart semantics:** hierarchy, orthogonal regions, history, defer,
   timers, run-to-completion.
3. **Active objects:** each machine *instance* owns an event queue; instances are
   spawned dynamically and communicate only by posting events (no shared mutable
   state across instances).
4. **Portable, sandboxed expressions:** guards in CEL; actions are a small
   structured set whose argument values are CEL. Host scripting languages are
   pluggable but not required for portability.
5. **Strict typing:** context variables and event payloads are typed and validated
   (§4.2, §4.3).
6. **Robust over time:** defined fault handling (§5.9), versioned definitions and
   safe-point migration (§10), and event-schema evolution guidance (§10.3) so
   long-lived instances survive engine/definition upgrades.
7. **Contracts:** declare and statically check that a machine provides an interface
   (§7).
8. **Engine is application-agnostic.** No domain concepts. Hosts supply storage,
   clock, and (optional) custom-action adapters through interfaces (§8).

## 2. Conformance

An implementation is **conformant** iff it passes every case in `conformance/`
(§9). The prose here explains intent; where prose and the suite disagree, the
suite wins and a bug MUST be filed against this document. Implementations MAY add
guard/action languages and storage/clock adapters; they MUST NOT change the core
dispatch semantics. Machine YAML MUST validate against `schema/machine.schema.json`
before execution.

## 3. Concepts

- **Machine definition** — a YAML document describing one *kind* of statechart,
  carrying its own `version` (§10).
- **Machine instance** (a.k.a. **active object**) — a running statechart: a
  definition + **extended state** (typed context variables) + an **event queue** +
  a **deferred set** (§5.7) + a **state configuration** (the set of currently
  active states; >1 when orthogonal regions are active). Has a stable **instance
  id** and records the **definition version** it runs under.
- **State** — `simple` (leaf), `composite` (one region of substates), or
  `orthogonal` (≥2 concurrent regions). Composite/orthogonal states have an
  **initial** transition per region.
- **Region** — an independent area of a composite/orthogonal state with its own
  active substate. Orthogonal regions are processed within a single RTC step of the
  *same* instance (synchronous), unlike spawned instances (asynchronous).
- **Pseudostates** — `initial`, `final`, `history` (shallow `H`, deep `H*`),
  `choice` (dynamic, guards evaluated at run), `junction` (static).
- **Signal** — a declared event name with a typed **payload schema** (§4.3).
- **Event** — an occurrence of a signal carrying a concrete payload.
- **Transition** — `source --signal [guard] / action--> target`. Kinds:
  **external** (default; exits source state), **internal** (no exit/entry; action
  only), **local** (does not exit the containing composite). May be **guarded**.
- **Guard** — a boolean CEL expression over extended state + event payload.
- **Action** — a structured statement (assign / post / send / emit / broadcast /
  spawn / stop) whose argument values are CEL expressions. Run on transitions and
  on state entry/exit.
- **Contract** — a named interface: required signals, states, spawns (§7).

## 4. Machine definition (YAML)

A definition is one YAML document beginning with the `harel:` format key. The
`schema/machine.schema.json` JSON Schema is normative for structure; this section
gives meaning. See `examples/full.yaml` (every feature) and `examples/minimal.yaml`
(smallest valid machine).

**Parsing:** harel YAML MUST be parsed under the **YAML 1.2 core schema**, where
only `true`/`false` are booleans. This matters because the transition key is `on:`;
a YAML 1.1 parser (e.g. stock PyYAML) would coerce `on`/`off`/`yes`/`no` to
booleans. Implementations on a 1.1 parser MUST disable that coercion. Signal,
state, and variable names MUST match `^[A-Za-z_][A-Za-z0-9_]*$`.

```yaml
harel: 1                       # format version (required, currently 1)
id: provider                   # definition id (required, stable)
version: 1                     # definition version, for migration (required, int ≥1)
contracts: [provider]          # interfaces this machine claims to satisfy (§7)

context:                       # typed extended state (§4.2)
  api_key:  { type: string, default: null, external: true }   # null == unset
  attempts: { type: int,    default: 0 }

signals:                       # typed signal/payload declarations (§4.3)
  configure: {}
  probe: {}
  create_instance:
    payload:
      name:    { type: string, required: true }
      bundles: { type: list, default: [] }
  instance_done:
    payload: { id: { type: string, required: true } }

initial: unconfigured          # top-level initial state (required)

on_error:                      # optional machine-level fault handler (§5.9)
  target: faulted

states:
  unconfigured:
    on:
      configure: { target: configured, guard: "api_key != null" }
  configured:
    entry:
      - assign: { attempts: "0" }
    on:
      probe:
        target: reachable
        action: [ { post: { signal: do_probe } } ]
      create_instance:
        internal: true
        action:
          - spawn: { def: instance, payload: { name: "event.payload.name" }, result: last_child }
  reachable:
    type: composite
    initial: idle
    states:
      idle: {}
  faulted: {}
```

### 4.1 Top-level fields
- `harel` (int, required) — format version; this document defines `1`.
- `id` (string, required, stable) — definition id.
- `version` (int ≥1, required) — definition version (§10).
- `contracts` (list of strings, optional) — declared interfaces (§7).
- `context` (map, optional) — typed extended state (§4.2).
- `signals` (map, optional but RECOMMENDED) — typed signals (§4.3). Strict typing:
  if `signals` is present, only declared signals MAY be posted to the machine and
  payloads MUST validate; an undeclared or malformed event is rejected at post time
  (host error, not a fault — it never enters the queue).
- `languages` (map, optional) — `{guard, action}` language ids; defaults
  `{guard: cel, action: harel}`. Overriding `guard` selects a host-pluggable
  language for guards; `action: harel` is the structured action set (§6) and is the
  portable default.
- `initial` (string, required) — id of the top-level initial substate.
- `on_error` (Transition, optional) — taken when an action faults (§5.9).
- `migrations` (list, optional) — forward migrations from older versions (§10).
- `states` (map, required) — `name -> StateNode`.

### 4.2 Context (typed extended state)
`context: { name: { type, default, external? } }`.
- `type ∈ {string, int, float, bool, map, list}`.
- `default` — initial value; MAY be `null` meaning **unset** (distinct from a
  type's zero value). A non-null default MUST match `type`.
- `external: true` — the **host** supplies the value (resolved settings/secrets);
  it is read-only to actions and refreshed by the host before dispatch. (eve maps
  resolved settings/secrets to external context — settings *are* the FSM context.)

### 4.3 Signals (typed payloads)
`signals: { name: { payload?: { field: {type, required?, default?} } } }`.
- A signal with no `payload` carries an empty payload.
- `required: true` fields MUST be present; others may be omitted (and take
  `default` if given). Extra fields not in the schema are rejected.
- Payload validation happens at **post time**; an invalid payload is a host-side
  error and the event is not enqueued (see §10.3 for evolving payloads safely).

### 4.4 StateNode
- `type`: `simple` (default) | `composite` | `orthogonal`.
- `entry`, `exit`: ordered list of actions (§6).
- `initial`: required for `composite`; for `orthogonal` each region declares its
  own.
- `states`: nested states (for `composite`).
- `regions`: list of `{ initial, states }` (for `orthogonal`, ≥2, ordered §5.5).
- `on`: map `signal -> Transition | [Transition, ...]` (a list is ordered; the
  first whose guard passes wins).
- `after`: list of `{ duration, target?, action?, guard? }` time-triggered
  transitions (§5.8).
- `defer`: list of signal names deferred while this state is active (§5.7).
- `history`: `none` (default) | `shallow` | `deep`.

### 4.5 Transition
- `target`: state id, dotted for nesting (`reachable.idle`); omit ⇒ internal.
- `guard`: CEL boolean expression (optional). `lang:` MAY override the language.
- `action`: ordered list of actions (optional).
- `internal`: bool (no exit/entry; action only).
- `local`: bool (do not exit/re-enter the least-common composite).

## 5. Execution semantics (normative)

### 5.1 Extended state
A flat namespace of typed variables (the `context`). Guards read it; actions
read/write it (except `external`, which is read-only). Reads/writes are visible
within the current RTC step. Assignments MUST respect declared types.

### 5.2 Run-to-completion (RTC)
Each instance processes **one event completely** — all resulting transitions,
exit/entry/initial actions, and orthogonal-region dispatch — before dequeuing the
next. An instance is never re-entered while an RTC step is in progress. Events
posted during a step are enqueued (§5.6), never processed recursively. RTC per
instance is single-threaded.

### 5.3 Hierarchical event handling
On dispatch of signal `s`, for each active leaf state, search for a transition on
`s` starting at the **most deeply nested** active state and walking up the parent
chain. The **first** state whose transition for `s` has a passing guard handles the
event; ancestors are not consulted further for that region. If `s` is in the active
config's `defer` set and unhandled, it is deferred (§5.7). Otherwise an unhandled
event is silently discarded (informative: hosts MAY log).

### 5.4 Transition execution
For a chosen external transition `src --> tgt` with actions `a`:
1. Compute **LCA** = least common ancestor composite of `src` and `tgt`.
2. **Exit** active states from the current leaf up to (not including) LCA,
   innermost-first, running each `exit`.
3. Run the transition actions `a`.
4. **Enter** states from LCA down to `tgt`, outermost-first, running each `entry`.
5. If `tgt` is composite/orthogonal, recursively take its `initial` (or `history`)
   transitions until all regions reach leaf states.

`internal`: run only the actions; no exit/entry; config unchanged.
`local`: like external but LCA is the containing composite itself (no exit/re-entry
of that composite). Entry/exit ordering MUST match PSiCC; the suite pins it.

### 5.5 Orthogonal regions
An `orthogonal` state has ≥2 regions, each with its own active substate. A
dispatched signal is offered to **every** region (each runs §5.3–5.4 independently,
in **declared region order**, within the same RTC step — order is normative and
deterministic). The configuration is the union across regions. A region reaching
`final` is done; when **all** regions are `final`, a completion event (`__done__`)
is generated for the orthogonal state's parent.

### 5.6 Active objects, queues, spawning, messaging
- Each instance has a **FIFO event queue**. `dispatch` = dequeue one event, run one
  RTC step. The host's run loop drains queues; the engine prescribes only
  per-instance RTC + FIFO ordering. **There is no periodic tick:** the only driver
  is event arrival (including timer events, §5.8). An instance runs to quiescence
  whenever its queue is non-empty.
- **Instances form a tree.** The root is created by the host; others are **spawned**
  by an action: `spawn(def, payload?) -> instanceId`. A spawned child runs
  independently with its own queue and lifecycle. The spawner receives the child id
  (via `result:` into a context var).
- **Messaging actions:** `post` → self; `send(to, …)` → another instance by id;
  `emit` → the **parent**; `broadcast` → all **direct children**. Delivery is
  asynchronous (enqueue for the target's next dispatch), preserving per-pair FIFO.
- **Termination:** an instance whose top region reaches `final`, or that runs
  `stop`, terminates: children are stopped first (post-order), exit actions run up
  the tree, the queue and deferred set are dropped, and a `__child_done__` (with the
  child id) is emitted to the parent.

> This is how the eve model works without violating "one machine = one state": the
> *provider* instance stays in `configured`; `create_instance` **spawns** an
> `instance` active object; that instance spawns an `os` child and, when
> provisioning, a child per package. Each is its own machine with its own single
> state; they coordinate by posting events.

### 5.7 Deferred events (normative)
A state MAY list signals in `defer`. Semantics follow UML's **deferred set**, *not*
a blind re-queue:
1. When a dispatched event is **not** handled by the active configuration (§5.3) and
   its signal is in the active config's effective `defer` set (union over active
   states), the event is moved to the instance's **deferred set**, preserving
   arrival order. It is **not** placed back on the tail.
2. **Reinsertion is edge-triggered by state change.** Whenever an RTC step changes
   the state configuration, every deferred event whose signal is **no longer
   deferred** by the new configuration is moved, in original relative order, to the
   **front** of the event queue (ahead of not-yet-processed fresh events) and will
   be dispatched before them.
3. A deferred event that is still deferred under the new configuration stays in the
   deferred set.

Rationale (informative): an instance's state can change only by processing its own
events, so a deferred event's eligibility can change only at a state transition.
Edge-triggering on state change therefore needs **no timer/poll** and cannot
busy-loop (which a naive tail re-queue would, when the deferred event is alone in
the queue). The deferred set is part of the snapshot (§8).

### 5.8 Timers (normative; clock via adapter)
Time is provided by an injected **clock adapter** (§8) so the engine stays a pure
event-driven function and conformance tests stay deterministic.
- A state's `after: [{ duration, target?, action?, guard? }]` schedules, on entry to
  that state, a timer for `duration` (e.g. `30s`, `5m`, `500ms`). When the clock
  fires it, the engine posts an internal **time event** to the instance; on dispatch
  it behaves as an ordinary guarded transition. Exiting the state cancels its
  pending `after` timers.
- The clock adapter exposes `schedule(instanceId, timerId, duration)`,
  `cancel(instanceId, timerId)`, and a monotonic `now()`. In production it is the
  real clock. **In conformance tests it is a virtual clock the harness advances
  explicitly** via an `advance:` step (§9); firing a timer enqueues the time event,
  which is then dispatched under normal RTC. No wall-clock time is used in tests.
- Outstanding timers (their `timerId`, target state, and fire deadline relative to
  `now()`) are part of the snapshot so they survive suspend/resume.

### 5.9 Action faults (normative)
An RTC step (exit actions → transition actions → entry actions) is **atomic** with
respect to faults.
1. If any action raises an error, the engine **aborts the step**: the partial
   transition is **not** applied (the configuration is left as it was at the start
   of the step) and the triggering event is moved to a **dead-letter** record on the
   instance.
2. The instance is then **faulted**. If the machine declares `on_error`, the engine
   takes that transition (from the current, pre-abort configuration) as a normal
   transition to handle the fault; its target is typically an error state. If
   `on_error` is absent, the instance enters the reserved **`__faulted__`** status
   and **stops dispatching** further events (its queue is retained) until a host
   `reset` re-activates it. Faulting is **per active object**, never global —
   siblings and parent keep running.
3. **Hangs:** the engine cannot preempt arbitrary host code. The portable
   guard/action languages (CEL + structured actions, §6) are **total and bounded**
   (no loops, no I/O) and therefore cannot hang. For host-pluggable languages the
   engine enforces a **deadline via the clock adapter**; on overrun the step is
   declared faulted (same path as §5.9.1–2). The deadline bounds the *machine's*
   progress; a host thread may still be running — hosts MUST treat pluggable-language
   actions as potentially long and SHOULD prefer the bounded default.

Faults, dead-letters, and `__faulted__` status are observable (§8) so a host (eve,
the TUI, an agent) can surface "instance X faulted in state Y on event Z."

## 6. Guard & action languages

**Guards = CEL.** A guard is a CEL boolean expression evaluated against a binding of
`context` variables plus `event` (`event.signal`, `event.payload.*`). CEL is
side-effect-free, non-Turing-complete, and has multi-language runtimes, which is
what makes guards portable. An engine MUST provide CEL and MAY provide host
languages (`groovy`, `js`, …) selected via `lang:` on a guard or via
`languages.guard`.

**Actions = a structured set (id `harel`).** Each action is a single-key map; its
argument *values* are CEL expressions evaluated against `(context, event)`:

| action | form | effect |
|---|---|---|
| assign | `{ assign: { var: "<cel>", … } }` | set context vars (typed) |
| post | `{ post: { signal: name, payload?: { k: "<cel>" } } }` | enqueue on self |
| send | `{ send: { to: "<cel>", signal: name, payload?: {…} } }` | enqueue on instance id |
| emit | `{ emit: { signal: name, payload?: {…} } }` | enqueue on parent |
| broadcast | `{ broadcast: { signal: name, payload?: {…} } }` | enqueue on all children |
| spawn | `{ spawn: { def: id, payload?: {…}, result?: var } }` | spawn child; id → `result` |
| stop | `{ stop: {} }` | terminate this instance |

Action values are CEL, so there is no second expression dialect to implement; the
structured set is total and bounded (no loops, no I/O, no host calls). Richer needs
⇒ a pluggable host action language via `languages.action` / `lang:`, which forfeits
the bounded-execution guarantee (§5.9.3). `post/send/emit/broadcast/spawn` signals
MUST be declared in the producing or receiving machine's `signals` and their
payloads MUST type-check.

**Adapter contract** (what an engine calls):
- `eval_guard(expr, ctx, event) -> bool`
- `apply_action(action, ctx, event, api) -> ctx'` where `api` exposes
  `post/send/emit/broadcast/spawn/stop`. Deterministic given `(ctx, event)` except
  for spawn-id allocation.

## 7. Contracts (interfaces)

A **contract** is a named, versioned interface a machine claims to satisfy:

```yaml
harel_contract: 1
id: provider
requires:
  signals: [configure, create_instance]   # handled in some reachable state
  states:  [configured]                    # declared
  spawns:  [instance]                      # defIds it must be able to spawn
```

A static **validator** checks a machine against each declared contract: every
required signal has at least one transition somewhere; every required state exists;
every required `spawn` def appears in an action. Contract checking is part of
conformance (a machine + contract + pass/fail). Contracts are how a host (eve)
demands "any provider must accept `create_instance` and reach `configured`."
Contracts are extensible: a machine MAY satisfy several; a contract MAY be
versioned and a newer contract MAY add requirements (a machine satisfying contract
v2 satisfies v1 if requirements are additive).

## 8. Persistence & host adapters

The engine is pure logic; the host provides:
- **Storage adapter** — load/save a serialized **instance snapshot**:
  `{ def_id, def_version, id, parent_id, status, state_config, context, queue,
  deferred, timers, dead_letter, history }`. `status ∈ {active, faulted,
  terminated}`. Snapshots MUST round-trip (serialize → deserialize → identical
  behavior) and MUST be representable as JSON/YAML so an instance suspended by one
  engine can, in principle, resume in another.
- **Clock adapter** — `schedule/cancel/now` (§5.8). The conformance harness supplies
  a virtual clock.
- **Action/side-effect** — the engine implements messaging/spawn/stop; the host
  wires the run loop and any external effects a *custom* (non-default) action
  language exposes.
- **Observer** (optional) — a callback stream of `{ instance, transition, entered,
  exited, emitted, spawned, faulted }` per RTC step, for hosts/TUIs/agents.

## 9. Conformance test format (normative)

`conformance/` holds language-neutral cases. Each case is a directory with:

```
conformance/<case>/
  machine.yaml          # one or more `---`-separated definitions; first is root
  contracts/*.yaml      # optional, for contract-validation cases
  test.yaml             # the scenario + expectations
```

`test.yaml`:
```yaml
title: orthogonal regions broadcast
context: { api_key: 'k' }          # initial external/context overrides on root
steps:
  - send: { signal: configure }     # post to root, then run to quiescence
    expect:
      config: [configured]          # active leaf state ids (sorted)
      context: { attempts: 0 }
      emitted: []                   # signals emitted to parent/host, in order
  - send: { signal: create_instance, payload: { name: a } }
    expect:
      spawned: [instance]           # defIds spawned this step, in order
  - advance: 30s                    # virtual-clock advance; fires due timers
    expect:
      config: [timeout]
  - send: { signal: bad_payload }
    expect:
      rejected: true                # payload/signal failed validation (not enqueued)
trace: optional                     # if set, exact entry/exit/action ordering
```

A run: validate definitions against `schema/machine.schema.json`, load them, create
the root instance, then for each step apply `send`/`advance`, **run all instances to
quiescence** (all queues empty), and check expectations. `config` is the sorted set
of active leaf states across all live instances (or scoped via an `instance:`
selector). `faulted:` / `dead_letter:` MAY be asserted. An engine passes iff all
expectations match. Ordering-sensitive cases set `trace`.

The suite MUST cover: leaf transitions; guards (CEL); internal/local/external; LCA
exit/entry ordering; composite initial; orthogonal broadcast + completion + region
order; shallow & deep history; choice/junction; typed-payload accept/reject;
defer (deferred-set + edge-triggered reinsertion + no busy-loop); timers via virtual
clock (schedule/fire/cancel-on-exit); spawn/send/emit/broadcast/stop + FIFO; action
faults (`on_error` present and absent, dead-letter); termination + child cleanup;
contract pass/fail; and snapshot round-trip + migration (§10).

## 10. Versioning, hot-swap & migration (normative)

Definitions are **immutable and versioned** (`version:`). A snapshot records
`def_version`. When the host loads a definition whose current version differs from a
live instance's `def_version`:

### 10.1 Pin by default
A live instance keeps running under the **version it started on** until it
terminates. The host MUST retain the old definition while any instance pins to it.
New instances use the new version. This guarantees a long-lived instance is never
silently mutated mid-flight.

### 10.2 Forward migration at a safe point
A newer definition MAY declare migrations:
```yaml
migrations:
  - from: 1
    to: 2
    when: "state in ['idle','configured']"      # CEL over a `state` binding
    state_map: { old_state: new_state }          # remap active leaves
    context: [ { assign: { new_var: "old_var" } } ]   # transform context
```
A migration is applied **only at a safe point**, defined as: the instance is
**quiescent** (empty queue, no in-progress RTC, empty deferred set) **and** its
current configuration satisfies `when` and is covered by `state_map`. Otherwise the
instance stays pinned and is retried at its next quiescent point (or runs to
termination on the old version). Migration is itself snapshot-atomic: it either
fully applies (config remapped, context transformed, `def_version` bumped) or not at
all. `when` and `context` use CEL with a binding exposing `state` (the active leaf
id, or list for orthogonal) plus the old context.

### 10.3 Event-schema evolution (recommendation; partly normative)
- Payload schemas SHOULD evolve **additively**: add optional fields, never
  repurpose or retype an existing field, never make an optional field required.
  Additive changes keep old producers compatible (MUST be honored by validators).
- For a **breaking** change, the recommended pattern is an **adapter machine** (an
  anti-corruption layer): a small machine that accepts legacy-version signals and
  `emit`s/`send`s current-version signals. Because adapters are ordinary machines,
  no special engine feature is required; the producer targets the adapter, which
  re-emits in the new schema. This keeps strict typing while letting old and new
  coexist during rollout.

## 11. Non-goals / future (informative)

- **SaaS / distributed queues & agent hosting**: instances communicate only via the
  messaging API, so queues can later be backed by a network transport without
  changing machine semantics. A multi-tenant host that exposes "legal events from
  the current state" to LLM agents (forcing well-maintained agent state) is a
  separate product layer. Out of scope for the engine.
- Visual editor, codegen, real-time/deadline scheduling beyond §5.8.
- Cross-instance transactions; instances are independent active objects by design.
