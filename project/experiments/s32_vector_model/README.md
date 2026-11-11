# Partial native S32 timing calibration

Run only through `job.sh` in an authorized Slurm allocation. `run.py` compiles
the frozen run46 SystemC model with strict warnings and evaluates four cases
under the original four workloads and two SRAM port conditions (32 runs).
The `region_q2` case must reproduce all eight complete run46 RESULT objects.

The optional S32 cases replace E execution and local S service for strict
32-bit, equal-shape unary Convert or binary Add/Sub/Product/Maximum/Minimum
operators. Broadcast, mixed-width, unsupported shifts and multi-input
operators retain the prior conditional model. A static S32 U instance alone
does not execute the mixed-width full graph; a dispatcher and conversion
lowering remain necessary. Actual model activation values are not verified.

`profile.py` accepts only the passed run49 native receipts (186 tests,
27 exact default pairs, passed standard-cell mapping), verifies collection
and RTL hashes, and extracts full U service periods for 16 four-lane commands
from three seeds. Queue depths 0/2/4 use their own measured periods. Local
S requests and write acknowledgements are included, so no separate ideal
E pipeline gain or duplicated S charge is applied. Partial tiles are
conservatively charged the complete 64-value tile period.

The prior 300 MHz / 2P+1U / shared 32 KiB / A32 / DDR 17.1 GB/s assumptions
remain fixed. The `idealdual` cases remain conditional port scenarios.
The checker enforces exact DDR traffic, cache and M-work invariants, finite
resources, E-work conservation, trace coverage and 160 tampering rejections.
This is partial timing calibration, not full-model RTL or physical signoff.
