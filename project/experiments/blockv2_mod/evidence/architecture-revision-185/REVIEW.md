# PR185 architecture correction — work in progress

Authority: PR185 head 234d4005a049c8cbe404710757d44871a571c598,
five-block-v1/2026-11-13 and the user's explicit instruction.
Only functional macros are hard boundaries. Logical groups define control ownership.
Selected product wiring is an Algo1 output, not an assumed P/U connection.

## Confirmed defects
1. native_graph_pipeline.py charges wrapper signal bits against group-center distance.
   A group rectangle is not a physical endpoint. This cost has no valid physical meaning.
2. native_projection_candidates.py requires a U/P PFED pair for every projection.
   Enumerating six pairs does not remove the preselected supply architecture.
3. projection_connections.py emits wrapper ports, without tracing them to macro
   or explicitly instantiated parent adapter pins.
4. Full elaboration jobs 114419/114420 prove arithmetic providers hidden inside
   service wrappers. See resource-mismatches.json and both XML files.
   Per P: three E32, one N32 and one dot core, beyond P's M/G/S inventory.
   Per U: two E32 and one block_v2_n in addition to registered N32/E16/S.
   P also instantiates S_base instead of the contract's S_P.
   Argmax is separately counted; its classification as reduction versus control
   must be resolved, not silently ignored.
5. Unchanged core files do not prove unchanged macro resources.
6. Current TLM service registration mirrors the old wrappers and cannot certify
   the corrected resource model.

## Required coherent correction
- Bind all 30 functional instances, nine controllers, actual program memories,
  and each soft adapter explicitly. No duplicate arithmetic hidden in services.
- Make service implementations consume declared macro endpoints and resources.
  Any required macro change gets a named mod version and explicit port/ABI delta.
- Separate genuinely fixed service/control edges from candidate product data edges.
  Retain real fixed edges only with source evidence. Do not infer all pairs connected.
- Candidate generation must enumerate compatible macro implementations and the
  actual necessary wiring. Neither pair names nor module hierarchy confer reachability.
- Generate the combined parent RTL from the selected same-plan endpoint bindings.
  No new hard P/U boundaries or magic metal multiplexers.
- Evaluate the exact selected instructions, resources, SRAM/DDR arbitration and
  chosen wiring. Full Qwen quick prefill/decode first; benchmark remainder afterwards.

## Evidence status
Jobs 114238, 114288, 114374, 114375 cancelled after architectural rejection.
Their artifacts are preserved as diagnostics; no corrected architecture pass.
The new expected inventory is a reference, not an accepted mod implementation.
RTL refactoring and full reevaluation are not yet complete.


## Implemented service/resource separation
- Five control-only modules under rtl/services; extraction manifest records
  original source hashes. These are parent service-controller ports, not
  P/U physical boundaries.
- Add/RoPE/RMS-apply enumerate C0/F0/J0/J1 E32; Gated enumerates P0/P1/P2 G32.
  Fifteen structural options, without selecting a product link.
- One registered three-client selector per existing E32, rather than one
  arithmetic copy per service. Selector holds ownership through both result beats.
  RTL job 114494 passed 96 real E32 operations under contention/backpressure/reset.
  Verilator 5.042 optimization crashed in jobs 114477/114489/114492; -O0 passed.
- Combined RMS remains unbound: block_v2_n is not the existing N32 ABI.
  The extracted apply stage binds existing E32; the reduction stage needs an
  explicit macro implementation decision. No renamed-core compatibility claim.
- Controller elaboration jobs 114453 and 114496 passed. Structural binding
  checker also rejects a missing E32 and attempts to assign E32 work to U.
- The old whole-graph native entry has NOT yet been migrated to these services.
  No full Qwen reevaluation has passed. Legacy wrapper tests are not new-base proof.


## N32 reduction macro revision
The previous missing block_v2_n interface is not renamed into N32. The new
n_s32_mod is an explicit N macro revision with one internal reduction engine.
RMS squares share the original scaling multipliers; division and square root
share the existing one group unit. Argmax reuses the maximum path.
Only cmd_mode[1:0] is added at the macro boundary. Epsilon, shifts and result
address use two acknowledged configuration commands over existing pins.
Scalar results commit through the existing 128-bit SRAM port; no scalar-result
parallel output port is added. See n32-mod-receipt.json for current hashes.

Jobs 114532/114533 validate 56 compiler-encoded NSV1 descriptors, 28 RMS and
14 Argmax numerical cases, 14 original-Softmax cycle comparisons, 3 service
abort/drain cases, 4 rejected descriptors, one divider and unchanged nonconstant
multiply-expression widths. This is macro/service evidence, not physical area
or a full Qwen run. The old wide-interface experiment was superseded before
integration; it is not the current macro port contract.

The monolithic RMS controller remains diagnostic only. Its supported replacement
is an N-mod factor stage and E32 application stage, with plan-selected data
movement. The complete graph pipeline has not yet been migrated.


