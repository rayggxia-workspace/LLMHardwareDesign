# Native S128 timing calibration

Issue250 / PR251. This directory owns the root integration diagnostic, separate
from immutable shared-X historical experiments. It reconstructs run08 by its
complete archive/member SHA-256 and changes only common S service duration.

The eight configurations retain Qwen2.5-3B B1/context512 decode, integer
arithmetic profile, 300MHz, DDR51.2GB/s and the same work. Compare historical
Xreg/NoPool, native P128, then native P/U128; two extra NoPool sensitivities
charge response and unpipelined access overhead. Native `sio`, DMA S traffic,
G gather/input/Mid/distribution and non-FFN S accesses all use the new common
cost. Already explicit X-copy, A-load and Down-ACK paths remain explicit S128.

This is **not** final RTL calibration: the inherited N profile may already
contain some S service, and bulk reservations do not capture individual native
request FSMs. A/copy FSM, finite G streaming, bounded control, native M/weight
and result timing must replace these costs with measured services. Diagnostics
do not supersede original archives or qualify a system token/s/energy claim.

Run only in Slurm compute nodes, c96 8×12, through `job.sh`. Freeze source
commit and source.sha256 before submit. `prepare.py` is deterministic source
preparation; no model simulation is executed on the workstation/login node.
