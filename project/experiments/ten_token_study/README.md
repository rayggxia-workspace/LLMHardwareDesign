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

`nexp_batch_adapter.sv` is a candidate local adapter exposing the command
interface of an independent, unchanged native N. Its zero-statistics batch must be compared
against the original five-command scalar relative-exp sequence before its
latency may be used as calibrated evidence. The adapter requires exclusive
N ownership and a shared-client arbiter at integration time.

`m_s32_stream_candidate.sv` is a new independent leaf candidate, not an
implementation of the accepted M ABI. K16/K32 issue 128/256 S32-by-byte
products per cycle. Wider B values require two/four explicit byte planes,
96-bit row contexts and one final RNE/S32 saturation. `byte_m=1` charges
these passes in the timing model. The historical baseline retains its
previous abstract native-wide-multiply assumption for traceability.

RTL, complete-model numerical, routing/STA and energy coverage are separate
gates. A timing-model target crossing does not satisfy those gates.
