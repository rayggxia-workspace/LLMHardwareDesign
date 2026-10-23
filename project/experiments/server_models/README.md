# Issue61 server model completion and independent intake

Issue61 / PR62, ownerLiangruizhi. All planned CPU reference/capture stages ran on c96/node13 via lrz-i61-* Slurm. Primary models: Qwen2.5-3B **base**, Qwen3.5-4B text, Gemma3-4B-it text; Phi4-mini is sealed independent holdout. See [report](../../../docs/experiments/issue-61-server-models.md), [acceptance ledger](../../../work/Liangruizhi/61/model-acceptance.json) and [data index](results/issue-61/index.json). CPU reference, float fallback, integer software and target hardware are distinct.

## Frozen sources and outputs

| stage | source commit | immutable server phase/output |
| --- | --- | --- |
| Gemma/Phi capture | 8a1fe4bfed52dd0baa552c6043f507bafe902c03 | phase5, gemma-capture01 / phi-reserved01 |
| Qwen capture | a96eef6175d15173496d674caee7b0078971f2f5 | phase9, qwen25-gqa01 / qwen35-gqa01 |
| integer reference | 3f17910ec3d9591a10e9b98ff09916154385751d | phase8, *-integer01 |
| corrected strict export/source verification | 0ff14d76d51beb0a0c607d7e0d024a41b49fd661 | phase13, *-strict02 / *-export-source02.json |
| collection/actual negatives/review | 7fdd2c243e8c1e8a1b9abfcae262ebc9f27bd1b5 | phase14, primary-model-data01.zip / phi-reserved02-sealed.zip |
| complete guarded I32 PV limb kernel | 4ca7214923dd5d87934fb2e10211517bbca35c19 | phase16, conditional-bounds02.json |
| causal packet/capacity readout | 8211803c9a6f7bab42f66ef320410693b9522be2 | phase17, causal-cost01.json |

Each source snapshot has binding.json; capture manifests also record exact model/config/token IDs/framework implementation/environment/artifact SHA. Preserve older failed/superseded phases. strict01 mixed cached norm observations with full-call fields, so **only strict02 is final**. Old aggregated linear cost fields are lower bounds; causal-cost01 separates every cached decode token. conditional-bounds01 is preserved;02 leaves all420/56 common scientific fields unchanged and adds1474560 complete I32 PV outputs matched to I64.

## Receive the committed selected evidence

Use an existing environment with NumPy and Git history containing the pinned commits. All temporary output must go to a new task directory on D. These commands refuse existing output paths. They do not download weights or launch another machine.

~~~powershell
python -B scripts/check_project.py
D:/Projects/Codex/qwen3-inference-20261022/environment/.venv/Scripts/python.exe -B -m unittest discover -s project/experiments/server_models -p 'test_*.py' -v
python -B project/experiments/server_models/receive_bundle.py --archive project/experiments/server_models/results/issue-61/batch-metadata01.zip --expected-sha256 b2e94f70861d92debf71d5f0055a7006c6c1731db688e46c0473d0786b9530fa --code-root . --extract D:/Projects/Codex/issue61-review-new --out D:/Projects/Codex/issue61-review-new-receipt.json
python -B project/experiments/server_models/review_samples.py --archive D:/Projects/Codex/issue61-review-new/review-samples01.zip --out D:/Projects/Codex/issue61-review-new-numeric.json
~~~

The archive has117 indexed members plus its index;27 source files are matched to5 original Git commits. Nested review-samples01.zip independently replays4 actual full-GQA groups /491520 FP64 values and6 full-K selected16-output linear cases /182784 partials /2304 Fraction RQ values. It does **not** include all420 encoded cases or all floating calibration data. It excludes Phi. Full archive and sealed Phi remain on authorized server with sizes/SHA in index; server access is a separate existing permission, not a public URL.

