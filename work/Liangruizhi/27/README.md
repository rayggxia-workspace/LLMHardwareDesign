# Issue27 supporting evidence

Task: https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/27

Owner Liangruizhi; branch task/27-state-port-model; independent worktree
D:/Projects/LLMHardwareDesign-stateport. Source base is PR24 head
7e0e82b7175525b3e113c791b7f1fc499b249443. Temporary/development and formal outputs
use D:/Projects/Codex/state-port-study-20261022, never a new C-drive directory.

Formal code belongs in project/experiments/state_ports. These files retain
independent methodology/oracle review and delivery metadata. The generic oracle
toy values are normalized synthetic cycles, not Qwen or physical measurements.

Current source preparation: 20 scheduler/graph tests pass; a dirty-source
development sweep passed 3456 configurations (1224 feasible,2232 infeasible),
4896 policy schedules. This is exploratory, not the final clean-source result.
Formal source, actual capture, rerun and delivery records will supersede this
preparation paragraph with explicit immutable commits/results below.

Collaboration readback 2026-10-22: PR26 at2cd9ca15 reserves W8A8 matrix/INT32
accumulation but not KV/nonlinear formats. Its owner retains benchmark selection.
PR17 atc6379c18 still has no qualified paired parent PPA. We do not take over
those scopes. PR24 now reports head7e0e82b7 and its Project structure CI passed
(run39775448318); the earlier PR/API synchronization delay is resolved.

Registry remains pending management-hub PR5. No local board.json or Projects
tools; online board state unverified, synchronization pending, administrator
unassigned. This is not evidence of absent membership or absent permissions.

## Formal delivery

PR28: https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/28

Frozen source6ffb9417f0f01f614b733ce6c3ca9837906b3203 ran run-01/run-02 and capture-01/capture-02 from clean source. 25 code tests and6 independent toy tests passed. All8 scientific payload files are byte-identical. The491436B evidence.zip (13 members) has SHA256 f760dec66344c11fe9c7f04f55d91f610157d7ad624f6d66faa6a9bbdb1f1588. See docs/experiments/issue-27-state-port-model.md for conditional results, exact counts, raw captures and limits.

Independent final audits: graph27073 assertions/96 graphs,73 invalid contracts,7 mutated checker cases; capture399 checks/46 NPZ members; resource case Cartesian coverage3456,108 static groups,24 complete interval witnesses. The resource auditor did not independently replay every unarchived heuristic schedule. Original CRLF audit JSON bytes are retained; diff whitespace check uses cr-at-eol for these intentional raw artifacts while retaining other whitespace checks.

Development history: initial integrated capture unittest lacked a task tmp directory; final test uses process TEMP/TMP on D and passes. Old dev sweep config predates explicit endpoint staging; development-01-audit records that mismatch, and it is not a formal data failure. Graph checker originally missed4 invalid version/address probes; frozen old source and old report remain; final checks reject them. No failed result was promoted.

Source/schema/sample metadata and SHA are in original manifests. Head inputs in NPZ are observed eager tensors; tile states are computed by independent NumPy. Later graph audit scripts add validation only and do not change formal resource/model code. Endpoint staging stays an assumption, not a demonstrated FIFO-depth proof.
