# Independent loader review

Scope: source-level, cycle-preserving combinational rewrite; no backend acceptance or whole-module solver success is claimed. Reviewed 2026-11-17 CST, read-only apart from this report. Management structure check passed.

## Bound inputs

- Original raw SHA256: `85c4199804a0564c2651a1aa008f61bb7c7f7c905e3c7311345b55e0d6592f02`.
- Parallel raw SHA256: `999948f63f4038831fc50c18f370968531dc9703754f1df70c25732666321775` (local and remote agree).
- Selector gold: `8633ae02da33708abaa38ab07b64b97c3f0afb86e1cfa6f66102a1d7d2793db2`.
- Selector gate: `685e3f80278a4f77a38e375fdf17b2d964a6ee3a223876b98cf47307bef2472c`.
- Selector script: `cd191f949c1cb1716ba036e4340770b11cc2f3bbb8f10cc97f2ac277af2ccc4c`.

The existing compositional JSON hashes `read_text().encode()` rather than raw bytes. Its parallel hash `5331d7...` is normalized-text identity, not the above raw artifact identity. Record both explicitly before publishing a proof-bound replacement.

## Argument for the reviewed parallel rewrite

The prefix before the old combinational block equals the new prefix before added lane temporaries; the complete suffix beginning at the positive-edge block is identical. This was independently checked. Thus functions, original state declarations, continuous outputs and every sequential assignment (including order of conflicting nonblocking assignments) are unchanged.

For fixed original state/input values, define each lane's address, waiting, first matching cache hit/index, padding and cache index. These functions are pure: they only read original state and their arguments. The new loop evaluates precisely those same values with `j=4*p+l`. The iteration domain is 0..7, so `j/4`, `j%4` and sized casts exactly match original `p`, `l`; no signed-negative or truncation case enters this mapping. Each new temporary is assigned on every execution, with identical 64-bit address and 3-bit cache-index widths. There is no inter-lane feedback.

Induct over the eight lanes. Before the first eligible examined lane, each examined lane updates address/hit/pad/waiting/hc in both designs. Eligibility on an examined lane uses the identical condition; adding `lane_exam` to that condition is redundant in this branch. The first eligible lane sets candidate and cp/cl/cc in both designs, and all later lanes are skipped by the selector. If none is eligible, both retain the last **examined** lane's auxiliary values; cp/cl/cc remain zero. If no lane is examined, every default remains zero. `free_owner` is outside the 77 selector bits but its identical default expression independently preserves it.

This establishes identical original combinational outputs for every two-state original state/input valuation. Identical reset and positive-edge updates then establish equal next state and cycle-by-cycle outputs from equal initial/reset state, without adding pipeline latency. The arbitrary-input selector proof supports the selector step; it is a manually normalized model and alone does not prove the surrounding loader.

## Limits and required wording

The reviewed source supports this compositional two-state argument. The current Python obligations checker mostly asserts that selected text fragments occur, rather than proving the entire normalized selector body is identical to the model. It is insufficient as a future-version automatic proof by itself. Bind this manual review to the exact raw hashes, or strengthen the checker to reject extra/reordered assignments and bind all model/log/script hashes.

No whole-module SAT completion was observed by this reviewer. Do not label the full solver passed. No mapped-netlist equivalence, timing improvement, or physical qualification follows from this source proof; those are separate gates.

For the parallel rewrite, the same branch induction also preserves settled four-state procedural-if behavior: candidate/hit are assigned known constants, X conditions do not enter an `if`, and skipped lane evaluation is pure. This is not a simulator event/delta-cycle equivalence test. Do not claim such a test was executed.

## Separate div/mod-3 candidate

For an unsigned 11-bit input, the maximum product `2047*683=1398101` fits 21 bits. Since `683=(2048+1)/3`, truncating `(index*683)/2048` gives exactly `floor(index/3)` throughout 0..2047; for the largest residue-2 input2045 the fractional term remains below1. `q<=682`, `3*q<=2046`, so 11-bit remainder subtraction and shifts fit. This supports the reported exhaustive/solver check in the two-state domain.

It does **not** establish strict four-state X propagation: the new q's top bit is forced0, while unknown-input division can produce all X. The arithmetic candidate is a different source artifact and needs its own raw hash and complete substitution binding. It is not covered by the parallel raw hash above.
