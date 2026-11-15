# blockv2-mod: current macro-native Algo1 flow

This remote working directory belongs to Issue 219. Architecture authority is
PR185 commit 234d4005a049c8cbe404710757d44871a571c598.

## Architecture and inputs

The nine P/U/C/F/J groups are control owners, never composite hard macros.
Thirty functional macro instances are declared independently. Parent controls,
program stores, selectors and transport resources are explicit. Data links,
including same-owner links, require selected endpoint bindings; no U/P data
connection is assumed.

Current inputs:
- [Hardware](hardware/blockv2-mod-shared-memory.json), base
  blockv2-mod-pr185-memory-c6ef5d0bffff12ab.
- [Service contracts](hardware/service-controller-contracts.json).
- One graph directory containing native-recipe-graph.json,
  native-operand-recipes.json and native-value-layout.json, bound to the same
  source model. These are graph/operand/index descriptions, not archived plans.

The old blockv2-mod-nine.json and algo1/blockv2-mod.json inventories are historical.

## Compilation

Run computation inside a Slurm allocation with the Python/module paths from
reproducibility/environment.json.

~~~sh
python compiler/run_macro_graph_frontend.py --graph-directory "$graph" --hardware hardware/blockv2-mod-shared-memory.json --services hardware/service-controller-contracts.json --output "$out/candidates"
python compiler/run_macro_selection.py --graph-directory "$graph" --candidate-directory "$out/candidates" --hardware hardware/blockv2-mod-shared-memory.json --services hardware/service-controller-contracts.json --output "$out/plan"
~~~

Selection emits native service descriptors, CALL dependencies, resource
reservations and required connections. Ranking currently uses an uncalibrated
work proxy, not measured cycles.

compiler/materialize_native_product.py combines selected plans into static
macro/parent endpoint wiring and generates the selected RTL assembly. It requires
source-matching complete assembly evidence. A different connection set requires
its own elaboration; an old product receipt cannot approve it. The resulting
candidate-wiring.json has schema native-product-wiring/1.

~~~sh
python compiler/package_native_plan.py "$out/plan/plan.json" "$out/package" "$product/candidate-wiring.json"
~~~

The package contains mother images, a finite local EXEC/WAIT/RETURN kernel,
descriptors, deployment transactions, hardware and same-plan candidate wiring.
The runtime rejects incomplete RTL wiring and unsupported local kernel programs.
These compilation stages do not substitute archived stage machine code.

## Current complete graph artifacts

All paths below are under evidence/architecture-revision-185/.

| Artifact | Evidence scope |
| --- | --- |
| shared-memory-graphs-114904 | Full 36-layer prefill and short decode selected plans |
| shared-memory-product-114907 | Same-plan macro/parent candidate endpoint wiring |
| shared-memory-bound-packages-114908 | 141490/70457 CALLs and 13/4 mother pages |
| selected-nine-assembly-114958 | Thirty-macro/nine-controller complete elaboration |
| pr185-admission-114959 | Structural admission and 51 rejected violation cases |
| current-evaluation-pipeline.json | Current jobs, dependencies and result paths |
| REVIEW.md and status.json | Evidence history and incomplete work |

Candidate RTL wiring is not physical routing/PPA acceptance.

## Evaluation and current limits

tlm/run_macro_package.py consumes a sealed selected package and graph-bound
runtime images. It models actual SRAM instances and shared read/write transport.
tlm/run_native_package.py is the older diagnostic-zero evaluator.

Short Qwen evaluation uses full two-token prefill and one history-two decode,
real weights and prefill-produced KV. The untimed graph oracle is an independent
numerical reference; its wall time is never reported as TLM throughput.
Every produced tensor must match the reference byte-for-byte.

Program loading and external stage input preparation/sampling are excluded from
reported kernel time. Macro timing remains uncalibrated. No continuous-request
throughput or physical timing acceptance is claimed. Complete short Qwen functional acceptance is recorded in
evidence/architecture-revision-185/Qwen-short-acceptance-115200.json.
Both full stages and all 1374 reference tensors passed. The remaining 20
benchmark graphs were attempted; all stop in layout/operand lowering, before
candidate selection. See evidence/architecture-revision-185/RESULTS_ZH.md and
remaining-benchmark-conversion-115202/summary.json. This is not broad model
accuracy, physical timing, or remaining-benchmark acceptance. P512/D128 128-token runs are
explicitly excluded.

## Historical entry points

algo1_blockv2_mod.py is the retired symbolic prototype, which emits no hardware
instruction package. It requires --legacy-symbolic-diagnostic. algo1.sbatch now
exits with a retirement error. legacy_symbolic_diagnostic.sbatch retains explicit
historical reproduction. Archived stage diagnostics are not the current compiler.

The previous README is preserved in:
evidence/history/README-before-pr185-627b3e6105fd.md

hardware/pr185-historical-source-disposition.json records the legacy RTL policy.
Forty-five historical/rejected sources are excluded from current production
elaboration. Their retained evidence does not admit them into the new base.

## Joint dirty range frontier (integration under evaluation)

The opt-in frontend flags `--joint --range-tiles 1` expose actual native commit
units. Selection then jointly searches ready source ranges, registered service
bindings, SRAM placement, retention and explicit DDR commits. `--depth` bounds
unfinished source-operator ancestry; `--width` bounds the search beam.

`--export-value VALUE` declares persistent state in addition to graph outputs.
These live-outs must have committed DDR copies. Short prefill evaluation exports
the 72 KV roots consumed by decode; decode includes its 72 present-KV outputs.
Do not omit state merely because it is not named as a final logit output.

`--incumbent-plan PATH` preserves an executable plan from the identical graph,
hardware and allocation as a fallback under the stated structural objective.
The searched candidate remains saved separately. This objective is DDR traffic
followed by structural work; it is not calibrated throughput.

Dirty data may be consumed locally without DWS/DRL, spilled by real existing
commands when required, or released after its last reader. Rewritten descriptors
are checked against the actual hardware routes and SRAM capacity before emission.
MPR1 still requires a full-K DDR input, so it cannot consume a dirty SRAM input
or continue a partial K reduction merely because the search permits overlap.

See [current integration scope](audits/JOINT_FRONTIER_STATUS.md) and
[RTL continuation responsibilities](audits/RANGE_RTL_ALIGNMENT.md). The complete
short-request execution uses `audits/run_joint_request.sbatch`, comparing final
outputs and declared KV against the independent integer reference. It must not
require elided intermediate DDR copies or substitute a different execution plan.

The next scheduling revision adds selection flags `--stage-resources`,
`--diverse-search`, and `--objective finish_proxy`. Its CALL dependency graph
releases each owner after its own last stage and retains shared-workspace leases.
The mother program waits on individual predicted completions to avoid joining
unrelated live commands into one barrier. This uses existing WAIT mask semantics.

Producer mappings/ranges are chosen before dependent consumer ranges. Independent
branches can be chosen in either order; construction order does not serialize
their hardware execution. See [stage scheduling status](audits/STAGE_FRONTIER_STATUS.md).
Full TLM acceptance of this revision is pending; the time objective is a structural
proxy, not calibrated latency.
