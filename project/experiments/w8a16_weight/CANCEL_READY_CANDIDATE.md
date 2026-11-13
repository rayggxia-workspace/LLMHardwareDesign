# Good-CANCEL ready-chain candidate, Refs250

Independent diagnostic and physical candidate; f08 remains the previous single-record
reference. Original Liberty/300MHz/physical rules are unchanged.

Original f08 placement probe102358 binds exact3_place ODB/SDC SHA. At original
constraints, mc_rsp_tag22 -> good/bad FILL validation -> W control ready -> matching
CANCEL acceptance -> RF/raw ready -> a_ready arrives3.7340ns, slack-1.3007ns.
The distinct worst path is4.6260ns from scope_bias read register to RF register D;
this fix does not claim that distinct RF path is solved.

A matching CANCEL is a nonfaulting state transition and may accept alongside an
unrelated malformed FILL. Only malformed FILL owns the single held fault receipt;
malformed CANCEL still waits behind malformed FILL. Cancellation remains a true
handshake, and already-offered DMA/issued returns/CLOSE/drain retain their lifecycle.
No speculative cancel ACK, new payload/FIFO/registers, numeric change or added cycle.

Source82e245c95 first passed18 W tests (10 actual faults including the new concurrent
bad-FILL/good-CANCEL),18 native tests and18 aperture tests. f33416101 normalizes only
weight source newline bytes and is the exact canonical source repeated in102365
and102367, all54 W/native/aperture runs PASS. Artifact SHA/source/strict lint audits
for canonical runs58/59 pass. Product costs remain INPUT11, CONTINUE16, FINAL18,
old single-active guard head EXEC II21,779 real DMA64 returns/requests and88 true
S128 ACKs per aperture regression. These unchanged costs are unit evidence.

Mapping102372 is source-bound to canonical102367. Physical qualification and real
P/global fabric joint must still pass; no300MHz result is inferred from the cut.
Original reports and index: work/YUZE-LU/250/weights/physical-15.
