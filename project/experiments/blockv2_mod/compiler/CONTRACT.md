# Whole-graph native compiler contract

Inputs are the operator graph bundle and the nine-instance blockv2-mod hardware
bundle. Numeric formats, weight/layout provenance and runtime shape bindings are
part of the graph bundle. SRAM configuration, service signatures, port behavior,
DDR limits and native encoder capabilities are part of the hardware bundle.

## Pipeline

1. Recognize semantic regions from graph edges, shapes and constant provenance.
   Preserve shared intermediates and every external input/output dependency.
   Recognition does not assign timing, choose a hardware instance or impose
   layer/stage ordering. Views remain explicit address transformations.
2. Generate implementable candidates. Each candidate must carry a native
   encoder, operand layout, scratch lifetime, resource/connection requirements
   and a hardware completion contract. Hardware that cannot execute a candidate
   is rejected here, before search.
3. Run Algo1 once over the complete dependency graph. Scheduling choices and
   connection choices belong to the same plan. Local tile recipes implement
   selected operators; they must not introduce a separately chosen global plan.
4. Encode selected candidates using the selected addresses and targets. Emit
   mother/local pages, descriptors, runtime layout and candidate connections.
   Bind every artifact to the same graph/hardware/plan fingerprints.
5. Run PR260 fast TLM on these artifacts. The evaluator interprets the plan and
   hardware arbitration; it must not remap operators, choose tiles, repair
   missing services with host arithmetic, or import sealed instruction pages.

## Acceptance

The complete original model must be covered; source operators may fuse only
when external dependencies remain represented. All emitted commands must have
an RTL-backed dispatch and completion. Candidate connections must match every
emitted data/control endpoint. The TLM receipt must identify the exact plan,
hardware, workload and timing model and report fast prefill/decode execution.
A diagnostic recipe graph, a symbolic plan, component RTL tests or successful
service registration alone does not meet these requirements.

The existing scalar finite-loop implementation is retained as diagnostic
evidence, not used as an archive fallback for this native compiler.

## Local program lifetime

A whole-graph deployment must not depend on a host installing a different U
program page for each operator. Use descriptor-fetching local kernels with
per-call operands, or an explicitly implemented hardware paging protocol.
The compact U images are useful service-execution evidence, not proof that
this whole-graph control requirement is already satisfied.

## Operand layout admission

value_layout.py resolves graph views to source element indices. operand_recipes.py derives per-operator row/tile requirements from graph shapes and edges, including causal Attention KV prefixes. The emitted segments are requirements, not free copies: a candidate must encode each necessary transfer or use an actual supported addressing mode. The same source address and output coverage checks apply before native candidate admission. The legacy RUN_LOOP search still present in compile_graph_input.py remains diagnostic until this candidate path replaces it.

Counted U transfer descriptors (DLC1/DSC1) encode materialization of non-contiguous source runs. native_u_candidates.py assembles the actual load/compute/store calls for RMS/Add after storage allocation. Candidate command generation alone does not provide a cost contract, choose a global binding or certify numerical input assets; those checks precede entry to the frontier.
