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


2026-10-25 生命周期复核：干净源 `10cd3d97d3b8ca9cbb242b1eee0078c2d708f577` 在全新 `.local/runs/formal-04` 实际通过 **200 tests / 0 skip**（原32+31、适配器137，其中核心48），10场景独立源码副本/进程重放，科学SHA仍为 `f2ec30e28966be33888cf314bd5e93a0bb24378d4147d79cbdd9ad9971efbbdc`。修复显式复制后源槽复用的误拒绝，按实际驻留字节范围处理部分覆盖与多个view复制；独立consumer采用另一个范围覆盖算法，并重查alias/接口宽度/FIFO。新增3个合法/非法成对回归；最初负例因残留旧transfer源导致错误提前触发，保留本机失败和修正记录，未改原fixture。旧正式回执不覆盖，最新见 `work/huangpingyang04-lgtm/63/formal-04/receipt.json`。A/B选定范围pass、C仍blocked；软件in_review。

用户再次明确要求重试SSH后，仅执行一次BatchMode连接，结果为 `Connection closed by 10.129.166.172 port 22`，未建立远程会话、未读取或修改服务器文件；未改网络配置。旧服务器版本仍未比较，后续只读比较后在新目录整合，不能覆盖原件。
