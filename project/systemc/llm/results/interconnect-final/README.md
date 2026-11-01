# Dataflow, finite bridge and extended-sequence evidence

54 complete real text-model experiments: seven observations, 21 width/queue
comparisons, seven first extended cases, five repair isolation cases, seven final
extended cases, and seven final original-prompt/link rechecks. Six failing runs
are intentionally retained. All final seven models pass frozen gates at all nine
positions using the same f14 executable; Llama is deferred. Eleven conditional
FP32 weight/parameter diagnostics are separate from complete SystemC runs.

remote-audit.json independently reassesses gates and strictly checks dependencies,
lifetimes, macro totals, controls, finite link limits, full binary equivalence,
original source/weight/scales/reference provenance and actual execution hashes.
It retains original FP32 metrics; it does not recompute those expensive forwards.
index.json verifies each collected raw small file byte-for-byte against that
allocated-node audit. Full weights, binaries, events and value CSV remain at the
indexed authorized server paths. Source archives f1/f2/f6/f14 were uncommitted
snapshots based on d6f033; archive/member SHA, not the parent alone, binds execution.
Actual staged runners are separately hashed. f9 was cancelled before execution.

The bridge carries host-mediated outer Tensor boundaries. Static matrix weights
and raw R state are outside it; internal macro arithmetic remains untimed. Timings
are assumptions, not M11/M12 geometry, chip throughput or finite total memory.
Sequential model execution shows no queue-depth benefit. Separate CTest senders
cover contention, corruption and missing-response rejection.

Chronology, failures, fixes, format costs and limits:
docs/SYSTEMC_INTERCONNECT_EXPERIMENTS.md. Local UBSan/13 CTest and synthetic
fixtures are a separate interconnect-local-f14 collection, not pretrained models.
