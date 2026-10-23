# Issue29 independent result audit

Independent local analysis of frozen source commit `916dcf9e74ecd6a2164bdbb79991b0f3f7ed1b1e`, tree `949a745e84fd65ba13188288a788aaeb05d74c37`. Read inputs were `formal-bundle01` and `formal-results01/run-01` under `D:/Projects/Codex/port-rtl-study-20261022/`. The analyzer does not import project generators, schedulers, verifiers or inspect RTL internals. All output is confined to this independent resource-audit directory.

## Actual verification

PASS, zero errors across 1,698,897 explicit checks:

- Frozen bundle/source/index hashes and all 1,872 program hashes match. All 27 result, compile-command and build-log files were independently hashed. Commands retain assertions, strict `-Wall`, and matching typed hardware parameters; no Verilator warning marker appears in the retained build logs.
- Index covers the full 3,456-point domain exactly once: 1,872 accepted programs and 1,584 missing-link rejections. All rejection reasons have an independently identified disabled link in the corresponding full-link program. Placement labels explicitly use O,m,l; JSON key ordering O,l,m is not used.
- All 1,872 unique program results and all 54 stress summaries report success and complete drained beat counts. There are 103,896 transfer tasks, 22,464 compute tasks and 345,384 dependency edges across accepted programs. Summary audits check dependency completion before task start, exact compute duration, no overlapping compute tasks on the same engine, no overlapping transfer tasks on the same endpoint, traffic byte counts, beat rounding, and response-depth bounds.
- All 24 retained program traces were independently read, hashing both compressed and uncompressed bytes. Across 122,494 recorded cycles and 1,332 transfer tasks, every accepted beat was associated with its exact task, setup latency, bank/address/direction/mask/generation; every ACK had a preceding accepted tag, and each transfer ended exactly at its final ACK cycle + 1. These checks use external pre-edge handshakes and task intervals only.
- All 720 accepted restricted/full-link pairs have identical task programs (except hardware header mask), identical cycle counts and identical complete result dictionaries, including every task start/end. Removing a link the fixed program never requests has zero measured effect here.

The complete report is `formal-analysis.json`; its script SHA and all result SHA values are inside it. The independent script is `../analyze_formal.py`.

## Scientific findings

All comparisons below fix port mode, queue depth, stall profile and link mask. Each placement selects the minimum of the same four scheduling heuristics. This is a finite best-of-four comparison, not an optimal scheduler proof.

For full mask63 and no response stalls, all tested queue depths yield the following 000→111 cycle comparison:

| Bank mode | Prefill32 000→111 | Prefill saved | Decode48 000→111 | Decode saved |
| --- | ---: | ---: | ---: | ---: |
| 1RW | 6977→6875 | 102 / 1.462% | 1983→1949 | 34 / 1.715% |
| 1R1W | 6843→6715 | 128 / 1.871% | 1821→1819 | 2 / 0.110% |
| 2RW | 6715→6715 | 0 | 1819→1819 | 0 |

Across all 12 full-mask 2RW phase/depth/stall groups, all eight placements tie after selecting best-of-four policies. Placement benefits therefore depend on the modeled resource bottleneck. A universal placement benefit is contradicted by this tested zero-effect condition.

The key static-placement negative result is stronger: placement111 is in the phase-minimum set for BOTH phases in every full-mask mode/depth/stall configuration. All 54 same-hardware joint-placement groups (including three masks) have zero regret against separately choosing each phase's best placement. The joint objective is one prefill32 plus one decode48 with equal occurrence weight, allowing separate best-of-four policies per phase. There is no prefill/decode placement conflict in this tested pair, and no evidence here that phase-adaptive placement is required. This conclusion concerns this workload/shape/service model and eight enumerated placements only.

Topology consequences differ from latency consequences. Mask59 removes V0 and retains only placement111: 1,008 excluded combinations over all modes/depths/phases/policies/stalls, but its surviving best cycles equal the full-mask best cycles in every tested group. Mask31 removes D1 and retains four O=0 placements, excluding 576 combinations. It can lose access to the best placement under 1RW/1R1W, while 2RW best cycles remain equal. This supports separating coverage/flexibility from measured cycles. It does not establish a physical area or wiring saving.

Endpoint logical traffic stays fixed across hardware and placement: prefill32 M=106,496 B, V=157,568 B, D=65,536 B; decode48 M=52,608 B, V=6,612 B, D=50,176 B. Beat totals are recomputed by ceiling-dividing each transfer separately by 64 B, so short decode transfers retain beat-rounding overhead. These are the inherited FP32-shape logical traffic assumptions, not an INT8 datapath precision contract.

## Evidence gaps and limits

No functional RTL defect was found by these checks. The most important limits are experimental:

- Matrix/vector/softmax arithmetic is synthetic service time; transport data are generation tokens. This is a bank-controller/traffic result, not a numerical inference implementation.
- Full per-beat task/ACK reconstruction covers the 24 retained critical-policy, depth2, p000/p111 traces only. Best-of-four often chooses fifo/shortest; many selected best cases are summary-checked but do not have a retained raw trace. All 1,872 have harness self-checks and independent summary checks; do not describe them as 1,872 independent full trace replays.
- Stress summaries are checked for expected initialization traffic, drain and credit bounds; this script does not replay their payloads. A separate independent protocol/data scoreboard checker is complementary evidence.
- No technology memory mapping, achievable clock, synthesis, physical area, power, energy or PPA is established. Different port modes and FIFO depths are different hardware budgets. Host Slurm elapsed time is software runtime, not hardware performance.
- Both phases use one narrow frozen layer/head/shape-derived workload pair. No broader Qwen, Llama or DeepSeek operator coverage, precision coverage or deployment throughput conclusion follows.

## Reproduction

```powershell
$env:TEMP='D:/Projects/Codex/port-rtl-study-20261022/resource-audit/tmp'
$env:TMP=$env:TEMP
$env:PYTHONPYCACHEPREFIX=$env:TEMP
& 'D:/APP/Python/python.exe' -B 'D:/Projects/Codex/port-rtl-study-20261022/resource-audit/analyze_formal.py' --bundle 'D:/Projects/Codex/port-rtl-study-20261022/formal-bundle01' --run 'D:/Projects/Codex/port-rtl-study-20261022/formal-results01/run-01' --out 'D:/Projects/Codex/port-rtl-study-20261022/resource-audit/formal-analysis01'
```

No server action, Git/GitHub mutation, main-tree edit or environment installation was performed for this analysis.
