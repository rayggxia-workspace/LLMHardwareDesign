# Provisional I/O timing contract for exact overlay C/U

This is a proposed reproducible standalone block test environment. It is not a previously accepted contract for these overlay implementations, nor an extracted A/B top environment.

## Evidence and limits

Both exact overlay `input.sdc` files contain only a 4 ns clock on clk_i and 0.1 ns uncertainty. Their generated 4_cts.sdc cannot establish constrained I/O paths merely by containing no STA violations. Configs point to `.../issue-219-block-search/blockv2-mod-pipeline-next-20261115/staging/algo1-main-execution-20261116/new-control/`. No SDC exists under that source staging tree. Its contracts/MAIN_ABI_BOUNDARIES.md explicitly separates interface mapping from physical validation.

The nearest historical comparison methodology is `/public/home/yuzelu/project-circuit/u-block-main-cross-owner-250-20261115/physical-u-rms-signoff-250/route-input.sdc`: explicit ns/fF units, clock 4 ns, uncertainty 0.1 ns, clock transition 0.05 ns, input min/max delay 0.2/0.8 ns, BUF_X2 input drive, output min/max delay 0.2/0.8 ns, ordinary output load 2 fF. That SDC assigns 50 fF to late_* and 5 fF to native_*; those name-dependent exceptions belong to its original interface and must not be blindly copied. Its receipt is u-block-250-signoff.json, setup +0.417082161 ns, hold +0.007655432 ns, electrical zero. Parent/macro hashes differ from the current overlay.

Segment-C final.sdc uses the same ordinary I/O 0.2/0.8 ns, BUF_X2 and 2 fF methodology. Its timing/electrical pass is separate from its 106 full-deck DRC findings. These numerical budgets are methodological precedents, not evidence that the overlay can meet them.

## Recommended common test

Apply exactly the same SDC to baseline and X8 candidates, before optimizing against it and again during extracted final STA. Report all I/O and internal clock groups separately.

| Item | Value | Basis |
| --- | --- | --- |
| Clock | 4 ns, uncertainty 0.1 ns | Exact overlay source |
| Clock transition | 0.05 ns | Historical standalone method |
| Every nonclock input delay | min 0.2 ns, max 0.8 ns | Historical standalone method, newly imposed on overlay |
| Every nonclock input driver | Nangate BUF_X2, pin Z | Historical standalone method |
| Driver input rise/fall transition | 0.05 ns | Explicit new finite-slew engineering assumption; historical write_sdc default was 0 |
| Every output delay | min +0.2 ns, max +0.8 ns | Historical standalone method; preserve min sign explicitly |
| Every output baseline load | 2 fF | Historical ordinary-output method |
| Selected 153 output load sweeps | 50, 500, 1000 fF, separate corners | New load sensitivity study; no inferred physical equivalence to top RC |

Use either a driving-cell model or fixed input slew as the primary model; do not unintentionally apply both and let tool ordering choose. The recommended BUF_X2 model with 50 ps input slew produces a port waveform dependent on its receiving load. A separate fixed port transition case (e.g. 0.1 ns) may be reported for comparison, clearly labeled as another scenario.

The selected 153 outputs comprise all data/control/ready/ack signals in the precise audit list. Constrain every other signal port as well so apparent slack cannot be improved by omitting unrelated configuration or DMA paths. Clock is excluded from data input constraints. Both RTL tops use asynchronous rst_ni with a two-flop reset release synchronizer; do not add a blanket reset false path to make a report pass. Preserve/report recovery/removal and reset coverage separately; a periodic input-delay assumption does not prove asynchronous-reset behavior.

No false paths, multicycle exceptions, or case-analysis constants should be added without RTL/protocol evidence. Any tool-reported unconstrained endpoints must be explicitly enumerated and explained. Missing clock or empty path groups are failures of coverage, not passes.

Do not add arbitrary max-transition/capacitance/fanout thresholds to hide library violations. Use characterized limits and disclose any design-level supplemental bounds. Verify units explicitly before assigning loads.

## Report meaning

A successful result means this exact routed implementation meets the declared standalone 250 MHz I/O test environment. Load sweep results quantify sensitivity under the same budget. They do not measure current top line RC, coupling, receiver slew or complete cross-block setup/hold. For 200/300 MHz, repeat with clock 5/3.333333333 ns while disclosing whether external delays remain fixed; do not convert a single path slack directly into top maximum frequency.
