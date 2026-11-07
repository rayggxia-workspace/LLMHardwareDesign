# Issue #219：Block 前沿搜索原型与服务器评估

**最新入口：[完整3B生成程序、有限调度与验收](FULL_RESULTS.md)。** 此前Gather阻塞已修复；完整Qwen2.5-3B的B1/S2数值/算法计划通过，未宣称全部bench、系统RTL或物理通过。

**当前入口：[零预连、虚拟外存与真实N/E修订结果](FIX_RESULTS.md)。** 下文是历史记录；其中 0.6B、4MiB 和假设 FP32/互联结果已撤出正式证据集合，不再用于判断真实 16 KiB 底座能力。后续代码在 `project/experiments/block_synthesis/`，本轮完整模型改用真实 Qwen2.5-3B。

任务：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219

执行账号 YUZE-LU；隔离分支 `task/219-general-block-search`；未修改主线程工作树或 #213/#214。源代码与合同边界见 [原型说明](../../../project/experiments/block_search/README.md)。

## 证据入口

服务器 `yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/`。

- 完整 Qwen3-0.6B：`full-qwen3-v3/`，596,049,920 参数；原始 6,839 节点，简化 2,285 节点。包含 embedding、28 层和 LM head。B1/S2、无 KV、FP32，三组 token 的 HF 与 ORT 最大绝对误差分别 3.064e-5、8.774e-5、4.578e-5；同时核对默认与显式因果 mask。该结果不代表宏数值通过。
- 99667：首次整网导出因 `aten::diff` 不受 legacy ONNX exporter 支持而失败。99672：显式 S2 因果 mask 版完成。99677：形状折叠版完成，保留 raw 与简化图。
- 99674/99679：初始评估；保留动态 shape 导入失败、容量失败与 beam 劣于贪心的证据。
- 99680：保留贪心候选；99681：增加离线只读权重布局 recipe，避免将整个权重转置矩阵当作运行时 S 激活。
- 99687：共享不可变历史后的评估；源码 commit `f1cf8b999`，冻结 `source-v6/` 与 `source-v6.sha256`。
- 99697：依赖 99687 成功的一次性回放、图表和哈希收集，不是周期监控。

最终评估为 **99698 / evaluate-v7 / source-v7 / commit 2e38eeaa8**，2 CPU，c64/node1，COMPLETED 0:0，2分23秒。不同 source-v* 不覆盖；v2 的 CRLF 脚本被 sbatch 拒绝，未执行，后续 archive 显式关闭 autocrlf。

99681、99687 为被新实现替代的本任务重复评估，已停止并保留部分结果；99697 的旧依赖收集也取消，没有遗留永不满足的依赖。没有取消其他 Issue 的作业。99699 收集因旧作业已从 scontrol 清除而失败；99700 修正后完成；99702 完成移动端图表修订后的最终收集，均保留日志。最终以 sacct 作为旧作业终态，scontrol 查询失败本身也如实保存。

最终回执 [delivery.json](results/delivery.json)；[64 组对照](results/summary.json)；[工具/源码哈希](results/run.json)；[输入与结果图册](results/report.html)。原始完整计划、硬件场景与归一化图均在服务器 `evaluate-v7/`，逐项输出 SHA 在回执中。回收的 summary/run/report 三项 SHA 与服务器回执一致。初次审计快照单独保留为 `delivery-audit-v8.json`。

## 实际结果

64 组中 23 组生成分析计划，41 组保留候选无可行扩展。23 组均通过独立重放。16 KiB 的32组均未完成；4 MiB场景中，Granite MoE、Falcon-H1、Qwen3.5 GDN仍未完成，其他七类层与完整Qwen3可生成分析计划。失败不是全局不可行证明，也不说明真实硬件无法通过分片运行。

完整Qwen3经只读权重预处理recipe后有2,081个运行时任务：

| 假设4 MiB场景 | beam=1 | beam=4 |
| --- | ---: | ---: |
| 分析延迟，cycle | 188,664,949 | 188,665,821 |
| 静态连接代价，任意分析单位 | 3,106 | 1,859 |
| 编译耗时，秒 | 23.399 | 96.116 |
| 状态合并数 | 0 | 0 |

静态代价下降约40.15%，延迟增加872 cycle，组合目标略有改善；代价未基于真实pin/RC标定，不能称物理线长或电气收益。此次收益来自多候选保留，尚未显示DP状态合并的价值。未优化资源区间查询的相同贪心整网方案耗时147.851秒，区间索引/相邻占用合并后23.399秒；输出延迟与连接代价一致。

原型服务器v7的9项回归通过；最终增加任意实例命名、实例数和带宽变化检查，本地10项通过。99703误用系统Python3.6，缺dataclasses而失败，修正运行器后**99704完成，10项通过**；[日志及三份执行源SHA](results/verification-v11.log)。200组随机区间分配与逐周期穷举空窗对照通过；源提前释放、资源重叠、静态连接缺失的负对照被拒绝。图册5种视图在800/360px通过浏览器交互与文本边界检查。

## 后续必须完成

1. 将#213/#214原生服务的数值、描述符、端点和局控资源合同接入硬件清单；去掉假设FP32/索引服务。
2. 实现多算子覆盖与分片/外存溢出，让16 KiB场景能够形成合法计划；不能以扩容替代这一步。
3. 补真实控制/适配器阶段和ACK事件；根据同一计划生成原生MC/LC镜像，再与SystemC/RTL对照。
4. 用实际pin可达性、负载/RC/时序反馈替换静态分析代价，加入强调度/约束规划对照及更多整网/执行范围。

因此PR#220保持草稿，Issue#219未关闭，尚未把整个通用综合目标标记为完成。

## 必须保留的限制

该交付为**分析算法原型**。尚缺自动分片/spill、多算子覆盖、原生控制镜像与真实 pin/电气约束。现有宏不支持所有假设 FP32/布局服务，严格模式拒绝假设架构。16 KiB 与 4 MiB 是容量分析对照，后者不是已有硬件。其余模型输入是完整 decoder 层，不是整模型。Llama 沿用原资料中随机参数配置边界。

## 协作回执

规则 rayggxia-project-collab 1.0.0；project_id=llm-hardware-design；负责人 YUZE-LU；Issue #219。登记沿用 management-hub PR #5 pending。当前没有 config/board.json，看板字段和条目 unverified，同步 pending，处理人待维护者指定。独立审查人待指定；不自合并，不关闭整个综合任务。
