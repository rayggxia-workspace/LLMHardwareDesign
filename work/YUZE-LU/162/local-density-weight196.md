# Stronger local placement cost: bounded diagnostic

Issue #162 / PR #163, 2026-11-03 Asia/Shanghai.

Actual candidate 1770 exhausted 50 FastRoute global iterations with 116814
overflow, although aggregate resource utilization was 66.87%. Candidate 1702
has estimated local preferred-direction peak demand 2.36207 at search weight
1e8. These are distinct observations; neither proves global infeasibility.

Allow two additional search weights, 1e9 and 1e10, to test whether congestion
cost was too weak relative to aggregate wire and die cost. Run one 16-trial
placement at each weight, gap 64um, plus an unchanged weight-zero replay of
1580. Every candidate cost is independently recomputed by Python; old trial
bytes must replay exactly. No change to cost formula, RTL, native masks,
minimum-pin/native-ground budgets, or final physical acceptors.

These are placement diagnostics only. Actual low/base/high necessary bounds
must precede further route selection. A stronger penalty may increase wire
length and fail electrical bounds; retain such failures. A clean proxy grants
no geometry, PG, distributed RC, 300MHz, or whole-system qualification.

Use existing own slots with dynamic refill. Verify exact UID, parent job,
source, command, output and step before retiring only own duplicate searches
1590/1591, after replacements are queued. Preserve their specs, partial results,
other controls, all eight allocations and all R/other tasks.
