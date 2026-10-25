# Issue85 runtime cache and recovery

One executable accepts either cached or uncached physical format at command handshake. Frozen PROTOCOL.md and project/rtl/runtime_cache/README.md define ready/valid, cfg priority, finite responses, epoch and reset constraints. Actual mathematical/RTL work is server-only. Parent handles publication; no direct merge.

Reproduce on authorized CPU Slurm with a new output directory, source commit and binding:

    python -B project/experiments/runtime_cache/inputs.py --old /public/home/yuzelu/RuizhiLiang/issue84-cache-share-20261025/input01 --out <new-input>
    python -B project/experiments/runtime_cache/run.py build --binding <binding.json> --out <new-build> --prefix '<singularity argv JSON>'
    python -B project/experiments/runtime_cache/run.py sim --binding <binding.json> --out <new-run> --input <input> --build <build> --stall <0 or1> --prefix '<same>'
    python -B project/experiments/runtime_cache/verify.py --input <input> --run <run> --out <new-receipt>
    python -B project/experiments/runtime_cache/run.py map --binding <binding.json> --out <new-map> --prefix '<same>' --library <frozenLiberty>

Analysis uses explicit formal output paths and refuses a different original84 comparison SHA. Collector uses explicit Issue85 root. Selected.zip requires byte checking before source checking; verify_sources.py compares original Git blobs and all contiguous phase bindings. No complete input or model download is needed on the PC.

Epoch is currently a separate32bit request/response metadata interface. Its mux/register/counter logic is mapped; five-beat data bridge counts do not qualify physical tag wires or network framing. Pack/gather, SRAM macro, STA, physical layout/CDC and gate equivalence remain unaccepted.
