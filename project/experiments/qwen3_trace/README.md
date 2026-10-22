# Fixed Qwen3 inference and boundary trace

Issue23 uses the public pinned Qwen3-0.6B weights to test full-prefix versus cached inference and chunked prefill. The experiment contract is frozen in `experiment.json` before the formal run. It is a CPU FP32 correctness/trace experiment, not a hardware performance or language-quality benchmark.

Weights, the isolated environment and caches remain outside Git under `D:/Projects/Codex/qwen3-inference-20261022/environment/`. Record local file hashes after download; the remote expected hash alone is not proof of download integrity. Do not install into the global Python environment.

The selected inputs are teacher-forced tokens from the fixed text; no generated token changes later inputs. Compare full prefix, one prefill followed by single tokens, and two equal prefill chunks followed by the same single tokens. Both full and cached paths use eager attention, FP32, the same masks and absolute positions.

All 28 layers record observed projection/activation shapes and actual cache growth. Numerical boundary slices use layers 0/13/27. Raw Q/K projections are pre-normalization/pre-RoPE. A temporary wrapper around the reviewed eager attention entry observes actual post-RoPE Q and cached K/V before GQA repetition; K/V must equal the actual cache. This experiment permits no concurrent model calls. The original function and all hooks are restored in a finally block, and every step is checked against an unobserved cached stream. A hook's stored sample is observer memory, not inherent model residency. Summing tensor event bytes is not a live working-set estimate.

The fixed atol/rtol are both 1e-4. Failures remain in output. Changing a tolerance or input after observing failure requires a new recorded configuration and explanation.

Product-specific static interconnect must serve prefill and decode without rewiring between calls. Runtime switching, arbitrary pooling and extra ports cannot be given free to one partition candidate. A valid fixed design with legal chunking may show no benefit from late customization; that is an acceptable result.

Formal invocation from a clean recorded commit, with all caches/TEMP already set to the task's D drive directory:

```powershell
& '<isolated-env>/Scripts/python.exe' project/experiments/qwen3_trace/run.py --model-dir '<verified-pinned-weights>' --out 'D:/Projects/Codex/qwen3-inference-20261022/results/run-01'
```

The runner rejects existing outputs, wrong weights/architecture, unreviewed implementation bytes or package versions. Timing/epoch fields intentionally differ between runs; compare scientific results under the declared tolerance, not the bytes of timestamped manifests. The isolated environment and CPU import/matrix checks have passed. Six protocol checks and a random tiny-model integration (196 events, injected exception restoration) passed; these are development checks. Two real-weight runs at source d63bc2d37a5f1457a4a170b17afba343fb54998d passed: 54 numerical comparisons, 4 state corruption controls, 35 traced calls / 13720 events. Five scientific payload files replay bytewise; see docs/experiments/issue-23-qwen3-real-trace.md and results/issue-23-run01/. Delivery adds a nonzero CLI exit for a scientific FAIL; recorded runs used the original source commit and were accepted from full evidence.

Protocol checks in the isolated environment: `python -B -m unittest discover -s project/experiments/qwen3_trace -p test_numeric.py -v`. Development integration: `python -B work/Liangruizhi/23/check_observer.py`. These do not require official model weights.
