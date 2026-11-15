# blockv2-mod: graph to macro-native instructions

Issue #219 / PR #269. PR185 defines the architecture: functional macros are hard
boundaries; P/U/C/F/J identify control ownership. Every data connection, including
same-owner connections, requires an explicit selected endpoint binding.

## Current inputs and execution path

The admitted command-pipeline/1 base is
evidence/command-pipeline/hardware.json
(blockv2-mod-pr185-memory-3fa694340b33bf0b); its service inventory is
evidence/command-pipeline/services.json.

Input a model graph directory containing native-recipe-graph.json,
native-operand-recipes.json and native-value-layout.json alongside this hardware.
Algo1 constructs a selected plan. Materialization joins the plans' selected
connections and checks the complete RTL assembly. Packaging emits mother/local
programs, CALL/WAIT dependencies, descriptors, address layouts, deployment records
and candidate-wiring.json from that same plan. TLM executes the sealed package;
it does not choose a replacement mapping or hardware implementation.

Generic graph entry points:
compiler/run_macro_graph_frontend.py, compiler/run_macro_selection.py,
compiler/materialize_native_product.py, compiler/package_native_plan.py.
Runtime entry: tlm/run_macro_package.py.
Use the remote Python/module paths in reproducibility/environment.json.

## Command-internal pipelines

The production path overlaps activation reads and SRAM commits, observes scaling
statistics during loading, converts through two packing/response slots, reads A
with two credits, models the M core's existing 32 weight credits, prefetches the
next K128 into the existing source window, and prepares the next writeback burst
while the previous DDR write completes. Dot has separate A/B cache lines.

Old selectable serial branches and corresponding generator templates have been
removed. An old pipeline contract is rejected during product binding, packaging
and execution. Real mathematical dependencies, ownership, finite capacities and
final commit waits remain. See audits/COMMAND_PIPELINE_REVIEW.md.

## Validation and current status

Fresh complete assembly admits 30 functional macros, nine local controllers and
242 parent control instances; hidden functional-macro negative checks pass.
evidence/command-pipeline/final-capacity.json binds 18 behavior capabilities to
actual RTL tests and the assembled source closure.

The combined regression job 115472 passed all 23 entries, covering production
TLM numeric paths, RTL reordered responses, backpressure, cancellation/error
drain, unknown-tag isolation, and deterministic regeneration.

Full history512/history513 compilation, same-plan instruction/wiring packaging,
and two causally chained decode executions are in progress. Current job records:
evidence/command-pipeline/full-decode512-two-step/jobs.json.
Initial history is frozen zero, first token is 840, and the second step consumes
the first step's committed KV and sampled token. Each full graph is checked
against an independent integer reference. No prefill or 128-step decode is run.

Run this complete target using audits/command_pipeline_submit.py with explicit
--hardware, --services and a new --output directory, inside the authorized remote
environment. See audits/command_pipeline_README.md for admission and dependencies.

## Evidence limits

Full two-step numeric/performance acceptance is pending. Earlier history2 timings
cannot be used as a history512 baseline or a claimed speedup for this change.
TLM timing is uncalibrated. External phase installation/loading time is excluded
and reported; modeled retirement totals are not measured continuous hardware
throughput. No physical implementation/PPA acceptance is claimed.

Historical receipts remain under evidence/architecture-revision-185 and
evidence/joint-frontier. Their graph, hardware and source bindings identify their
scope; they do not admit current modified RTL. Complete plans, binaries, weights
and runtime images stay on the remote server; lightweight source and evidence
are published through PR #269.
