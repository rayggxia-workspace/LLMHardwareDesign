# Issue219：有约束规划器与真实来源验证

更新时间：2026-11-07 18:50 CST（Asia/Shanghai）。[Issue #219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219) / [草稿 PR #220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)，负责人 YUZE-LU。独立工作树 `C:/Users/wine10/AppData/Local/Codex/issue-219-general-block-search`，分支 `task/219-general-block-search`；未改动主线程工作树、其他硬件 PR 或其他作业。

## 当前结论

实现入口为 [block_synthesis](../../../project/experiments/block_synthesis/README.md)，不是旧 `block_search`。核心已有流式初解、链覆盖 DP、联合约束搜索和独立验证；**完整五类 Block / 完整 LLM 的综合尚未完成**。当前真实后端只有 #214 U/E 加法服务；其他宏的实现资格没有被冒充成已登记编译规则。

| 验收层 | 本轮证据 | 结论 |
| --- | --- | --- |
| 算法正确性 | 25 项服务器测试，含独立参考、负对照 | 通过；人工数据只测试算法，不作硬件/LLM 性能证据 |
| 原生宏/适配/S | 冻结 #214 来源的 U/N/E/四 SRAM bank 原始测试，三初态 | 通过；取得本轮 U/E 客户端边界的测量 |
| 生成计划原生回放 | 自动分配 S 地址、四项加法、原生描述符字段、生成 SV 客户端程序 | 三初态均数值/地址/80 周期一致；不含 LC 取指和初始搬运 |
| 完整模型前端 | Qwen2.5-3B，3,085,938,688 参数，36 层、Embedding、LM head，真实权重 | HF / ORT 三组输入通过，B1/S2 prefill、FP32、无 KV cache |
| 完整模型综合 | 2,277 个运行时节点；253 项离线只读权重布局 recipe | blocked_lowering；尚未登记 FLOAT 到真实定点/尺度/布局服务的分解，不是 16 KiB 不可行结论 |
| 原生母控/局控/DMA 程序 | 尚未完成生成镜像与统一回放 | 未通过；事件 IR/描述符不冒充可部署镜像 |
| 物理连接/时序 | 本轮未启动 P&R/RC 验收 | 未覆盖；无布通率、300MHz、线长或论文级改进结论 |

[输入和结果图册](results/joint-v1/report.html)可浏览全模型各层算子依赖、真实 U 服务输入图、执行时间轴、S 地址存活和局部搜索记录。浏览器在 1100/360px 核对选择器、内容、标签切换、JS 错误和页面溢出；窄屏图允许横向查看。原图和检查 JSON 在本地 `results/joint-v1/browser/`；报告自身不依赖截图。

## 实际算法和测试

服务资格先过滤，逐元素 tiler 从清单的合法片长/打包规格产生候选，覆盖 DP 不隐藏共享张量。快速调度器保留有效副本、分配连续 S 窗口，脏片段在外存写确认之后释放，需要时实际 LOAD。外存不是“无限免费缓存”：提供容量就检查，并生成稳定区域与搬运；未提供容量明确未取得容量资格。

CP-SAT 同时处理实例选择、计算/搬运各阶段、地址和生命周期、共享副本/重新加载、静态网 OR 及不兼容端点。流式初解保证有可回退的合法计划，局部搜索超时不丢弃它。跨层线路改动开放该线全部使用者；65 个非相邻消费者的用例验证没有按层截断，重复绑定可耦合压缩决策。小链与独立闭式参考对照；负例覆盖提前消费、ACK 前源释放、地址覆盖、陈旧副本、资源争用、外存越界、驱动冲突、未支持格式/属性。没有把 UNKNOWN 写成 INFEASIBLE。

自动 tiler 当前只接入有数值资格的同形状逐元素模式；矩阵 K 分片/累加、RMS/Softmax 统计与回放、GDN/KV 状态和 MoE 分支尚未接入编译前端。算法接口允许扩展，不能据此声称已经支持任意 3–4B 模型。

借鉴来源和实现模块对应见 [README](../../../project/experiments/block_synthesis/README.md) 与 [决策0010](../../../docs/decisions/0010-qualified-block-planner.md)。本轮没有移植论文源码或继承其最优性/性能数字。

## 服务器作业和来源

服务器根目录：`yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/`。以下正式作业均 `COMPLETED 0:0`，c64、`yzl-*`、`Timelimit=UNLIMITED`；实际 CPU/节点/耗时见 [Slurm 回执](results/joint-v1/slurm.psv)。

| 作业 | 目录 | 用途 |
| --- | --- | --- |
| 99777 | cp-environment-v2 | 离线依赖：OR-Tools9.10.4067、NumPy1.26.4、Pandas2.2.3、protobuf5.29.5；自己的 target，不改共享 venv |
| 99782 | qualify-u-v1 | 真实 U 来源包、原始测试/断言及服务测量 |
| 99785 | full-qwen25-3b-v1 | 完整 3B 权重导出及三组 HF/ORT 数值对照 |
| 99836 | full-audit-final25 | 最终代码完整导入/覆盖；原99810保留；未生成整网硬件计划 |
| 99834 | test-joint-final25 | 最终 25 项算法测试 |
| 99835 | native-plan-final25 | 最终生成计划三初态原生 U 回放 |

最终原始节点 8,027、简化 2,537。HF/ORT 最大绝对误差 `0.0002898872 / 0.0001579523 / 0.0002427101`；逐元素 `rtol=3e-4, atol=3e-4` 检查通过。这不是定点宏数值验收。[完整模型回执](results/joint-v1/full-model.json)、权重与导出输入/输出 SHA、[执行来源和结果索引](results/joint-v1/receipt.json)、[测试日志](results/joint-v1/tests.log)均已回收。执行时按文件 SHA 冻结；提交后的核心文件与执行文件逐项等价核对，见 `verification.json`。

U 功能来源为 #214 `f5fb8115ece2e125edda6c223f0538ed52c941c6` 的验收来源归档 `receipt-compact64-p-images/package/provenance/smoke-9IjPXp-source.tar.gz`（同包含 U 功能源），复制到本任务目录后执行。实际 archive、原 SRAM bank、测量日志、生成程序和执行文件 SHA 随回执索引保存。没有在他人目录做计算或修改原包。

收尾读回 #213 HEAD `b2179645bb13ed366eeac3d3e766efb42b68fdc8`：C_64/F_64 已通过，J_64 验收中。#214 HEAD 仍为上述 f5fb。#213 使用完整 #180 `2a66b918` 局控；#214 P/U 使用 #195 语义加 b54531b3 紧凑取指移植。共同 v2 编码不证明完整 profile 或描述符兼容，本轮没有混用两者。

## 必须保留的失败和边界

- 99775：计算节点 pip 无法联网/DNS；更换离线 wheel 和自己目录安装，不修改共享环境。
- 完整模型第一次带 `--mem=64G` 被提交器拒绝（节点内存元数据为1），没有产生作业；去除不可用的内存元数据约束后 99785 完成，不是模型内存失败。
- 99781：原 spill 测试允许先把片段搬到另一 S，不必 STORE；修正测试为本地 S 被 scratch 占满后还要本地消费，确实要求 STORE/LOAD。未伪造强制 spill。
- 99809：16 个小片段的 CP 在8秒内返回 UNKNOWN；加入流式合法初解、固定绑定裁剪和超时保留机制后通过。该失败不代表硬件不可行。
- 首次收集器误用服务器系统 Python3.6，保留 `joint-delivery-v1/`；切换已固定的 Python3.12收集，后续版本独立保存。
- 历史 0.6B、4MiB 和假设 FP32/互联的64组结果保留追溯，**撤出正式证据集合**。本轮没有再运行这些模型或场景。

## 尚需完成，恢复入口

1. 在现有 SystemC/RTL 数值实现上注册 M 矩阵、N 统计回放、G 激活、R 状态等服务，补齐参数/系数/格式和布局的真正 lowering。首个整网缺口是 embedding Gather 的外存读取与数值格式，不是强行把整行放进 S。
2. 将同一分片计划接入原生 DMA，核对数据、退休流量、真实 ACK 和背压；这会给出可用的外存路径时序/资源 profile。不能把 #182 独立 DMA 存在写成当前编译链已接通。
3. 对准已核验的 MC/LC 共同子集，实现镜像生成和母/局控完整回放；当前仅有事件 IR、U 描述符字段和客户端程序。
4. 按真实固定底座登记 M10 端点、驱动/接收负载、路由资源和反馈；保留失败上下文。路由失败不能直接变成永久不可行剪枝。
5. 覆盖全量3–4B benchmark：分别报告导入、映射、SystemC、RTL、物理，不以一个局部通过填满所有栏。

当前任务保持 in_progress，PR保持 Draft，不自合并或标 done。登记沿用 management-hub PR5 pending；缺 config/board.json，Projects权限/条目 unverified、同步 pending，维护者待指定。审查人待指定。已有成果可审查，但不是原定整网目标的完成回执。