## Current local projection correction
The parent local-source controller elaborated successfully in job 114551.
It uses an explicit S32 DDR source, staged K128 conversion, and native M input
protocol. The service declares M and S_P resources; P0/P1/P2 are three
unselected structural options. No U source or P/U COPY connection is mandatory.
Macro/adapter edges remain candidate edges even within one control group.
DDR arbitration, LC dispatch, complete graph integration and numerical projection
verification are pending. This is not a replacement full-Qwen acceptance result.

The response path checks the full published window identity before accepting
M input-load proof. SRAM error injection cannot accidentally alias an earlier
pipelined acknowledgement tag. Cancellation withdraws unpublished window
availability. Regeneration preserves the controller body and was checked for
idempotence. Functional verification of these changes is still required.

The full local source index is RTL_REVIEW_INDEX.md / rtl-review-coverage.json:
68 RTL files, with pending and rejected files explicitly distinguished from
unit evidence. This index is coverage, not proof that all files are reviewed.
External elaboration dependencies have separate hashes. Old whole-graph plan
and legacy group-as-leaf inventory outputs are explicitly diagnostic-only.
The corrected hardware/blockv2-mod-macros.json has 30 independent functional
macros and nine control owners, with mod_elaboration_accepted=false.

Selected connectivity fixture job 114553 also elaborated with one real
m_native_leaf_s32 and one local_s_p (four original SRAM banks), no U provider,
no extra E/N/dot core and no S_base substitution. This validates the selected
fixture's resource composition, not a whole-base acceptance or numeric run.
See projection-selected-structural-receipt.json for complete source hashes.

## Current full-K and graph-projection evidence
- Job 114576: actual M/S_P projection plus native descriptor dispatcher;
  four consecutive K=128/2048/11008/11008, N128 cases, 512 matching values,
  no reset between commands, three rejected descriptor/identity cases.
- Job 114578: real DRL1 -> SRAM -> DWS1 materialization, MPR1 projection,
  DWS1 result commit. Forty calls include one 16-segment K2048 input.
  Both actual SRAM results and committed DDR payloads match the independent
  integer reference. This is four projection cases, not full Qwen acceptance.
- Job 114579: every MatMul recipe in the existing full prefill and short decode
  graphs lowers for all three declared P control owners. Prefill: 145 tasks,
  4,966 tiles, 1,152 segmented tiles, 435 candidates, 36,708 calls. Decode:
  145 tasks, 2,483 tiles, 435 candidates, 14,898 calls. The generated artifacts
  are unselected candidates, not a DP-selected instruction package.
  Fused FFN and other operator families are outside this particular check.
- Projection candidate lowering generates actual load/store instructions for
  fragmented input. It neither changes source layout on the host nor assumes U/P.
- The extracted Add shim still contained the historical compact-U descriptor
  translation and fixed topology. It now exposes the full native descriptor,
  identity, cancellation and completion interface, with parameterized topology.
  Job 114580 elaborates it; numeric/whole-parent integration remains pending.
- Functional source snapshots are preserved under jobs 114576 and 114578.
  Old elaboration receipts are not rewritten using hashes of newer source files.

The complete objective remains open. Neither the old graph entry nor TLM has
been migrated to the full corrected nine-owner assembly. No current result
authorizes a full-Qwen, timing-calibration or physical-implementation pass.

## FFN candidates and explicit E32 MAC revision
- Job 114600 lowers every one of the 36 graph FFN tasks for all nine M-owner /
  G-owner combinations in both prefill and short decode. Each graph yields
  324 unselected candidates, including 216 with different control owners.
  Inputs, intermediates and outputs use explicit native DDR load/store calls.
  This is not a DP-selected full plan or an executed full FFN.
- The projection service assembly now dispatches MPR1, DRL1, DWS1 and GSM1.
  The G service preserves the actual CALL ticket through completion instead
  of dropping it. Job 114602 checks 512 projection values plus 128 G values
  over 44 calls; 114624 proves one M, one G32 and one S_P in the selected
  connectivity fixture, without hidden E/N/dot instances.
- e_s32_mac_ap64 is an explicit candidate E macro revision, NOT a hidden
  parent dot engine. Its external pins match e_s32_ap64 exactly. Four S80
  accumulators support up to 65,535 signed products per lane with one final
  rounding. Original multiply-expression widths/counts are unchanged:
  four width-32 and four width-33 expressions, not a physical gate estimate.
- Job 114616 verifies 70,648 commands, including 204 old-operation cycle
  comparisons and exact full-K numerical references. Job 114623 checks
  ownership retention across MAC commands under a competing service;
  114622 repeats the original shared-selector behavior.
- Superseded by the update below: the E32 revision is now installed in the
  candidate inventory and EMD1 has a verified native service. Full parent and
  same-plan TLM acceptance remain pending.
