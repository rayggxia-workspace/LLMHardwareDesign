# Exact-overlap local-demand placement experiment

2026-11-03 Asia/Shanghai, Issue #162 / PR #163.

Actual continuous bbox attribution on1702/1970 has8244 cross-cluster nets,
744 within-cluster nets and2PG nets. At the1702 estimated peak2.36206726,
cross-cluster contribution is2.36116003 and within-cluster0; at1970 peak2.49684482,
cross-cluster contribution is2.44944312. This is a placement heuristic, not
actual path congestion or proof that a macro interface is defective. The
complete original1850 search-path replay is independently running for evidence.

The old objective uniformly deposits each bbox over entire intersected coarse
tiles. Thin bboxes can therefore be diluted. Add an explicit optional `exact`
model: compute actual overlap fractions with16x16 tiles. C++ decomposes each
axis into at most3 constant segments, depositing at most9 rectangles through
difference arrays; Python directly loops intersected cells and recomputes exact
overlap areas. Horizontal/vertical zero extents widen by one4um grid cell only
for density, while original HPWL and electrical budgets remain unchanged.

Test two16-trial exact-model searches, weights1e8 and1e9, and all16 old1970
quantized outputs as a replay. No physical route admission until all independent
cost/nonoverlap oracles, byte replay, and original native-ground/minimum-input
low/base/high necessary bounds pass. Preserve unsuccessful candidates. The old
default model and final eight physical acceptors are unchanged; no RTL/native
mask, pin, area accounting or final gate relaxation. Use only existing own
slots with exact UID/source/command verification before any old child retirement.
