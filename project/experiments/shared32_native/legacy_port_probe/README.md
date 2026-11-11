# Old-metric shared A port-width sensitivity

Issue247 / PR243. This independent generator leaves the frozen
`shared_pool_study` sources untouched. It changes only the shared consumer
quantum from 32 to 16 bytes per clock in generated code. The local suffix
retains 32 B/clock. FIFO depth 4, 64-byte shared SRAM service, latency 2,
non-broadcast reads, 32KiB pool, R4 arithmetic, tile shapes, contexts,
private capacities and original overlap remain fixed.

The run covers four original workloads (W8 decode512, W16 decode512,
W8 decode2048, W8 prefill2), both old local-port layers (shared/ideal dual),
pool0/pool32, and shared consumer32/16: 32 complete runs. Every 32-byte
RESULT must equal run25 in all fields. Every pool0 RESULT must equal run25
in all fields, including disabled-pool metadata. Pool32/16 is checked by
the frozen traffic/work audit with only its declared shared width and
minimum feeder duration strengthened. The actual generated header runs
the frozen independent numeric/address/FIFO oracle; an additional scan
requires every consumed event to fit the selected width.

These are old evaluation-system conditional results. They are neither a
conservative lower bound on actual RTL throughput nor native full-model
token/s. The new local SRAM implementation is not qualified by selecting
the old ideal-dual layer. Descriptor control, BEGIN/SEAL/RELEASE, actual
LOAD join overhead, finite fill packing, native S32 three-limb conversion,
native capacity and K32 lowering remain outside this single-factor probe.
No unmeasured costs are invented. Native full-model token/s remains null.

## Deployment inputs

Use a fresh run directory under the authorized Melodydt server workspace.
`source/` is the current source snapshot; `inputs.json` records its real
40-hex commit plus `code_sha256` (source-relative) and `input_sha256`
(run-relative). Include all four files in this directory in the code lock.
The complete original run25 frozen-input tree must be copied unchanged,
including `inputs/`, run15/run19/run23 results and R1/R2/R4 calibration
receipts. Also copy run25 `inputs.json` as `run25-inputs.json` and its
decompressed `results/result.json` as `run25-result.json`.

Frozen identities:

- run25 source: `a8e793e4c6f97e9dca5b0cc203797dcd3b0e0e78`.
- run25 result SHA256: `b56095b29aac658af899db495d5b44a07246c3ad04fa93a7b8945def87cfbd03`.
- run25 manifest SHA256: `bb90cbd0e958b76c12bb0474eb039a2799618659bf4b4132adf2361b341c1989`.

All non-Markdown experiment files listed in the run25 manifest must remain
unchanged; later result prose and current production RTL may differ.
Every run25 input is checked against
that frozen manifest, and all generated pre-patch files must match the
actual run25 generation receipt. The current manifest, traces, generated
sources, binaries, tool versions, logs and output SHA256 are recorded.

Copy this `job.sh` into the run root and execute `sbatch --parsable job.sh`.
Only Slurm execution is permitted. The job uses 4 allocated cores,
SystemC3.0.2 and the existing EDA container. No local EDA/model execution.
The success receipt is `results/result.json` with `passed: true`,
32 cases, exact controls and both numerical/FIFO probes passed.

Static generation only is permitted locally via `generate.py --repo ...
--out EMPTY_DIR --r1-calibration ... --r2-calibration ... --r4-calibration
... --feeder-bytes 16` (or 32). This produces no performance result.
