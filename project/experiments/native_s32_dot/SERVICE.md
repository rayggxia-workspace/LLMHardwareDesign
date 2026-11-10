# Native exact S32 single-port service evidence — Refs #252/#253

The provider is a P-owned functional resource. It uses one ordinary128-bit
port of the existing16KiB four-bank S, and no added SRAM or hidden wide
read. A128-entry K chunk uses 32 words per query row plus32 words per B
column (N-major) or256 words in K-major layout. Final results use two
separate128-bit words per active row. ROWS1/2/4 means4/8/16 real signed32
multipliers sharing B values; one full-K context spans multiple chunks.
All rows use the same output precision and scale shift for one command.

The two four-K cache tiles have288/320/384B payload, the registered S offer
has16B payload, and the core owns160/320/640B carry-save accumulator pairs.
These are lower bounds on register bytes, not whole-core area: multiplier
pipeline, final CPA/RNE state, output, metadata, comparators, muxes and
control are counted in same-source mapping. Exact full-K products and sums
round once, after the final K. No SRAM or complete KV cache is assumed.

`BEGIN` fixes key/full K/N/active rows/shift/layout/result window. `CHUNK`
requires the exact next K offset, source producer commitment, in-range and
nonoverlapping S windows. A nonterminal chunk responds only after all
reads and core operations retire. The final response follows the last
actual result write ACK and final core take. `CANCEL` and in-flight abort
drain existing S offers/owners; the written mask describes acknowledged
writes, including a write offered before cancellation. There is no implied
rollback. This is a typed candidate ABI; the upstream LC/DDR lease owner
and whole chip fabric are separate qualification gates.

| Evidence | Exact source | Slurm | Result |
| --- | --- | --- | --- |
| Initial ROWS core compile | `f101e808b` | 102386 | Strict width failure retained |
| ROWS1/2/4 core | `83b1acc11` | 102389 | 54 passes, full65535 max positive/negative prefix, every shift0..63, real witness, inactive-row rejection, consecutive STEP II1 |
| Single-port frontend first build | `7c8d44a4a` | 102393 | Strict mask/index/init warnings retained |
| Registered offer without refill, bounded peer | `c31f55b5e` | 102397 | 108 passes, slow II2 offer retained as reference |
| Registered offer with refill, actual four-bank S | `648e9f11d` | 102403 | 108 passes; two accepted owners, raw layouts, cancels, true writes/readback |
| Same source, unused mock-only test branch | `648e9f11d` | 102404 | Strict unused boot-signal rejection retained; does not invalidate the actual-bank build |

The independent offline audit checks every original file SHA, raw-vector
hashes and all pass logs. Exact source archives are tracked. For later runs,
large generated files remain immutable at the listed remote paths with raw
SHA, and the repository keeps representative raw stimulus/traces and large
verbose bank log tails. Run `audit.py` for core and `audit_s128.py` for the
service. The service audit independently reconstructs every read address,
K/group issue, two-slot ownership and final result ACK count in six complete
timing traces per successful job. Fixture writes and readback are separate
from measured command time. Neither historical peer nor actual SRAM model
constitutes300MHz STA or a DDR/whole-model timing proof.

Slurm102403 selected no-stall true-S records, seed25201/init0:

| Layout | Active rows | K/N | S reads / result ACKs | CHUNK accept to terminal |
| --- | ---: | --- | ---: | ---: |
| N-major | 1 | 128/8 | 288 / 2 | 377 cycles |
| K-major | 1 | 128/8 | 288 / 2 | 377 cycles |
| K-major | 2 | 128/8 | 320 / 4 | 411 cycles |
| N-major | 3 of4 | 128/8 | 352 / 6 | 445 cycles |
| K-major | 4 | 128/8 | 384 / 8 | 479 cycles |

Random request/response throttling produced507–700 cycles for corresponding
selected frames. This is observed pressure, not an arbitrary-stall bound.
Production command framing, source DDR/KV loads, contention between staging
and execution, S residency, physical timing and whole-model execution still
need separate measured fees. Hardware throughput changes are separate from
the fixed-hardware DP target.
