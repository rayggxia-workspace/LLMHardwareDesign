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


## 2026-10-26 服务器验收补充

用户重新授权服务器操作后，已只读比较旧目录8文件：core/resource_bridge/test_resource_bridge与发布版SHA不同；5个vendor资料仍保留，当前发布版改用固定的兄弟llm_resources。旧目录实际上缺少consumer.py、cli.py、__init__.py；旧记录的“曾实存CLI/consumer”未由本次观察支持。旧目录未修改、未移动或覆盖。

在全新 `/public/home/yuzelu/PingyangHuang/issue-63/server-validation-20261026T0100/repo` 核验发布源 `d07abaeef16049da199f0efa96acffc95bd487dd`，通过Slurm作业91622（hpy-adapter63、debug/node27、1CPU、23秒、COMPLETED/0:0）实际200项/0skip、10场景独立源码与新进程重放通过；科学SHA仍f2ec30e28966be33888cf314bd5e93a0bb24378d4147d79cbdd9ad9971efbbdc，与Windows逐字节相同。仅传输本任务Git对象、固定参考输入；未传凭据/配置/环境，未读#55活动文件或干扰作业。最初2G内存请求被Slurm拒绝（节点公布内存1MB），保留失败，命令覆盖--mem=0后提交成功，未改集群配置。

精选证据在 `work/huangpingyang04-lgtm/63/server-20261026/`；原始日志与完整输出留新服务器目录。receipt中的server_access=false表示离线验收器自身不发SSH，不代表本轮未在服务器执行，执行平台由execution.json和Slurm记录明确区分。A/B选定范围pass；C仍缺同版实例/真实M8引出/冻结底座等证据。软件实现、离线验证与服务器复跑均完成；正式结项仍待PR79审查/合并，当前零reviews、Issue in_review，不能宣称done。看板仍unverified/同步pending。


2026-10-26通信优化实际结果及复跑命令见[研究交付](search-20261026/README.md)。19格主/消融实验及12格强化贪心各双轮独立源码复跑一致，223回归通过。相同合成资源下，强化贪心相对固定顺序线上字节减少14.2873%，beam减少10.9374%；保留更强基线和负面结果，不宣称真实芯片速度提升。
