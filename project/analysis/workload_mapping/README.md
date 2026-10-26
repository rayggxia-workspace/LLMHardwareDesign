# Workload communication adapter

Main contract, assumptions and evidence: [WORKLOAD_MAPPING_INPUT](../../../docs/WORKLOAD_MAPPING_INPUT.md).

From the repository root, with the fixed local reference snapshots already supplied:

```powershell
python -B -m project.analysis.workload_mapping.validate_delivery --output-dir .local/runs/formal-new --reference-root .local/dependencies/reference_assets
```

Choose a new output name on every run. Source must first be committed; all
scientific work is offline. `--allow-dirty` labels a development preflight and
does not establish a clean source freeze.

The usual individual commands are:

```powershell
python -B -m project.analysis.workload_mapping validate --graph project/analysis/workload_mapping/examples/minimal.mapping.json --blocks project/analysis/workload_mapping/examples/minimal.blocks.json
python -B -m project.analysis.workload_mapping build --graph project/analysis/workload_mapping/examples/minimal.mapping.json --blocks project/analysis/workload_mapping/examples/minimal.blocks.json --root .local/runs --output-dir minimal-new
python -B -m project.analysis.workload_mapping verify --bundle .local/runs/minimal-new
python -B -m project.analysis.workload_mapping replay --bundle .local/runs/minimal-new --root .local/runs --output-dir minimal-replay-new
python -B -m project.analysis.workload_mapping bind --assets-dir .local/dependencies/reference_assets --binding project/analysis/workload_mapping/assets/reference_binding.example.json --physical --root .local/runs --output-dir binding-new
```

The last command intentionally returns **3** and saves the actual reference pin
pass, unknown protocol, and blocked physical conditions. It is not a mapping pass.
For typed v2 semantics, first convert the original fixed fixture using
`python -B -m project.analysis.workload_mapping.v2_bridge INPUT --expected EXPECTED --output-dir .local/runs/v2-input-new`,
then pass its graph/blocks plus `--semantics .../semantics.json` to build.

The two fixed graphs call the existing `block_v2_offline` numerical/protocol
oracles; the generic core has no fixture IDs or expected numbers. #48 accounting
is reused unchanged. Generic schemas, unknowns, actual asset limitations, and
server-version protection are explained in the main document.


新增通信优化实验命令：`python -B -m project.analysis.workload_mapping.search_experiment --suite full --workers 4 --export --output-dir .local/runs/search-new`。原两图不变；方法、串行通信优化边界、主表/消融及实验回执见[主要合同](../../../docs/WORKLOAD_MAPPING_INPUT.md)。这是新增研究模块，不是原CLI自动推断映射，也没有真实芯片时延结论。