- Full Qwen acceptance remains false. Benchmarks beyond Qwen have not started.


## Native dot and Attention candidate update
- Job 114666 executes EMD1 using one actual E32 MAC, its registered selector,
  and S_base. Seven numerical cases cover strided QK/AV layouts and K up to
  65535; three cancellation phases, two DDR faults and three descriptor rejects
  pass without resetting between cases. Source snapshots and hashes are frozen
  in e32-dot-service-receipt.json. This is not a full Attention execution.
- Job 114669 confirms one E macro and one S_base in the selected fixture.
  No separate dot macro is added. The candidate inventory still contains the
  original 30 functional instances and nine control owners.
- Job 114680 elaborates E32 and N32 parent service assemblies. A hierarchy gate
  rejects hidden arithmetic/storage macros; its negative check rejects the
  functional fixture. Parent controls themselves are not physical blocks.
- Job 114697 failed because its checker obtained only the legacy controller
  IDs. The checker now uses an explicit nine-controller ID assignment, without
  consuming the rejected old hardware inventory. Job 114700 passes both graphs.
- Each graph has 36 Attention tasks and 288 unselected E/N mapping candidates.
  Prefill: 1152 rows and 350208 calls across all candidates. Short decode:
  576 rows and 175104 calls. These are NOT counts of a selected executable plan.
- Attention candidates explicitly commit/load scores and probabilities between
  selected resources. N32 Softmax produces Q16 probabilities; AV uses shift 16.
  A finite DDR staging path is an implementation choice, not a claim that all
  valid future candidates must communicate through DDR.
- Current review coverage: 75 RTL files; 6 rejected, 22 with matching unit
  evidence, 44 pending full review, 3 replacements in progress. No complete
  RTL review, whole-base acceptance, full instruction package, physical wiring
  acceptance, or corrected TLM throughput result is claimed.


## Candidate resource admission
- All MatMul, FFN and Attention lowerers now enforce real SRAM capacity,
  descriptor footprint containment, CALL identity, implemented descriptor routes,
  existing adapter identity, and local-controller ownership.
- A controller is a capacity-one scheduling resource, not a physical block.
  SRAM reservations persist through the candidate's final output commit;
  individual CALL completion does not silently free intermediate values.
- Jobs 114715/114716/114717 regenerate the complete prefill and short-decode
  candidate sets. Job 114720 rechecks all six streams with the current admission
  implementation and freezes source hashes. It covers 2094 candidates and
  1276758 calls, plus 18 negative checks (capacity, missing LC, wrong target,
  cyclic dependency, forged transfer metadata, invented active adapter).
- Job 114719 failed at Python parse time; it produced no acceptance evidence.
  Job 114720 is the corrected execution, not a reuse of the failed receipt.
- These checks do not implement or prove global DP scheduling, dataflow
  correctness, full SRAM endpoint wiring, or numerical Qwen acceptance.
  Add/RMSNorm/RoPE/Gather and decode Concat still require the corrected native
  path; View handling must preserve source storage and dependency semantics.


## Native Add integrated into shared E32 parent controls
- Add now propagates SRAM response errors instead of tying them off inside the
  service. Error-free tie belongs at the actual S_base binding. The extraction
  normalizer preserves this change and is idempotent.
- E32 parent controls dispatch EMD1, Add (3/7/2), DRL1 and DWS1. Add uses the
  registered E selector slot 0, dot slot 3; unused slots remain inactive.
  SRAM has the existing four-client finite arbiter. No extra arithmetic macro.
- Parent elaboration job 114730 confirms one E selector and one SRAM arbiter,
  and no embedded functional macros. Functional job 114733 uses actual E32 MAC
  and S_base: 256 Add values and eight dot numerical cases, maximum K65535,
  plus the dot cancellation/fault/reject suite, without reset between services.
  Source snapshot is in e32-add-cluster-receipt.json.
- Job 114731 failed because the adapted testbench timeout diagnostic referenced
  the old hierarchy; it did not produce functional evidence. Job 114733 corrects
  that reference. No functional assertion was removed.
- Job 114732 lowers all 180 Add tasks for four E owners on each graph:
  720 candidates / 59904 calls for prefill, 720 / 29952 for short decode.
  Explicit loads and committed stores surround every native Add command.
- Full graph selection, final instruction pages/wiring, RMSNorm/RoPE/Gather/
  Concat integration and corrected quick TLM acceptance remain incomplete.


## RoPE native service extraction
- Preserved existing RPE1 descriptor validation, row operand gathering, completion
  and cancellation draining. Replaced the embedded E commit wrapper with the
  control-only RoPE word service, exposing actual selected E macro ports.
- New parent hierarchy: rope_native_service_controller -> rope_native_row ->
  rope_s32_service_controller -> rope_e32_ap64. Job 114736 confirms exactly
  those four control modules, with no embedded E/N/M/S functional macro.
