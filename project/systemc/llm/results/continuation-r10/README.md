# Four small structural fixtures (Issue153 / PR154)

These are **seed153 random two-layer models, not pretrained-model inference**. All four complete three autoregressive positions. The independent official FP32 parameter reference and SystemC next IDs match3/3. Gemma's window2 crosses its boundary; Qwen executes GDN plus Attention; Falcon executes Attention plus SSM. `index.json` binds actual remote source archive/executable/input/output hashes and actual Slurm94519 COMPLETED0:0 (3:48).

Local GCC10.3/SystemC3.0.1 `-Werror + UBSan` reruns produce byte-identical complete hidden/logits binaries for all four. Large/random binary inputs stay outside Git; the seeded generator and hashes permit reproduction.

The original r10 generic exporter/validator strings say "true checkpoint" / "original full FP32 checkpoint" without detecting a synthetic fixture. They are retained as raw historical output. Their actual source is explicitly recorded in each `*-source-fixture-scope.json`, generator, journal and this index. They must never be promoted to real pretrained evidence. Subsequent exporter/validator code now carries explicit fixture/input scope automatically. This metadata correction does not change numerical outputs.
