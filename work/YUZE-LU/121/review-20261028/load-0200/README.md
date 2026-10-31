# Actual M/T output-load sensitivity

Six independent16CPU tasks ran concurrently on c96/node17 in run266/job92947. All six experiments and all loaded native STA passed, including annotation/electrical/complete endpoint checks and actual tiny-fixture wrong-load negatives. Original approved final files stayed unchanged. Source commit3e5ca96dfda0771996a5d0ba4095799f9c58bc42.

| Macro | Variant | Total output load fF | Minimum setup / hold ns |
| --- | --- | --- | --- |
| M | approved | 50 | +0.008340 / +0.013190 |
| M | P2 base + receiver | 45.509479 | +0.008340 / +0.013190 |
| M | P2 high + receiver | 67.264218 | +0.008340 / +0.013190 |
| T | approved | 50 | +0.429092 / +0.007988 |
| T | P2 base + receiver | 60.427015 | +0.422594 / +0.007988 |
| T | P2 high + receiver | 89.640522 | +0.404473 / +0.007988 |

This replaces the approved50fF only in a fresh read-only process. The outputs carry2fF receiver plus actual P2 wire C;50fF is not added again. It is uncalibrated lumped output-C sensitivity only. Series R, input/clock wires, coupling, remote driver and combined interface timing remain unqualified.

Run265/job92944 completed its native STA but failed the original readback parser: actual0.8ns native serialization differs by more than its fixed1e-8 numeric tolerance. Original failures remain. Run266 uses unchanged exact-token comparator plus a real same-tool tiny DFF fixture for the intended budget and actual wrong-load control, without relaxing slack or dropping endpoints. Six independent tasks started at once in both runs; no P&R or passed final gates were repeated.

S258 final-netlist three-initial-state function passed and is captured here. S DRC/strict LEC, R236 native P&R and V264 GRT remain running at capture. Capture time, remote paths, exact sizes and SHA are in index.json; the directory label is not the observation timestamp. Original timing.rpt trailing whitespace is preserved.
