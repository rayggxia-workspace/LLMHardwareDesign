# Qwen2.5-3B instruction-driven timing experiment

This Python transaction-level model replays sealed Algo1 mother programs and their local descriptors. It advances controller dispatch and waits, finite SRAM port accesses, and two DRAMsim3 channels on one event clock. DDR writes become visible on completion. The runner produces the page timeline, DDR transaction counts and token retirements used by the throughput audits.

## Inputs and execution

Use Python 3.10 or newer. Build `native_tlm_dram.cpp` as a C++17 shared library against the project's qualified DRAMsim3 build with strict write callbacks. Use its `src` and `ext/headers` include paths, and make the linked `libdramsim3.so` available to the dynamic loader. The run needs the sealed deployment directory, its proof SHA-256, the initial DDR image table with its payloads, and the 630 ps single-channel DDR configuration. The two-step decode additionally needs the sealed KV binding and its SHA-256.

From the repository root, substitute the input paths and hashes in these commands. Each output directory must be new.

```bash
bench=project/experiments/systemc_benchmark
audit=work/YUZE-LU/234/native-sram-width
python -B "$bench/test_native_tlm_services.py"

for width in 128 512; do
  python "$bench/run_native_tlm_request.py" "$PROGRAM" "$DDR_IMAGES" "$DRAM_LIB" "$DDR_INI" \
    "decode-$width" "$DEPLOYMENT_SHA" --decode-kv-binding "$KV_BINDING" \
    --decode-kv-sha256 "$KV_SHA" --dma-fabric-budget --kv-read-window 8 --sram-port-bits "$width"
  python "$bench/audit_native_decode_timing.py" "decode-$width" > "decode-$width/timing-audit.json"
done
python "$audit/compare.py" decode-128 decode-512

python "$bench/run_native_tlm_request.py" "$PROGRAM" "$DDR_IMAGES" "$DRAM_LIB" "$DDR_INI" \
  prefill-512 "$DEPLOYMENT_SHA" --prefill-tokens 2 --dma-fabric-budget \
  --kv-read-window 8 --sram-port-bits 512
python "$audit/audit_prefill.py" prefill-512 2
```

Decode executes two complete 36-layer positions with a 512-position representative KV history and the complete vocabulary projection. The second step consumes live KV writes and the token selected by the first step. Its throughput is the inverse of the interval between the two retirements.

Short prefill starts with empty KV and runs the first two prompt positions through the final residual and KV writebacks. Prompt tok/s is two divided by that simulated elapsed time. The sealed deployment places vocabulary projection at the end of the full 512-position prompt, so short prefill measures input processing through the second position.

The 512-bit candidate models up to four adjacent 16-byte words per SRAM request on one bank row, with partial bank enables and an acknowledged response. It uses the same clock, instruction stream and DDR budget as the 128-bit case. This is a width sensitivity experiment with modeled local services. RTL and physical qualification of the 512-bit path, end-to-end numerical acceptance and the full P512/D128 benchmark remain open.

The [experiment record](../../../work/YUZE-LU/234/native-sram-width/README.md) identifies the archived inputs and runs.
