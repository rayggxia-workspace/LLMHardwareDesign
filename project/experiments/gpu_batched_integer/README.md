# Actual grouped INT8 backend

Windows/cu128 task-local backend using the cuBLAS and NVRTC DLLs bundled in the isolated official Torch2.10.0 wheel. It installs no driver/toolkit and never falls back to floating-point GEMM. `cublasGemmStridedBatchedEx` uses INT8 A/B, INT32 output and `CUBLAS_COMPUTE_32I`; the ABI/status and all independent INT64 checks are explicit.

`kernel.py` batches up to8 independent K groups, with the INT32 temporary capped near128MiB (one group can exceed it for a large one-shot shape). Activation quantization is vectorized but retains the same dynamic per-row/group scales. FP32 dequantization preserves the original group summation order.

`fused.py` compiles only the FP32 partial dequantization/reduction with the bundled NVRTC. Explicit `__fmul_rn`/`__fadd_rn` and disabled FMA retain the original rounding order; accumulation remains cuBLAS INT32. This is still mixed precision. DLL SHA, source/PTX SHA and the backend name are recorded; no fake-quant timing or frontend overhead becomes a hardware speed claim.

Actual CUDA tests compare all sampled accumulators with INT64 and outputs bitwise against the original per-group kernel for K32/K128, FP16/FP32 inputs and one/non-tile rows. Auxiliary tests check fixed-tree RMS, convolution and recurrent call-boundary equality. Run:

```powershell
$env:CUDA_CACHE_PATH='D:/Data/llm-gpu32/cuda-cache'; & D:/Data/llm-gpu32/.venv/Scripts/python.exe -B -m unittest discover -s project/experiments/gpu_batched_integer -p 'test_*.py' -v
```

Use `--fused-integer` in state/long runners, or `--integer-backend fused` in the quality runner. FP32/canonical auxiliary execution is a separate flag/group with its own quality and continuation checks. The canonical backend supports only the task's fixed unpadded batch1 global causal text: per-query prefixes replace the causal mask, with sequential gated-delta updates and fixed reduction trees. It is a diagnostic reference, not a general padded/sliding-window attention adapter.
