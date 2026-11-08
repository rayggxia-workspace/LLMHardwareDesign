# main 真实大模型仿真就绪性审计

2026-11-08，Asia/Shanghai。负责人 Melodydt；[Issue #232](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/232)。

**结论：可以开始真实模型的分阶段功能实验；当前 main 尚不能直接加载一个真实大模型并完成全部层、prefill/decode 的统一 RTL 仿真。** 已有五类 Block、母控和可复跑的小型 RTL 流程；整模型 SystemC、真实层 RTL、模型编译和外存集成分散在未合并任务中。完整物理系统的验收也不能从独立宏通过推导。

## 基线、完整性与审计边界

- 新分支 `task/232-main-model-readiness` 从最新 main `c4d7b960599b9d292f27eb4429d5f226a7156c95` 创建；创建后读回 ref 指向同一 commit。main Git tree 为 `1ae905e08e375860ab19ebd4096b422d3781a37a`，递归清单未截断，共 1,789 个文件。远端分支完整继承该树，未挑选或混入 PR180/198 的实现。
- 本机根目录是管理资料副本，并非 Git checkout。本次在独立 `work/Melodydt/232/audit-main-c4d7b960/repo` 拉取审计所需文件；按 main Git blob 验证所用文件，运行源码包另有 SHA-256。此目录是部分审计快照，不宣称执行了完整 CLI clone/fetch/pull，也不以本地未下载的文件判定远端缺失。
- 仓库级目录存在性由完整远端树判断；代码检查和实测只覆盖明确列出的文件/用例。`ref-project/` 只保留在远端主干树内，不阅读其内部内容、不重新计算其完整性、不作维护。
- 使用本人 Melodydt GitHub 连接；复用仓库 Skill 1.0.0、任务分支/PR、Slurm、本人目录、持久日志和分阶段验收规则。其他会话仍负责 #179 / PR180，本任务未修改其目录、分支或作业。

## 主干实际具备什么

| 项目 | 当前 main 的证据 | 能支持的结论 |
| --- | --- | --- |
| P/U/C/F/J 与私有 S | `project/rtl/pu_leaf_base/`、`block_cfj_v1/`、`s_sram/`；[五类两格式入口](assets/five-leaf-bases/README.md)、[U 修复回执](../../work/YUZE-LU/212/u-native-fix.md) | 有独立实现及限定条件下的物理/功能证据；不等于九实例整网通过 |
| 母控与程序 SRAM | `project/rtl/mother_control_v1/`；[双格式报告](mother-control-dual-format.md) | 两驻留目标、固定原生 profile；64/128 位格式共用 128 位 PM 口。组合测试中局控 PM 仍有行为夹具 |
| 服务器回归 | `project/experiments/pu_leaf_base/native_entry.sh`、`control_replay.sh`，以及 `mother_control_v1/` 的运行器 | 可在已授权容器/计算节点执行定向 RTL 回归，仍依赖冻结外部源和真实 SRAM 模型 |
| 模型资料 | `docs/model-analysis/` | 有模型图和历史分析，不是整模型可执行部署包 |
| 独立宏证据检查 | `project/experiments/block_v2/check_release.py` | 当前实际执行失败，见下方；管理结构通过不能替代此检查 |

完整 main 树的 `project/` 只有 `experiments/` 和 `rtl/`。其中没有 `project/systemc/`、`project/control_task_compiler_v1/`、`project/experiments/seven_model_system_bench/` 或 `project/experiments/qwen_layer_dma/`。模型权重不随此仓库交付；本次未重新核验全部检查点的授权共享位置、版本或 SHA，不将旧任务可访问视为本人本次已备齐输入。

## 已有但尚未合入 main 的成果

以下属于其他任务的来源证据，本次只读核验，不转移其验收或接管任务。

| 来源 | 已报告的能力 | 本次使用限制 |
| --- | --- | --- |
| [PR146](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/146)、[PR154](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/154) | 七宏 SystemC 和整模型执行源 | 未合并；不能按 main 的一条命令直接启动 |
| [PR198](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/198)，`cc6bf8ed98b8489cafc59305b5def5351e662c11` | 七模型 SystemC 行为外存：165 处理位置/84 生成 token，与冻结输出逐字节一致；Qwen3.5-4B 第0层 GDN/第3层注意力、两个位置、完整2560维及 FFN 的 RTL+DMA 对账 | 测试台承担编排、尺度和格式服务，计算宏与 DMA 独立推进时钟；不是统一控制的整模型 RTL。与冻结输出一致也不代表原 FP32 数值门全部通过 |
| [PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180) | 母控/局控镜像、装载和恢复研究 | 活动开发中、未合并；main 的母控只锁定其中指定历史源，不能视为包含其全部新能力 |
| [PR182](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/182)、[PR195](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/195)、[PR196](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/196) | 分组 DMA、Block 控制、Qwen FFN 编译切片 | 各自合同和拓扑不同，需受审查的依赖整合，不能直接拼接并继承系统资格 |

PR198 的[两层实测报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/cc6bf8ed98b8489cafc59305b5def5351e662c11/docs/experiments/issue-197-qwen-rtl-layer-dma.md)、[整模型 RTL 缺项](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/cc6bf8ed98b8489cafc59305b5def5351e662c11/docs/experiments/issue-197-full-model-rtl-gaps.md)和[SystemC 外存报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/cc6bf8ed98b8489cafc59305b5def5351e662c11/docs/experiments/issue-197-systemc-offchip.md)提供进一步边界。本轮没有重跑这些模型，不把其历史作业记为本次通过。

## 阻止直接开始整模型 RTL 的缺口

1. **执行程序与统一顶层。** 需要固定目标实例清单、ID/ABI/拓扑、程序容量和算子到指令的映射；生成全部层、头、分片、prefill/decode 的母控/局控镜像。现有两端控制测试不能证明完整模型可调度。
2. **数据与完成通路。** 需要将选定 DMA 真正接入每个私有 S 的仲裁、预约、写确认、代次、错误排空及协调复位；定义有限带宽/容量外存和时钟域。外存行为模型可以用于数字仿真，真实 DDR/HBM PHY 不是此功能阶段的前提。
3. **权重、KV、递推状态和数值合同。** 需要共享输入索引和模型版本/SHA，固定每条边的位宽、尺度、舍入、饱和、布局、尾部掩码；实现 KV 追加/读回和 R 状态版本发布。R 算术已有实现，缺口是模型规模下的状态编排，不能写成“R 被禁止使用”。
4. **测试台与模型边界。** 明确 embedding、RoPE、动态尺度、词表投影、argmax 和 token 回送由 RTL 还是声明的 host 接口承担；逐层/逐 token 与独立参考对账，分开统计 DUT 和测试台行为。未接统一时钟前不能推导整模型周期、吞吐或能耗。
5. **版本和证据一致性。** 修复/解释下述独立宏清单漂移；任何新集成必须记录实际来源和新结果，不能仅更新 SHA 就继承历史功能/物理资格。

## 本轮实际验证

| 检查 | 结果与边界 |
| --- | --- |
| `python scripts/check_project.py` | 管理结构通过；本机默认 Python 过旧，后续明确用 Python3.12.14；服务器使用 Python3.12 |
| main 文件 Git blob、Python AST | 对已拉取审计文件逐项核验；清单和实际数量见 `work/Melodydt/232/audit-summary.json`。AST 只检查语法，不执行业务 |
| `python -B project/experiments/block_v2/check_release.py` | **FAIL**：`pins.py` 首项不符；逐项只读对比另找到 `receive.py`、`map.py`、`physical.py`、`qualify.py`，合计五项。当前文件均精确匹配 main Git blob，转换 CRLF 后也不匹配清单。详见 `release-check-findings.json`；未更改清单或绕过检查 |
| 主干 U 原生入口 RTL | **PASS 3/3**：Slurm100556，c64/node1，4核，`COMPLETED 0:0`，有效时限 UNLIMITED。原样使用 main 的25个源码文件及已锁定外部控制源/SRAM模型，Verilator5.042；覆盖0–3源FMA、准确S读次数、延迟ACK和非法N/lane拒绝 |
| 失败/环境记录 | 首次打包校验因Windows换行在提交作业前失败；100554因本轮环境采集在容器外执行Verilator而FAIL1:0，未进入RTL。100556只修正采集方式，输入源码包相同；失败记录保留 |
| 未执行 | 本轮整模型软件推理/SystemC/RTL、全部Block回归、全系统门级、P&R/DRC/STA、PVT、DDR/HBM器件校准及能耗验收均未执行 |

服务器输出留在本人独立目录，日志、输入/输出 SHA 和可复制追踪命令见[本任务交接](../handoffs/2026-11-08-issue-232-main-audit.md)。本次小型回归证明基础链路可复跑，不赋予完整 ISA、模型精度或物理系统资格。

## 建议起步范围与验收

建议先选择 **Qwen3-0.6B 的真实短序列**作为 dense 基线：通过受审查的依赖整合引入固定 SystemC/输入和冻结参考，先复跑完整模型功能；再完成一层真实 RTL、一个 prefill 及至少两个连续 decode 的统一控制回放，最后扩展到全部层。选择该模型是降低首轮容量和递推状态复杂度的工程建议，本次未下载权重或启动整模型任务。

若优先复用已验证的 RTL 层链路，可从 PR198 的 Qwen3.5-4B 两层用例接续；应保持2560维、完整矩阵和两个连续位置，先重跑来源证据，再把测试台调度迁入母控/局控。它更靠近已有真实层 RTL，但会同时引入 GDN/R 状态复杂度。

开始新模型作业前，应完成：固定输入授权位置和SHA、锁定依赖提交/数值合同、验证统一顶层装载与执行入口、先跑小型预检。成功判据是逐层与逐token输出和状态/内存退休事务对账、错误与背压下可恢复，以及源/工具/输入/输出可追溯。上述工作是建议的后续实现范围，本次审计没有将其标为已实现。