- Job 114734 executes eight cases using actual E32 MAC and S_base, selector
  client slot 1. It checks 768 result values across identity, half-split rotation,
  sum and negative coefficients, one cancellation, two descriptor rejections
  and recovery without resets. This does not establish arbitrary coefficient
  accuracy, full graph RoPE, or whole-Qwen numeric acceptance.
- The native service has not yet been connected into the shared E dispatcher
  and shared SRAM client paths. Existing Add/dot assembly evidence remains
  scoped to its recorded source snapshot; no new RoPE dispatch route is claimed.


## RoPE shared dispatcher and full graph candidate integration
- E parent dispatch now implements dot, Add, RoPE, load and store. RoPE uses
  the already declared E selector slot 1; there are still four hardware slots.
  The native wrapper and word controller are aliases for one service path,
  not two independent selector clients.
- Add/RoPE SRAM requests share an explicitly registered s128_serial_pair parent
  adapter. It latches requester ownership before issuing and retains it through
  response consumption. This is real parent RTL, not an active switch invented
  during product wiring. Parent resource/endpoint registration remains partial
  for the complete nine-controller implementation.
- Job 114755 confirms one E selector, one four-client SRAM arbiter and one
  serial pair selector, with no hidden functional macros in parent controls.
- Job 114757 passes RoPE/Add interleaving without reset (896 RoPE values,
  256 Add values, cancellation/rejection/recovery). Job 114756 repeats the
  full dot/Add regression including K65535 and faults on this revised cluster.
- Job 114758 lowers all 72 RoPE tasks on each graph for four E owners:
  288 candidates with 25920 calls in prefill and 12960 in short decode.
  Candidate operand loads, RoPE calls and DDR output commits are explicit.
- These results do not select a global plan or execute the full model.
  RMSNorm, Gather/Concat, final instruction pages/wiring and TLM remain open.


## RMS application and graph-derived factor handoff
- RMA1 reads a committed NSV1 RMS factor packet from allocated SRAM. It validates
  packet mode/index/reserved bits and derives baseline = shift - extra_shift,
  then factor shift = 14 + baseline for Q16 activation/output. Gamma shift is
  explicit. The two products use the selected E macro; there is no parent
  arithmetic core or host-computed factor.
- Shared dispatch now supports RMA1 in E client slot 2. Add/RoPE/RMS use the
  explicitly registered three-client s128_service_selector; its granted owner
  is held through response consumption. Macro count and E selector slots stay
  unchanged. This supersedes the two-client adapter for this parent build.
- Job 114783 executes 896 RMS application values and 256 Add values without
  reset, including cancellation and invalid descriptor/packet rejection.
  114769 tests the native service alone. These fixtures supply factor packets:
  they do not yet execute the full N reduction -> DDR -> E application chain.
- Job 114780 confirms no hidden functional macros in parent service controls.
  114781/114782 rerun dot/Add and RoPE/Add numerical suites on this revision.
- The RMS graph lowerer emits actual N factor commands, committed stores/loads
  for the factor packet, E application commands and output commits. It preserves
  one factor for the complete reduction while applying 128-element chunks.
  The packet may replace N source word zero only after the reduction finishes.
- Whole-model numerical acceptance, global DP selection, final native pages,
  selected physical endpoint connections and corrected TLM remain open.


## Concat native transfer candidates
- Concat no longer depends on the old U counted-transfer ABI. Its new lowerer
  emits implemented DRL1/DWS1 row commands for any selected control owner with
  declared private SRAM. It rejects source/output overlap, gaps, duplicate
  destination writes, unsupported segment alignment and out-of-range operands.
- Job 114785 compiles all 72 short-decode Concat tasks for nine control owners:
  648 candidates, 7776 calls. Prefill contains no Concat tasks; an empty result
  there is not evidence of executing Concat.
- Job 114786 independently interprets the executable descriptors' address and
  SRAM fields and compares every output value against graph segments for all
  648 candidates. A mutated source address is rejected. This verifies descriptor
  data effects, not RTL timing or a complete TLM model.
- Candidates explicitly retain unresolved parent SRAM/DDR endpoint bindings.
  An empty candidate connection list is not a claim that transfers are wired.
- Gather still uses a legacy fixed-width runtime-index/DMA path and has not
  been admitted into the corrected nine-owner service assembly. It requires
  real runtime index handling, not an archived token or host-selected row.
- Full graph DP selection, final instruction pages and same-plan wiring,
  complete N-to-E RMS numerical execution and Qwen TLM acceptance remain open.


## Runtime-index Gather and N parent integration
- GTH2 reads the actual signed 32/64-bit index from DDR, normalizes negative
  indices, rejects out-of-range values, computes a power-of-two row address,
  and copies the selected slice through ordinary SRAM write acknowledgements.
  A table row is never selected on the host or embedded as a fixed token.
