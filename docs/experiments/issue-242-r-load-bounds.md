# Issue #242：R 原始 LOAD 地址边界修复

日期：2026-11-09，Asia/Shanghai。负责人 Melodydt；[任务 #242](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/242) / [PR #243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。规则版本 rayggxia-project-collab 1.0.0。

## 问题与实现

主干 `c4d7b960599b9d292f27eb4429d5f226a7156c95` 的 R256 原始端口会接受 target 0/1、索引 64，再把地址截成状态行地址，导致覆写索引 0。target 5 的任意索引也会更新 decay/beta；其他操作数目标对非法索引的握手语义不统一。

修复在 `r_stream_local.sv` 的 `load_ready` 中增加完整索引检查，按目标与 `WORDS` 决定合法范围；所有装载写入均受现有握手约束。端口、合法装载时序、计算状态机及容量未变。原始非法请求无握手、无写入、无额外响应，直接调用者必须预校验或撤回。已有 C 适配器负责显式错误应答，源码未变。完整目标表、覆盖及复跑步骤见[回归说明](../../project/experiments/r_load_bounds/README.md)。

## 源码、配置与结果

实际测试 commit：[`f034be2b7c87137b92f7bfce274a5485647e512d`](https://github.com/rayggxia-workspace/LLMHardwareDesign/commit/f034be2b7c87137b92f7bfce274a5485647e512d)，包含 RTL、两个 testbench、run.py 和 Slurm 脚本。后续提交仅追加文档与轻量证据。

| 输入 | SHA-256 |
| --- | --- |
| 修复后 r_stream_local.sv | `48a93b2f4d4a5777eb4ef59f36cf635541498c660562353d430ec70470c04d84` |
| 旧 main r_stream_local.sv | `dc41d52eb88efe6cc592683b788d09da980c1c01e779ab54db9fb647d730363d` |
| 未修改 r_state_store.sv | `7b50c3abae20587ac49726fed375da6390fc1d4a260ae299939fc6725dae1d40` |
| 未修改 C 适配器 | `9d152b23fadbc906b23f0ebc6d6080bf2ff127baacaafdd1959dc9387b5d29d3` |
| ORFS 容器 | `49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a` |

全部 testbench、运行器和打包输入的版本见 [inputs.json](../../work/Melodydt/242/inputs.json)。输入为固定有符号模式和独立数值计算，无外部模型数据。Verilator `5.042 2025-11-02 rev UNKNOWN.REV`，容器 Python 3.10.12。`run.py` 记录实际命令和初态种子。每例执行全 1/143、随机/143、随机/144 三次。

服务器 `yuzelu@10.129.166.172`，工作目录 `/public/home/yuzelu/Melodydt/issue242-r-load-bounds/run01`。实际启动命令为 `cd /public/home/yuzelu/Melodydt/issue242-r-load-bounds/run01 && sbatch --parsable job.sh`。作业数组 `101572_0-3`、名称 `mdt-rbounds`，c64，每例 4 核，最多两例并行，实际节点 node1，时限 UNLIMITED。

| 数组项 | 案例 | 执行结果 | 单次覆盖 |
| --- | --- | --- | --- |
| 101572_0 | raw256 | 3/3 通过 | 8039 非法地址、163 合法装载、31471 检查 |
| 101572_1 | raw1024 | 3/3 通过 | 7631 非法地址、571 合法装载、48103 检查 |
| 101572_2 | service256 | 3/3 通过 | 28 个适配器事务 |
| 101572_3 | negative | 3/3 检出旧缺陷 | `invalid LOAD accepted WORDS=256 t=0 i=64` |

四个 Slurm 项均 `COMPLETED 0:0`。负控制仿真实际退出 1，运行器核验其诊断后退出 0；不将旧源码记为功能通过。汇总 [verification.json](../../work/Melodydt/242/verification.json)，原始作业终态 [sacct.txt](../../work/Melodydt/242/sacct.txt)，逐例 result.json 与 12 份日志见[证据目录](../../work/Melodydt/242/README.md)。已逐项核验源码及全部输出日志 SHA。

服务器保留编译日志、obj 与完整证据包 `evidence.tar.gz`；本地独立任务目录也有副本。证据包 SHA-256 为 `949031ef34ed9b2dc5cd841c67df6b9c82284128adb24d75d722c8e88eab348b`。仓库只接收轻量日志、结果与索引，不接收二进制和大包。

```bash
squeue -j 101572 -o "%.18i %.16j %.10T %.20N"
sacct -j 101572 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList -X
tail -n 25 /public/home/yuzelu/Melodydt/issue242-r-load-bounds/run01/slurm-101572_0.log
cat /public/home/yuzelu/Melodydt/issue242-r-load-bounds/run01/results-raw256/result.json
```

## 检查与证据边界

管理副本和独立任务副本均执行 `python -B scripts/check_project.py` 通过；运行器 Python 语法检查通过。既有 WIDTH 等编译警告保留；同配置 raw256 与旧源码负控制归一化警告头对比无新增警告。使用 `-Wno-fatal`，未宣称严格 lint 无警告。

本轮验证原始地址合同、状态/操作数保持、合法读写、decay/query-dot、背压与复位恢复。未执行原 192 项最终单元网表回归、综合、等价、P&R、STA、DRC；未执行实际大模型端到端仿真。新增保护逻辑会影响硬件，新 RTL 仅取得上述 RTL 功能证据，原 R256/R1024 的物理资格仍绑定原始冻结源，不能转移至本修复。详见[基础宏结果边界](../BLOCK_V2_RESULTS.md)。

任务提交审查后保持 `in_review`；独立审查人待指定。物理重新验收如需开展应另行明确范围和负责人。本任务不改变全项目里程碑，登记沿用管理中心 PR #5 pending；无 board.json/Projects 条目能力，看板 unverified、同步 pending，交接见[恢复入口](../handoffs/2026-11-09-issue-242-r-load-bounds.md)。
