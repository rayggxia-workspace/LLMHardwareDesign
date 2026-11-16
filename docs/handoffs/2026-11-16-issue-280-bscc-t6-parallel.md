# Issue #280 BSCC-T6 三窗回放与 DMA 物理实现

北京时间 2026-11-16。仓库 `rayggxia-workspace/LLMHardwareDesign`，项目 `llm-hardware-design`，负责人 Melodydt，分支 `task/280-seven-model-energy`。本次从 `b2fe2c0f368857d7c98d01733fbffbb515e0f1f7` 接续。冻结 Qwen3 入口源码 `ac2a7265d4510e0fc73164a83ebb5355da586a88` 和作业 116481。C639 物理入口沿用 `91812f2891ba9ec563fb5a41aff71920129fe761` 引用的 116937 RTL 与 117939 的 300 MHz SDC。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)

## 已部署并验证

服务器 `ssh.cn-zhongwei-1.paracloud.com`，工作根 `~/LLMHardware/zenanyan/issue-280-bscc-t6-01`。OpenROAD 镜像和解包环境位于 `~/LLMHardware/opt`。运行环境作业 38769328 在 `m3ca0104` 以 12 核、1 分 07 秒 `COMPLETED 0:0`，固定 Singularity 3.7.0。计算节点已实际启动 OpenROAD、Yosys 0.68+post、NumPy 2.2.6。回放启动前通过原 frozen source、upstream 和 baseline SHA-256 清单。使用从原 116481 FP32 参考缓存生成的 KV 镜像。校验原始 FP32 参考散列、布局和镜像内容。同源 replay 审计校验两份计划各自的 SHA-256、搬迁仍对应的相对路径与资产实际散列，再比较其余计划字段、逐层结果、DDR 快照和事务守恒。

| 已迁移工件 | SHA-256 |
| --- | --- |
| ORFS SIF | `49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a` |
| 冻结回放归档 | `2e06361d0bbc25f277c1f1403734f48d804a568cc7c9f4d09ce2b86c71406188` |
| 共享读和阶段切换归档 | `b0a59912f9fef3ab2401776986a30e4280c9377f5facaa0fe60e88fc9a1a2c78` |
| 512-bit FFN 写回归档 | `146d3e5635d32d4b19eb2a32948d41191557c3e79b9ef0c3eea665c4b35129be` |
| 回放以原散列补齐的 pilot 输入清单 | `2c5454812681ea939b107ef4c5d09cbda2d1a1a4d144acb1f8292f61d566873f` |

早期 38769138／38769243 在模块脚本读取未定义 PAMENV 时退出。38769263／38769264 在站点 Singularity 配置缺失时退出。38769304 的备用模块预检在临时解包时超出内存。38769328 完成原 SIF 在共享存储的独立解包并验证。38769385 因缺少归档的 `pilot-inputs.sha256` 退出，已按原散列补齐并重提 38769452。所有实际 Slurm 提交均为 `--time=0`。

## 本轮作业

以下目录相对工作根，分区均为 `v6_384`。提交命令通用前缀 `sbatch --parsable --time=0`。北京时间 16:47 读回三项 `RUNNING` 和写回作业 `COMPLETED 0:0`。

| 作业 | 工作目录 | 节点及核数 | 提交前缀后的命令 | 日志及结果 |
| --- | --- | --- | --- | --- |
| 38769452 Qwen3 三窗事务 | `replay/` | `m3ca2408`，2×12 核 | `run_bscc_t6_qwen3_dma.sbatch` | `slurm-38769452.log`，`replay-38769452/` |
| 38769386 共享读 DMA | `physical/` | `m3ca0405`，12 核 | `run_bscc_t6_dma_physical.sbatch shared` | `slurm-38769386.log`，`physical-38769386/` |
| 38769388 阶段切换及所含共享读 DMA | `phase/` | `m3ca0504`，12 核 | `--job-name=mdt-280dmaphase run_bscc_t6_dma_physical.sbatch phase` | `slurm-38769388.log`，`physical-38769388/` |
| 38769390 512-bit FFN 输出写回 | `writeback/` | `m3ca0801`，12 核 | `--job-name=mdt-280dmawrite run_bscc_t6_dma_physical.sbatch writeback` | `slurm-38769390.log`，`physical-38769390/` |

38769452 已构建探针并进入 Prefill 和 Decode 的逐层回放。38769386／38769388 已进入 Yosys 综合。38769390 的 `ffn_down_store_scope` 经最终布线 DRC 0，300 MHz 最差 setup **+368.527 ps**，hold **+6.77053 ps**。最终网表、ODB、SDC、SPEF 和报告均通过 SHA-256。结果清单散列 `09f5f7bde0f88f27234b1b5be28c47eab0652d73c6fd06aa62296bb52cbb3951`。该工件对应冻结 C639 的 FFN 输出 writer。下一层残差写回使用另外的生产者，DPI 设备接口继续按仿真边界处理。

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01
squeue -j 38769452,38769386,38769388,38769390 -o '%i|%j|%T|%N|%C|%l|%R'
sacct -X -j 38769452,38769386,38769388,38769390 -o JobID,JobName,State,ExitCode,Elapsed,NodeList,Timelimit
tail -n 20 replay/replay-38769452/{prefill,decode}.log
tail -n 20 physical/physical-38769386/flow.log phase/physical-38769388/flow.log
(cd writeback/physical-38769390 && sha256sum -c physical.sha256)
(cd replay/replay-38769452 && sha256sum -c results.sha256 && cat dma-windows.json)
```

推进顺序为核验 38769452 三窗与两项读侧物理终态，随后补齐 6,144-bit 活动、其余写回覆盖和代表性工况的 DMA 功耗标定，最后将 DMA、其他片上分项和 DDR 芯片按相同窗口合入。Melodydt 后续用上述命令复查。Slurm 在聊天之外独立运行。

项目管理结构、Python AST、Bash 语法、迁移路径正负例、封存清单及写回物理结果通过实际核验。规则 rayggxia-project-collab 1.0.0。#280 进行中，PR #281 草稿待审查，登记 PR #5 待合并，组织 Projects 条目待管理员核验。
