# Qwen 10 token/s candidate-budget study

Refs #240 / PR241. This is an isolated continuation; the original SystemC
experiment, production RTL and other tasks remain independently versioned.

The structural contract is `five-block-v1/2026-11-07`: independent leaf
macros, local-controller ownership, M1–M10 frozen active base, and M11/M12
product connections. None of the configurable interfaces or arithmetic
resources is claimed to exist in the accepted frozen base.

Two routes are investigated: W8/S32 with a larger explicit external budget;
and a fixed 17.1 GB/s budget with separately labeled precision/storage
candidates. The main scope is B1, Qwen2.5-3B, context512 decode; the trace is
a workload projection, not a numerically qualified KV generation program.

`model.cpp` extends the isolated preceding arbitration/dataflow experiments.
`sweep.py` records every resource override. Input traces are inherited from
`work/YUZE-LU/240/inputs`, with additional context2 trace from the preceding
local run. All generated files and binaries belong in a new run directory.

`nexp_batch_adapter.sv` is a candidate local adapter that instantiates the
unchanged native N. Its four-command zero-statistics batch must be compared
against the original five-command scalar relative-exp sequence before its
latency may be used as calibrated evidence. The adapter requires exclusive
N ownership and a shared-client arbiter at integration time.

RTL, complete-model numerical, routing/STA and energy coverage are separate
gates. A timing-model target crossing does not satisfy those gates.
