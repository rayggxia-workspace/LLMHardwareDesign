# 母控与局控研究接续指南

2026-11-06，Asia/Shanghai。负责人 Melodydt。工作属于 [Issue #179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR #180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)，分支为 `task/179-local-block-continuation`。Block 设计输入来自 [PR #176](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/176) 的 `08f2ea20a11dfdd09892a67599163e32b7237edb`。

## 十分钟读懂当前成果

| 要了解什么 | 从这里开始 |
| --- | --- |
| 方案和进度 | [七页研究摘要与指令参考 PDF](CONTROL_RESEARCH_AND_ISA_QUICK_REFERENCE.pdf)；[持续更新的完整方案](TWO_LEVEL_CONTROL_PLAN.md)及[同名 PDF](TWO_LEVEL_CONTROL_PLAN.pdf) |
| 指令编码和编译入口 | [ISA v0.1](CONTROL_ISA_V0_1.md)、[机器可读编码](../../project/control_isa_v0_1/isa.json)、[镜像装载](../../project/control_image_v0_1/README.md)、[R6 任务到镜像](../../project/control_r6_v0_1/README.md) |
| 实际 RTL | [母控](../../project/control_rtl_min_v0_1/mc_min_controller.sv)、[局控](../../project/control_rtl_min_v0_1/lc_min_controller.sv)、[试验接线和原生 ABI](../../project/control_f_compute_v0_1/trial_bindings.json) |
| 测试程序和复现入口 | [J/C 镜像生成](../../project/control_jc_trial_v0_1/trial.py)、[C 作业脚本](../../work/Melodydt/179/control-c-job.sh)、[服务器操作与恢复记录](../handoffs/2026-11-04-issue-179-local-block-continuation.md) |

母控调度 Block，局控从本地程序存储取指，宏适配器驱动原生端口。`G_CALL` 传目标、任务描述符和参数，`L_EXEC` 引用本地服务描述符。跨块数据由源端发往目的 S，目的实际写入后返回确认，源端随后释放数据。当前母控试验 RTL 支持两个目标和 8 个全局令牌，局控每块一个活动任务、一个在途服务。生成镜像要按所选接线、ABI 和受支持的指令子集校验。

## 按已验证的版本接续

已验证的控制 RTL 基线是 `160c97f6e1c92fcca205cc8f7e7820bb3257137b`。七页 PDF 也以此提交为版本标记，文件 SHA-256 为 `49088da4747b6e9bae14a34fdc498a2c171b6a1832f1a22f28032c032fef9244`。后续进展以 PR180 的回执和完整方案为准。

如果另一个分支只需要参照控制接口，在已有克隆中单独检出基线，可以并排对照两份代码：

```bash
git fetch origin task/179-local-block-continuation
git worktree add --detach ../llm-control-reference 160c97f6e1c92fcca205cc8f7e7820bb3257137b
```

如果工作本身要从这套 RTL 接续，先确定对应 Issue，再用该提交建立独立任务分支和目录。将 `ISSUE_NUMBER-topic` 替换为实际 Issue 编号和主题。

```bash
git fetch origin task/179-local-block-continuation
git worktree add -b task/ISSUE_NUMBER-topic ../llm-control-next 160c97f6e1c92fcca205cc8f7e7820bb3257137b
```

从新工作目录运行管理结构、编码和 R4 接口静态检查。功能仿真和时序复现按现有[服务器规则](../REMOTE_RULES.md)及各证据索引执行。

```bash
python -B scripts/check_project.py
python -B project/control_isa_v0_1/test_codec.py
python -B project/control_r4_v0_1/check_contract.py
```

## 可沿用的试验证据

| 类型 | 基线结果 | 接续时应保留的边界 |
| --- | --- | --- |
| P | 直接写回 5/5，经 G 写回 9/9，双局控联跑 10/10。[证据](../../work/Melodydt/179/control-chain-validation.json) | 双局控交接使用固定试验接线。生产顶层的 S 选型、数据端点和反向确认仍需核对。 |
| F | 单 F 11/11。[证据](../../work/Melodydt/179/control-f-validation.json) | 真实 G/E/S 的局部写回和读回。 |
| U | 单 U 12/12。[证据](../../work/Melodydt/179/control-u-validation.json) | 真实 N 分段统计、S 回放和 E 写回。 |
| J | 单 J 9/9。[证据](../../work/Melodydt/179/control-j-validation.json) | 真实 T 片段提交、逐字确认和释放。 |
| C | 单 C 11/11，作业 97863，既有 RTL 回归 56/56。[证据](../../work/Melodydt/179/control-c-validation.json) | 真实 R256/E/G/S。消费者用真实 S 试验夹具，第二个局控待接。 |

R7.3.6 由 Melodydt 继续研究 F/U/J/C 跨块写确认、源释放、丢确认后的复位重装和独立 300 MHz 时序。实现端可先提供同版本 Block 顶层、S 容量和端口、正向数据与反向确认端点。生产 M11/M12 互连和组合时序仍待联合验收。项目登记 [PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 待合并，项目看板缺配置，生产顶层与审查人待指定。