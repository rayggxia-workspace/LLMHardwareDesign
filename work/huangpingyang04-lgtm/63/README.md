# Issue #63 selected delivery evidence

Issue: https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/63
PR: https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/79

- source_inventory.json: recovery/local continuation, pinned dependencies and server originals not read.
- delivery.json: concise scoped status and execution-source commit.
- receipt.json: actual clean-source 195-test run, fixed-byte hashes and each process exit.
- science.json: deterministic selected results and SHA equality across 10 independent-source-copy replays.

Raw sources, archives, all outputs, failed attempts and stdout/stderr stay in ignored .local/runs and .local/dependencies. The original server version is protected and has not been compared or changed.

Reproduce from the repository root using a new output directory:

```powershell
python -B -m project.analysis.workload_mapping.validate_delivery --output-dir .local/runs/formal-new --reference-root .local/dependencies/reference_assets
```

A is selected logical/software scope; B is selected old real macro import/pin checking; C remains blocked. No full model, physical integration, routing or PPA claim. No Issue closure or PR merge is authorized.