- Service is parent DMA/address control, with one outstanding DDR read and one
  64-byte data buffer. No functional compute macro is added. Cancellation
  drains an offered/accepted operation before reporting; partial output is not
  published as success. Error tags and DDR/SRAM errors propagate.
- Job 114788 validates actual S_base data for 32/64-bit and negative indices,
  out-of-range 64-bit values (no truncation), maximum 16 KiB payload, bad tags,
  DDR errors, cancellation and recovery without resets.
- Job 114809 runs the same service through the N parent dispatcher/DDR and SRAM
  arbiters and switches to actual N Argmax then back to Gather without reset.
  Job 114799 confirms no hidden functional macros inside parent controls.
- Graph candidates carry the runtime index address and exact storage width.
  INT64 graph input narrowed by an existing input materializer still requires
  an explicit representability check; the RTL itself also supports INT64.
  Candidate connection lists retain unresolved shared DDR/SRAM endpoint work.
- Full graph selection and instruction pages, complete same-plan connections,
  end-to-end RMS numerical execution and corrected Qwen TLM remain unaccepted.


## Unified corrected graph frontend
- compiler/run_macro_graph_frontend.py accepts graph/recipes/layouts, the actual
  macro hardware inventory, and service contracts. It verifies source identity,
  builds one storage allocation, resolves View dependencies independently of
  source traversal order, and generates all corrected native candidate families.
- Storage allocation is now separate from the rejected legacy graph scheduler.
  No old plan, archived instruction package, group-center wire cost or mandatory
  U/P pairing is read. Candidate-specific workspaces have distinct allocations.
- Job 114811 completes both full graphs in one entry: prefill 543 executable
  tasks, 540 views, 2641 candidates; short decode 615 executable tasks, 540 views,
  3289 candidates. Aggregate call counts across alternatives are 1036372 and
  522506 respectively, NOT final instruction-stream lengths.
- Independent job 114821 re-reads every candidate stream, checks checksums,
  source/task coverage, dependency order and resource admission. It verifies
  reordered View chains and rejects four malformed graph classes.
- Frozen sources and input hashes are under macro-graph-frontend-114811.
  This is a unified candidate frontend, not yet a global DP-selected plan,
  complete endpoint wiring solution, machine package or Qwen TLM execution.


## Macro/LC DP selection and complete graph machine packages
- Native macro selection now adapts actual macro, LC and registered parent
  adapter capacities into the bounded frontier DP. No control-group identity
  appears as a functional macro lease. SRAM is reserved through candidate
  final commit; re-encoding adds graph and resource completion dependencies.
- The ranking model is explicitly structural work units, not predicted cycles.
  It estimates descriptor/memory/arithmetic work; shared DDR contention, wire
  optimization and physical timing are NOT validated by this selection.
- Job 114823 selects all 543 prefill and 615 short-decode tasks and re-encodes
  them with monotone deployment identities: 141490 and 70457 native calls.
  Independent verification replays the DP and checks graph/resource edges.
- Job 114824 generates descriptor bytes, local kernel and MC binary programs:
  13 prefill mother pages and 4 short-decode pages. Both receive independent
  start/completion ordering checks. The modern packager validates plan content
  hash and every descriptor's declared target/schema/ABI/topology, and consumes
  the corrected macro inventory rather than the legacy group inventory.
- candidate-wiring.json intentionally remains incomplete: it contains selected
  compute endpoint requirements but lacks complete SRAM/DDR/control binding.
  It is not a complete physical candidate solution and delivery_accepted=false.
- The packages have not yet run against joined corrected RTL/TLM providers.
  No throughput, full-Qwen numerical acceptance or physical wiring acceptance
  is inferred from successful binary packaging.


## Actual endpoint and LC/service structure integration
- Generated P/N/E parent control assemblies join the native LC with the
  corresponding service cluster. Fourteen service pins are internal checked
  connections. These assemblies are standard-cell hierarchy, not hard blocks.
- Job 114847 elaborates all three assemblies with one native LC each and no
  embedded functional M/E/N/G/S macro. Job 114846 selected the old quantizer
  library during elaboration; the corrected search path explicitly uses the
  already verified mod quantizer. No RTL requirement was weakened.
- Selected endpoint binding now reads actual RTL port contracts and checks
  selected-plan hash, service-source hash, direction, width and unique drivers.
  Each plan has 153 compute/SRAM connections and 42 explicit inactive/error
  ties. Unused macro services do not acquire automatic product connections.
- Fifteen external interface groups remain unresolved in each plan: typed M
  weight DMA, service read/write DMA, LC scope DMA and MC control/config/session.
  No physical wire-length or timing estimate is assigned to these missing links.
- Existing typed DMA has 12 registered clients (nine LC and three M), with
  ordinary LC requests paired into 128-byte records; arbitrary native 64-byte
  mode is currently limited to the three P client slots. New 64-bit service
  tags cannot simply be wired to its 32-bit client tags. A real adapter/sharing
  design and write path are still required, with corresponding timing costs.
