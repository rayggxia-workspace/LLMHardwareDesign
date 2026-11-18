# One-hot selector v2 independent review

Candidate: `loader-onehot-v2.sv`, SHA256 `020538508ff7db6461afab28f73726867e5900fde2255a4a311789b105040567`.

The 77-bit direct combinational miter in Slurm 119681 passed (`onehot-v2-119681.log`). Inputs are unconstrained lane payloads, examination bits, and raw eligibility bits. The gate model computes eligibility = examination AND raw eligibility, exactly matching the original nested examination/eligibility semantics. The proof includes no-eligible fallback to the last examined lane, all-zero examination defaults, candidate selection, lane identifiers, address, hit/pad/wait, cache slot and hit slot.

`review_onehot_v2.py` verifies that the gate's selector body is identical to the candidate body; all preceding logic except inserted temporary declarations and the complete posedge suffix are identical to the previously reviewed distributed-parallel source. Thus arbitrary-lane selector equivalence composes with unchanged lane computations and unchanged state transition logic. This is a two-state source-level compositional argument. Neither complete-loader SAT nor four-state X propagation is claimed.

The earlier v1 candidate failed direct SAT and is rejected. Its fallback mask was replaced with an explicit shifted 8'hff mask; the v2 proof passes across the entire input space. Never reuse the v1 synthesis/proof result as acceptance evidence.

Physical evaluation is separate from logical acceptance. Jobs 119686 (one-hot v2) and 119687 (row-last comparator) are diagnostics of a standalone loader using identical 30/50% utilization, 4 ns clock, 0.1 ns uncertainty, 0.8 ns IO delay and 2 fF output loads. They are not final parent block signoff.

An important flow discrepancy was found: the ORFS Nangate45 default ADDER_MAP_FILE maps extracted full/half adders directly into FA_X1/HA_X1 before ABC; the standalone FAST mapping does not run this step. Parent-level comparison with ADDER_MAP_FILE empty is necessary before extrapolating standalone improvements.

## Completed physical diagnostics

Both jobs completed with exit code 0. After setup repair and detailed placement:

| Candidate | 30% WNS (ns) | 50% WNS (ns) |
|---|---:|---:|
| Previously reviewed combined | -0.4696 | -0.2534 |
| One-hot v2 (119686) | -0.028458 | -0.026355 |
| Row-last reordered sum (119687) | -0.441803 | -0.450382 |

One-hot v2 consistently improves the standalone loader result and is eligible for parent-level testing. Row-last does not consistently improve it and is not recommended for promotion. Neither candidate has positive setup slack in these standalone checks. Parent macro/block signoff remains outstanding.
