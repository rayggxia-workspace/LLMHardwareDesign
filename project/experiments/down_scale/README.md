# Llama down_proj calibration, scale units and Block costs (Issue59)

Frozen comparisons are in `experiment.json`; no new models or remote jobs.
Raw captured FP32 nonlinear outputs cross an explicitly checked S32Q20 bridge.
After that boundary, dynamic scale generation, A8 encoding, matrix products,
scale alignment, checked INT64 accumulation and final signed RNE/sat8 are integer.
Offline W8/static/Y scale compilation and error measurement use FP64.
W8/A8 codes use symmetric [-127,127], output uses [-128,127], all zero dynamic
groups use exponent -20. INT32 group bound is group*127^2. Mixed units are
aligned exactly by left shifts to min(eA+eW), checked against both observed and
format-wide INT64 bounds; no intermediate rounding. Exponent formats are i8
for A/W/Y, i16 for product/common units; shifts outside +/-63 reject. Only
divisible declared K groups are supported; tails are not silently padded.
For this K8192 domain a min/max exponent-spread guard <=35 is sufficient for
INT64 format safety (K*127^2<<35 < 2^63); reject larger spread, never wrap.
Final saturating left shifts detect output overflow before materializing the
shifted result; right shifts use explicit guard/round/sticky and signed ties.

Static max/MSE use original32 or expanded128 calibration only. MSE searches
seven fixed dyadic exponents using input reconstruction MSE, deterministic
ties choose smaller step. No output-error or evaluation fitting. Evaluation
systems/arithmetic were observed in Issue56; heldout is a predeclared new text.
The 5% local RMSE/0.1% output saturation screen is exploratory, not application
quality acceptance. FP32 outputs from the same BF16 checkpoint are reference.

Use the existing local venv from Issue56, with per-process D-drive TEMP/TMP,
offline HF variables and OMP/MKL/OPENBLAS threads=1. All output directories
must be new. In the repository root:

```powershell
python scripts/check_project.py
<venv-python> -B -m unittest discover -s project/experiments/down_scale -p test_contract.py -v
<venv-python> -B project/experiments/down_scale/capture.py --weights <existing-model> --parent <issue56-gqa-group.npz> --output <new-capture>
<venv-python> -B project/experiments/down_scale/numeric.py --capture <new-capture> --output <numeric01>
<venv-python> -B project/experiments/down_scale/service.py --workers 2 --output <service01>
<venv-python> -B project/experiments/down_scale/audit.py --capture <new-capture> --numeric <numeric01> --repeat <numeric02> --service <service01> --output <audit.json>
```

Numeric and service experiments are independent and can run concurrently. Repeat
numeric/service with new directories. Formal runs require clean commit-bound
source. Inputs, package versions, configuration and source/output SHA are saved.

Service assumptions: 8 S32KiB 1RW/128bit banks; W8 occupies S0..3, source32 one-row
ring S4, up to four rows A8 S5, metadata S6, result S7. M32KiB includes 2KiB PE,
8KiB A,16KiB W,6KiB MC. V16KiB scratch. One 8-lane wide engine moves between M
and V in the paired placements; no duplicate engine. Quantizer uses the common
vector engine. 2KiB per endpoint TX/RX direction, single 128bit shared bus,
64B header+64B payload alignment, fragment payload <=1984B, bounded partial
batches 1/4. Initial packed W8/static metadata placement is before the timer;
source32 external DMA through final S7 output is timed. No full network, external
weight fetch, upstream nonlinear cost, full layer N2048 or inter-operator pipeline.

Dynamic full row needs two source passes (32KiB won't fit V16KiB); groups <=2048
retain <=8KiB source in V, reread locally for scan and quantization. Source max,
integer CLZ/compare (3 assumed cycles), A8 publication, metadata compiler (three
eA+eW/min/max slots per 8 lanes plus one spread guard slot per 8 outputs), partial packets, 64bit shifts/adds, final wide RNE,
and bank read/write traffic are included. Wide work assumes 4 32bit limb slots
per lane per update/final RNE; vary each slot 1/2/4 cycles. No divide, square root,
LUT or wide multiplier occurs on this dyadic path. The added shift/carry/adder/
RNE and CLZ/vector capabilities are candidates, not demonstrated RTL. All matrix
and arithmetic timing assumptions remain uncalibrated. No speed/PPA claim.