- The new endpoint artifacts are bound to the selected plan hashes but remain
  incomplete. Existing sealed instruction packages are not retroactively
  relabeled as having complete wiring or executable TLM acceptance.

## Current architecture gate and shared read transport (jobs 114860–114893)

The parent-control deny list previously omitted G32's actual g_s32 master,
compact G/E, R and T. The gate now derives functional masters from both PR185
and the explicit mod inventory, checks the complete recorded hierarchy, and
rejects stale source hashes or undeclared control instances. Graph compilation
and modern plan packaging invoke this check. Twelve negative cases pass.
This is structural admission, not complete assembly acceptance.

The review index now separates rejected implementations, functional unit
evidence, current control-structure evidence, and retained unselected RTL.
Unselected/unreviewed files are not approved merely because the current path
does not use them. External dependency coverage now includes the current three
parent hierarchies (50 frozen RTL dependencies), not only the old projection
fixture. The complete review remains unfinished.

Both full graph inputs were checked after the gate change: prefill 543 tasks,
2,641 choices and 141,490 sealed native calls; decode 615 tasks, 3,289 choices
and 70,457 calls. The known 153 endpoint connections have no static metal
conflict across phases; 15 interface groups remain unresolved. No TLM run or
full program execution is implied by this check.

native_shared_read_dma is an explicit parent standard-cell revision with
LC descriptor clients 0..8, M weight clients 9..11, and 64-byte service clients
12..20. This changes controller ownership state, not DDR bandwidth or credits:
two channels, two lanes per channel, 32 entries/descriptors per channel,
three 64-byte return skids per channel, four issues per rolling three cycles.
The global DDR tag stays 64 bits. Area has not been synthesized.
It does not prescribe any U/P data connection.

Job 114873 passes four mixed-client stresses, including serial-limit=3;
each has 6,314 accepted operations, 6,313 returns and one reservation cancel.
Job 114883 passes three integrated nine-client serial-adapter stresses,
1,800 full-tag requests each and 443–444 real fence completions. The adapter
keeps the full 64-bit caller tag; namespace reuse follows a matching physical
fence. Read transport sources and test outputs are frozen in their job folders.
The first test launch 114870 failed from host glibc incompatibility; the existing
container wrapper fixes the environment. Job 114871 was superseded after
correcting a generator cast-width substitution; current evidence is 114873.

This read-transport candidate is not yet bound into the selected plans.
Remaining work: shared writes, explicit MC/LC/control/data endpoint bindings,
full nine-owner assembly, regeneration of both plans against that base revision,
then joined fast Qwen prefill/decode evaluation. No P512/D128 128-token run.

## Complete selected RTL assembly and same-plan bound packages

The read-only transport revision is superseded for current integration by
native_shared_memory_dma/native_shared_memory_plane. LC clients 0..8, M weight
clients 9..11, native reads 12..20 and writes 21..29 share the same 64 transport
entries, six return skids and rolling four issues per three cycles/channel.
Nine write owners add 576 bytes of explicit parent payload registers; this is
not added private SRAM. Writes retire only after backend commit ACK; its error
bit returns to the original full 64-bit owner tag. Current jobs 114903/114898
pass mixed 30-client transport and 18-service read/write stresses including
short serial namespaces, stalls, 54 write errors/run, and shared bandwidth.

Jobs 114899/114900 elaborate the nine-controller plane and selected product.
Audit 114902 finds exactly the original thirty independent functional macros,
all nine correct LC IDs, finite MC/LC program stores, one shared memory transport
and eighteen serial adapters. A hidden extra G negative case is rejected.
Inactive functional inputs are tied only in this selected product fixture;
they are not registered as fixed base data paths. Only the six selected owners
acquire service memory data links. No P/U connection is presumed.

New RTL base: blockv2-mod-pr185-memory-c6ef5d0bffff12ab, in
hardware/blockv2-mod-shared-memory.json. Product-specific assembly sources are
excluded from the common base hash. Old MC/switch ODB hashes are retained only
as reference evidence; new physical acceptance is false. Default MC service
stall bound is explicitly 100000000 cycles, with finite 16 KiB MC and 1 KiB/LC PM.

Full graph recompilation 114904 generates 141490 prefill calls and 70457 decode
calls on this base. Materializer 114907 consumes these actual plans (no archived
plan substitution), reproduces the selected RTL byte-for-byte against complete
assembly evidence, and emits native-product-wiring/1. The builders now accept
the selected wiring/base as arguments rather than a fixed earlier job path.

