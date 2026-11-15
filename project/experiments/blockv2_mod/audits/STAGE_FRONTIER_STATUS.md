> 场景纠正：要求512历史KV、连续2步decode。此前历史2、单步decode及21.6%/28.0%收益仅属偏离要求的诊断，不作为本轮验收。错误场景后续作业已停止。

# Decode efficiency iteration

Current scope is decode only: all 36 layers, one new token, history length two.
Inputs reuse previously validated real KV/token assets. No new prefill is run.
This is not P512/D128 or calibrated steady-state throughput.

The low-traffic plan has 55,589 CALLs and 10,179,072 explicit DRL/DWS bytes.
The stage/diverse plan has 65,561 CALLs and 15,284,736 explicit bytes.
The original plan has 17,791,488 explicit bytes. All three still demand about
3,278,553,088 M weight-record bytes and 96,428,032 M activation bytes.
Thus a 42.8% explicit-transfer saving is NOT a 42.8% total DDR saving.
No redundant transfer was proven by the conservative 16-byte symbolic audit.

Stage scheduling improves the structural completion proxy by about 4.95% over
the low-traffic plan, while increasing explicit traffic. This tradeoff is not
accepted as a performance improvement before complete same-input TLM comparison.
No calibrated cycles, physical utilization or throughput is claimed.

Independent full-K MatMul output ranges can now omit artificial predecessor
range edges. Real producer/consumer dependencies, LC/SRAM ownership, shared
packing-workspace leases and parent-before-child construction are preserved.
Other service families retain conservative sequencing. Thirteen focused
invariants passed in job 115296; full decode search/package/execution is
115297 -> 115299 -> 115301, static audit 115300. Earlier decode executions
115291 passed full decode and all 73 exported values. 115294 remains pending.

The TLM progress log now exposes DDR/SRAM counters plus service-active and
dispatch-wait sums for completed calls. These sums overlap between services;
they are not additive critical-path delays or arithmetic-core utilization.

## Completed low-traffic decode

Job 115291 executed all 55,589 instructions and compared 73 exported values
(logits plus 72 KV tensors), 828,928 bytes, bit exact. Comparison 115314 checked
identical inputs/base/timing models against accepted original execution 115084.
Model time: 807.066455283 ms -> 632.603909949 ms (-21.6169%).
Actual all-inclusive DDR: 3,427,752,576 -> 3,418,237,056 bytes (-0.2776%).
P0/P1/P2 controller reserved fractions changed from 89.01/0.93/4.87% to
74.41/25.98/21.95%. These include memory waiting, not arithmetic utilization.
This validates the low-traffic decode variant, not later variants or prefill.

## Cost accounting and observed placement

The versioned service-payload/2 estimate corrects MPR1 activation accounting:
each K128 input is loaded once per command, then shared by its output groups.
Ordinary weight records use 1088 bytes, head16 records 1152 bytes. Source
write/scan/convert and packed write/read are counted once per K128. Arithmetic
work is still a structural proxy, not calibrated cycles. Legacy structural/1
remains selectable and recorded; results from different proxies are not mixed.
Job 115302 passed 15 invariants. Full decode cost-revision search/package/TLM:
115303 -> 115304 -> 115306; static audit 115305.

Audit 115307/115310 proves no duplicate physical M weight record spans in the
low-traffic plan. Every one of 9251 MPR commands uses 16 output groups. The same
plan assigns 2031443968 / 675569664 / 571539456 weight bytes to P0 / P1 / P2.
The LM head alone carries 330612736 bytes, making it a significant scheduling
target outside FFN. Weight placement is a demand distribution, not measured
arithmetic-core utilization.

Complete comparison 115309 checks input assets, graph/base/allocation, numeric
receipts, all instructions, clock/DDR/SRAM configuration and unchanged timing
model sources. It reports all DDR reads/writes including internal service and
descriptor traffic. Client wait sums are not additive critical-path delays.
Functional acceptance and predicted performance comparison are separate.

GitHub publication of this increment is pending: the connector returned
Transport closed on three reads. Sources and pending hashes remain remote in
delivery/github-integration/decode-pending-index.json. No upload is claimed.

# Scheduling semantics

The search construction order requires every needed producer range to have been
chosen before its consumer. Choosing A's mapping does not wait for all A ranges
to execute. Independent C can be chosen before or after B and still overlap.

The internal range-ready set denotes constructible ranges, not the user's
independent operator-level Ready frontier. Source operators retain partial
progress; software planning completion must not be read as hardware retirement.

Actual CALLs remain atomic under the existing single-command LC contract.
Different owners are released after their respective last CALLs, rather than
after the whole candidate. Shared SRAM is protected by the owner's dependency;
a shared DDR workspace remains leased through the complete candidate.

The emitted dependency graph is checked against the searched resource schedule.
Mother encoding issues ready independent targets and uses individual predicted-
first WAITs, instead of joining unrelated live commands into one WAIT barrier.
These are existing target-mask WAIT instructions. Prediction uses structural
work units, not calibrated physical time. No concurrency inside a busy LC CALL
or WAIT-any hardware support is assumed.

The bounded beam reserves opportunities for early estimated completion, low DDR
traffic and low dirty-buffer pressure. Only exactly equivalent stored states are
deduplicated. There is no dominance claim across incompatible mappings or data
placements, and no global optimality claim.

RTL changes are not part of this increment. Direct inter-SRAM transfers, SRAM-
source M execution and cross-command K continuation remain separate capability
gaps. No implicit U/P path, extra accumulator bank or physical block boundary
is introduced.

Validation: 12 independent scheduling/control/construction tests passed in job
115275. Full graph stage/diversity search is job 115276; full instruction-package
execution is still pending. The prior dirty frontier remains a separate baseline.

Full-graph run 115257 exposed Python decimal integer serialization limits in state deduplication. Structural tuple keys replace JSON keys; the regression covers 31,034-bit task masks and 100,000-bit backing masks. No global interpreter limit was disabled.
