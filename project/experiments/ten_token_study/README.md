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

The final record is [the results report](../../../work/YUZE-LU/240/ten-token/RESULTS.md).
The 102.4 GB/s, P3/K16/E8 candidate predicts 10.7298 token/s at context512;
context640 is 10.1907 and context2048 is 6.6501. Original17.1 GB/s compressed
W4/head8 and W2/head8 candidates predict 4.9202/6.7335; neither is numerically
qualified. These are different resource budgets, not DP algorithm gains.

## Reproduce in a new run directory

Use GCC14.2, SystemC3.0.2, Python3.12.4. Copy this directory's C++/Python files,
the existing `work/YUZE-LU/240/inputs/*.trace`, and the new receipt's
`evidence/systemc/{decode2,decode640}.trace` into `NEW_RUN/generated/`.
Set `TEN_TOKEN_MODEL` to the absolute executable path when its name differs.

```bash
cd NEW_RUN
g++ -std=c++17 -O2 -Wall -Wextra -Werror model.cpp -ISYSTEMC_PREFIX/include -LSYSTEMC_PREFIX/lib -lsystemc -o model
export TEN_TOKEN_MODEL="$PWD/model"
python -B sweep.py --workers 2 --designs prior17 batch17 b68_p3_m2_e8 b68_p3_m4_e16 b85_p3_m2_e8 b85_p3_m4_e8 b102_p2_m2_e8 b102_p3_m2_e8 b136_p3_m4_e8 fixed17_w4_head8 fixed17_w2_head8 --output round3.json
python -B sweep.py --workload decode2 --workers 2 --designs prior17 b85_p3_m2_e8 b102_p3_m2_e8 --output context2.json
python -B sweep.py --workload decode640 --workers 2 --designs b85_p3_m2_e8 b102_p3_m2_e8 --output context640.json
python -B sweep.py --workload decode2048 --workers 2 --designs b102_p3_m2_e8 b136_p3_m4_e8 --output context2048.json
python -B sweep.py --workload prefill2 --workers 2 --designs b102_p3_m2_e8 b136_p3_m4_e8 --output prefill2.json
python -B sweep.py --workers 2 --designs b17_p3_m2_e8 b34_p3_m2_e8 b136_p3_m4_e8_w16 b136_p3_m8_e8_w16 --output attribution-w16.json
python -B check_candidates.py --results round3.json context2.json context640.json context2048.json prefill2.json attribution-w16.json
```

Native RTL requires Verilator5.042. For M, put the two SV files under
`NEW_NATIVE/source/`, generate `vectors16` and `vectors32` with
`python -B m_vectors.py generate NEW_NATIVE/vectors16 --lanes 16` (and32),
then submit `m_native.sbatch` from that new directory. Verify each result
with `python -B m_vectors.py verify NEW_NATIVE/vectors16` (and32).
N's `native.sbatch` expects `source/{nexp_batch_adapter,tb_nexp_batch}.sv`
and unchanged `source/native/block_v2_n{,_group}.sv`, `block_v2_n_exp.svh`.
Read project remote rules before using its server/container paths; use the
allocated cores only. Source scripts must have LF line endings for Slurm.

`verify_delivery.py` runs from the repository and verifies copied native
logs, source versions, integer results and the receipt SHA manifest. Raw M
stimuli can be regenerated; their hashes and remote paths are retained.