Bound packaging 114908 and independent verification 114909 produce 13/4 MC
pages, a 352-byte LC kernel, descriptors, hardware and complete RTL candidate
wiring. All binary programs match the selected-plan encoding before wiring
materialization. Wrong base, wrong plan, extra macro, changed source identity
and incomplete wiring are rejected. Intermediate compute requirements are
named separately; candidate-wiring.json is the resolved product bundle.
RTL completeness does not imply physical wiring or Qwen execution acceptance.

The current TLM registry still targets the rejected legacy wrapper model and
must be replaced/adapted before execution. No corrected TLM/Qwen acceptance is
claimed. The next entry is the two packages under shared-memory-bound-packages-114908,
with shared-memory-product-114907 and the current hardware file.

## Complete assembly admission hardening and macro-model regression

A second review found that the complete assembly checker rejected named functional
cores but did not reject all unknown or renamed parent instances. Parent controls
now match the exact registered instance paths and masters, including program
stores, adapters, quantizers and transport. The selected product itself must
declare hard_boundary=false. This registry is a structural resource contract,
not a synthesized area estimate.

All 32 previously unclassified historical files now have an explicit architectural
disposition, together with the 13 previously rejected files. These 45 sources are
excluded from current production elaboration. Reasons distinguish unregistered
arithmetic, transitive rejected wrappers, legacy supply topology, legacy ABI
controls, unselected adapters and a testbench. Retaining a helper for reference
does not assert that the helper is inherently invalid; reuse requires explicit
resource and endpoint admission. Historical functional verification is not claimed.

Job 114958 re-elaborates the complete selected nine-owner/thirty-macro design.
Job 114959 applies the final checker to that elaboration: 51 negative cases
include renamed arithmetic, duplicate quantization logic, hidden G/Argmax,
changed ownership, composite hard boundary and each excluded source.
Both existing full prefill/decode plan-package/wiring joins pass again.
No RTL bytes were changed during this admission-hardening pass, and existing
functional RTL receipts retain their original evidence scope.

Job 114969 tests the new macro-bound TLM arithmetic with 56 frozen N32 RTL cases,
six frozen E32 dot RTL cases, and 256 projection cases compared with PR260's
integer reference progression. DDR tests distinguish uncommitted data from valid
zero, preserve unknown padding and permit committed workspace reuse.
These are provider contract regressions. New full-Qwen TLM execution, joined
MC/LC program execution and timing calibration remain incomplete.

## Macro-bound full-package execution entry and real assets

The new entry tlm/run_macro_package.py uses the exact sealed instruction pages,
declared macro providers, nine actual SRAM model instances, and thirty-client
shared transport. MacroScheduler routes LC descriptor reads through clients 0..8;
M reads and service reads/writes use their own registered client classes.
Programs are modeled as preinstalled; PM loading time is explicitly excluded.
Detailed service timing remains uncalibrated, so execution alone cannot approve
a calibrated throughput claim.

Job 115001 binds all 141490 prefill and 70457 decode CALLs across 22 used routes.
This is complete provider coverage, not execution of both programs.
Job 114989 materializes all 438 prefill assets from actual checkpoint tensors,
source-graph transpose recipes and ONNX constants. Every image is sealed.
The initial asset job 114979 rejected Constant-node RoPE data; the preparer
now handles actual ONNX tensor Constant nodes as well as initializers.

Job 115013 produces independent full-model FP32 logits and KV for tokens [1,2].
Its checkpoint hashes exactly match the materialized images. Earlier reference
job 115011 produced logits but failed during KV export due to the installed
DynamicCache API; the actual layers/keys/values API is now used.

First execution job 114990 failed at DRAMsim3 dynamic-library loading due to host
glibc. Job 115012 uses the existing container and is now executing the full short
prefill with real inputs and DDR callbacks. It must be polled to terminal state;
do not restart merely because a chat turn ends. No full Qwen or decode execution
acceptance is recorded. Check receipt.json and the Slurm job/log before any retry.
Source snapshot: macro-execution-sources-115012.

## Real DRAM batching, complete numeric oracle and next-stage state preparation

Jobs 115018/115020 compare original and batched DRAMsim3 callbacks. The batch
bridge advances the same memory models only before the next external event and
stops at the first return. Queued requests retain their ordinary offer cycles.
Three original busy cases and three cases with source windows 1/4/24 have exact
callback timestamps/order and matching original DDR counters. Sparse cases take
about one third of the original wall time; full-service speedup is smaller.

The full prefill prefix in jobs 115012/115034 has identical reported timestamps
through 2500 calls. The original slow job was then cancelled, with evidence in
dram-batch-whole-plan-prefix.json. The current real-data run is 115034; poll that
job, do not restart it on a chat boundary. It has a 90-minute Slurm limit.
An attempted increase was denied by Slurm; no new authorization is needed for
the active run, and no time-limit change is claimed.

