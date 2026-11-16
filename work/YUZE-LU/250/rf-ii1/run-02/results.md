# Ready-independent RF forwarding — Refs #250

Source `3da385c13937bced6251db70d35b0ab7a66b2caa`; Slurm 102249,
`issue250-context-20261111-102`, c64 6×10, completed 0:0.

Global placement of the complete M found a real external return-tag → cancel
control → RF response-ready → RF prefix-adder critical path (6.46ns in the
shared product candidate). This change precomputes the registered pending
response bypass without using `rsp_ready` as a data mux select. A new response
or control samples that read only when `response_ready`; if pending, that
implies `rsp_ready` and therefore true same-edge retirement. The RF still
commits only on actual response retirement. Held output never commits the
precomputed value. No false path, stage removal, extra storage or cycle change.

Strict independent context regression: six seeds × three initial states, all
18 passed. Existing 64 same-owner II1 head chains/seed, three-owner bound,
CREATE/RESTORE/STEP/SPILL/DROP, errors and unchanged state, reset, held output
and backpressure remain checked. Default scale's 18 standalone regressions
also passed. Source/receipt SHA and every command accept/retire CSV were
independently audited by `audit_ii1.py`; see `audit.json` and `recovery.json`.

This is functional equivalence evidence for the unit. Complete M integration
and physical timing are separate and must be re-run; no 300MHz claim.