Check supplemental bounds/cost file sizes/SHA against index.json and their source binding/Slurm receipts in work/Liangruizhi/61. The full data archive contains actual raw captures/encoded linears/strict02; use it for receive_probe.py on all420 conditions. Its SHA is2f03daf778c6667aae49d2edd40f3397227514e59c6342d367a552cac6ff7730,569140969B. Never treat selected review replay as full calibration recapture.

## Recorded execution and safe reruns

Authorized root: /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023. No GPU/GRES. Read REMOTE_RULES and inspect squeue/sacct before scheduling. Existing capture-job.sh/qwen-capture-job.sh requested24CPU, quant-job.sh/receive-job02.sh requested2CPU, independent output directories. They intentionally refer to existing immutable outputs; do not blindly resubmit them. A repeat must use a new bound phase and new output names after checking current Issue/member progress.

Frozen environments: old Issue53 venv is read-only Python3.12.7/torch2.10.0+cpu/transformers4.57.6/NumPy2.2.6 for Gemma/Phi; own venv-modern has transformers5.20.2 for Qwen and jsonschema4.26.0 for strict format checks. Wheel inventories in modern-wheels.json/schema-wheels.json. Temporary/cache variables point inside own server root, OMP/MKL match allocated threads, data analysis threads1. Direct HF download failed DNS; public fixed ModelScope relay was SHA-verified, no full weight copies in Git/local PC, no tokens embedded.

Actual capture entry: capture.py --model {gemma,phi,qwen25,qwen35} --model-dir <existing verified directory> --plan <fixed mirror plan> --binding <matching frozen phase binding> --threads 24 --out <new directory>. Protocols are capture-protocol.json and qwen-capture-protocol.json. Qwen3.5 native conv/recurrent dictionaries must remain continuous; no per-window resets. Phi sealed_reserved forbids quant_probe.

Actual arithmetic/receiver entries:

~~~text
quant_probe.py --capture <capture> --binding <phase8/binding.json> --out <new integer dir>
receive_probe.py --result <integer dir> --capture <capture> --out <new independent.json>
export_capture.py --capture <capture> --binding <phase13/binding.json> --out <new strict dir>
validate_export.py --capture <capture> --export <strict dir> --out <new source-audit.json>
bounds.py --root <full server evidence root> --binding <phase16/binding.json> --out <new bounds.json>
cost_readout.py --root <full server evidence root> --binding <phase17/binding.json> --out <new cost.json>
~~~

Record exact command/source/environment/model/input hashes/Slurm state before reuse. These commands are reproducibility documentation, not permission to launch duplicate runs. Existing full-model captures finished90026/90030/90033/90036; selected integer90031/90034/90037; strict02/source90039–90042; collection90044; bounds90045/90046; cost90047. Actual duration and errors in execution ledger/logs; never report capture timing as isolated model throughput.

## Numerical and physical limits

quant-protocol.json fixes S8 A/W, dyadic I8 scales, i32 groups, checked wider alignment, bias before final RNE/sat. FP32->S32Q20 bridge, offline scales, native nonlinear/state and FP64 attention exp/div remain explicit fallbacks. KV8/16 and P7/P15 are separate choices. A16x16 product on S8-only resources needs9 limb products plus shifts/adds/ports, not a free16bit multiplier. bounds.py uses real I32 matmul/add for S8-valued limbs with independent I64 overflow checks, not a native INT8 speed benchmark.

Psum guard + immutable per-head Vscale yields a conditional I32 bound only for the declared normalized/masked domain; not unnormalized online O, varying page scales or arbitrary contexts. Fixed-W L1 bounds cover observed scales/selected outputs only; certificate storage/runtime checks and wide fallback required. Native KV logical vs backing allocations are separate. Packet/port readout is a lower bound, not a scheduled E2b/RTL/PPA result. Float reference/capture success is not quantization quality acceptance; failed candidates and saturation remain in raw metrics. Phi post-freeze validation, E2b/E3/physical/full-graph performance remain unexecuted.