The independent untimed graph oracle does not read selected instructions or TLM
providers. Job 115050 evaluates all 36 layers and logits in about 20 seconds.
Job 115052 checks its vectorized matrix math against 512 actual M RTL reference
values (K128/2048/11008). Full-model native top1 matches FP32 at both positions;
cosines are 0.99547346/0.99928275, relative L2 0.09701747/0.03788248.
These are quality metrics, not a general quantization-accuracy acceptance policy.
Job 115054 preserves all 651 produced tensors and FFN intermediates (17026048
bytes); its logits hash is unchanged. The TLM must match these bytes exactly.

The running new entry will preserve actual committed DDR bytes with byte-valid
masks. Job 115046 derives all 72 decode KV input mappings from the source/dest
graphs and compiled source-index views. No zero-history KV is substituted.
Scene job 115058 waits for successful 115034 and 115054, then checks every
produced tensor before preparing decode data. It reuses sealed static images and
takes a greedy token from actual prefill logits. This is external short-stage
input preparation: view relocation, host sampling and PM/initial loading time
are excluded. It is not a generated hardware phase-transfer program and cannot
support a continuous-request throughput claim. Decode execution remains pending.

Current working-source snapshot: phase-numeric-sources-115058. Full Qwen and
remaining benchmark acceptance are still open.

## Current execution handle correction and fixed LC-program admission

At the measured rate, the 90-minute limit on job 115034 was inadequate. Slurm
refused an in-place increase. The run was cancelled at about 17.5 minutes and
the identical two-token prefill package/model was submitted as 115069 with a
three-hour limit; this is not P512/D128 and does not change workload scope.
Dependent scene job 115058 was replaced by 115071, afterok:115069:115054.
Only these current handles should be followed. The lost run time is recorded,
not portrayed as a server stall or successful full execution.

The generic package loader previously checked seals but did not explicitly
reject a different local program when using the fixed TLM descriptor kernel.
It now requires the supported EXEC -> WAIT -> RETURN image and matching
deployment topology/image identity. Job 115082 checks both complete packages
and twelve altered-program cases. This is admission hardening; current selected
binary programs remain unchanged and loading time is still excluded.

## Complete queued decode verification chain

The live short-prefill job remains 115069. After successful full-prefill execution
and the 651-tensor comparison, scene job 115071 prepares actual KV/token inputs.
Jobs 115084 and 115085 then execute the complete decode instruction package and
independent fixed-point operand graph, respectively. Job 115086 compares every
produced tensor byte-for-byte. Job 115098 independently computes FP32 prefill and
decode using the actual native-selected next input token; 115100 reports complete
decode logit quality metrics. These jobs are dependency-gated, not claimed passed.
The authoritative job/result mapping is current-evaluation-pipeline.json.
Remaining benchmark conversion is not started before Qwen acceptance.

## User-facing entry correction

The root README still led with the historical group-level inventory and symbolic
entry. It is now rewritten around the current thirty-macro hardware, graph input,
native candidate selection, selected-product evidence, packaging and evaluator.
The previous text is preserved under evidence/history with an explicit historical
header and original SHA256 in its filename.

algo1_blockv2_mod.py now requires --legacy-symbolic-diagnostic before importing
legacy providers. algo1.sbatch exits with a retirement error; deliberate historical
reproduction is available as legacy_symbolic_diagnostic.sbatch. Both default
rejection paths were executed and returned 2. This changes no current native
compiler or running TLM model. See entry-cleanup-receipt.json.

## Remaining benchmark execution preparation

Prepared tests/convert_remaining_benchmarks.py and its Slurm entry. Each of the 20 catalog graphs is independently attempted through source hashing, ONNX import, semantic recognition, layout and operand lowering, native macro candidate generation and Algo1 selection. Failures retain stage, source and traceback/log; a selected plan is explicitly not a machine package or TLM pass. The launcher requires a Qwen acceptance receipt bound to evidence hashes. Only Python/shell syntax was checked; no remaining benchmark conversion has started.

## Complete comparison evidence binding

The complete tensor comparison now rejects incomplete CALL retirement, an empty or incorrectly typed reference, and committed DDR state from different runtime assets. Exact and FP32 reports bind their execution/reference receipts and comparison source hashes; exact reports also bind committed DDR state. This does not alter the running job or its arithmetic/timing. Python syntax checked; actual full comparisons remain pending jobs 115071 and 115086.

## Complete short prefill passed, real-KV decode started

Job 115069 completed all 141490 calls and 13 mother pages with no active calls left. Job 115071 checked all 651 produced tensors (17026048 bytes) exactly against the independent fixed-point graph oracle: zero mismatches. Both prefill positions agree with FP32 top-1; detailed accuracy metrics remain separate from broad model qualification. Kernel time is 1601322395079 ps with uncalibrated service timing. Actual committed KV and native greedy token 16 prepared the decode assets; job 115084 is running. Decode oracle 115085 produced 723 tensors. Overall Qwen acceptance remains false pending complete decode and review. See prefill-complete-milestone.json for evidence hashes.
