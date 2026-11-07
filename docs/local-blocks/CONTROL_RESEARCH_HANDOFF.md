# 母控与局控研究接续指南


## 当前接续入口：五类原生前端与返回缓冲

代码基线 `ec8b8acae39cf42fc74fe0e659a962eba93474e3`，PR176 `08f2ea20`；原生输入固定 PR213 `1bb43127` 与 PR214 `33821f73`。采用当前 64 bit 局控显式原生配置，U/F/C/P/J 的试验程序 17/17 通过。母控和双局控间新增可综合单槽 512 bit 返回缓冲，5/5、零警告 lint、结构综合通过。目标时钟周期保持 3.333333333 ns。

最新 [复现说明及输入锁](../../project/control_frontend_v1/README.md)、[验收门清单](../../project/control_frontend_v1/frontend-gates.json)、[结果与源码/报告 SHA-256](../../work/Melodydt/179/frontend-validation.json) 共同构成可执行接续入口。[研究和 ISA PDF](CONTROL_RESEARCH_AND_ISA_QUICK_REFERENCE.pdf) 已原位更新到 15 页，含原生 ABI、指令字段、装载、返回缓冲和生产验收条件。

原生基准 12/12、C/F 交换 12/12、准入 16/16、P16 ACK 13/13、软件 42/42、7 种局控结构综合通过。旧 U 操作数计数错误和旧 C/F 同时发送死锁均被负例检出。两份 R6 输入独立复核通过；历史默认、紧凑、复位及 U/J/C 回归继续有效。最新上游两份测试输入变化已按 Git blob 同步，相关程序 3/3 和交换 12/12 再验通过。

当前已交付无需正式产品绑定即可独立执行的控制工作。A1 七项生产绑定未冻结；实际 M11/M12、CDC、复位和新增整链物理仍按 A2–A5 接续。结构综合不代替 300 MHz 时序。完整历史方案和运行档案在获授权工作环境原位维护，本分支共享版去除内部调度细节。Issue 保持 in_progress，PR Draft，审查人待指定；登记 PR5 pending，看板配置及同步 pending/unverified。


2026-11-07，Asia/Shanghai。负责人 Melodydt。工作属于 [Issue #179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR #180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)，分支为 `task/179-local-block-continuation`。Block 设计输入来自 [PR #176](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/176) 的 `08f2ea20a11dfdd09892a67599163e32b7237edb`。

R7.3.6 已完成固定拓扑上的 F→P 协调复位重装、U/J→P 两字写确认、C→P 状态发布和独立 300 MHz 验收。定向 17/17、既有集成回归 85/85、独立时序 12/12。复现本轮时，以 PR180 中包含 `project/control_r736_v0_1/` 的提交和[验证索引](../../work/Melodydt/179/control-r736-validation.json)为入口。下方固定提交用于复现 R7.3.5，当前指令格式及进度见更新后的 PDF。

64 bit 历史批次 通过专项 9/9、紧凑镜像联跑 39/39、旧格式集成回归 16/16。300 MHz 独立时序 12/12，最小 setup +0.199837 ns，最小 hold +0.086654 ns。 生成器使用 `--instruction-version 2`。 [64 bit 验证索引](../../work/Melodydt/179/control-isa64-validation.json)

## 十分钟读懂当前成果

| 要了解什么 | 从这里开始 |
| --- | --- |
| 方案和进度 | [研究摘要与指令参考 PDF](CONTROL_RESEARCH_AND_ISA_QUICK_REFERENCE.pdf)；[历史完整方案](TWO_LEVEL_CONTROL_PLAN.md)及[历史同名 PDF](TWO_LEVEL_CONTROL_PLAN.pdf) |
| 指令编码和编译入口 | [64 bit ISA 与旧版编码](CONTROL_ISA_V0_1.md)、[机器可读编码](../../project/control_isa_v0_1/isa.json)、[镜像装载](../../project/control_image_v0_1/README.md)、[R6 任务到镜像](../../project/control_r6_v0_1/README.md) |
| 实际 RTL | [母控](../../project/control_rtl_min_v0_1/mc_min_controller.sv)、[局控](../../project/control_rtl_min_v0_1/lc_min_controller.sv)、[试验接线和原生 ABI](../../project/control_f_compute_v0_1/trial_bindings.json) |
| 测试程序和复现入口 | [J/C 镜像生成](../../project/control_jc_trial_v0_1/trial.py)、[最新功能与回归脚本](../../work/Melodydt/179/control-isa64-rtl-job.sh)、[独立时序脚本](../../work/Melodydt/179/control-isa64-sta-job.sh)、[服务器操作与恢复记录](../handoffs/2026-11-04-issue-179-local-block-continuation.md) |

母控调度 Block，局控从本地程序存储取指，宏适配器驱动原生端口。`G_CALL` 传目标、任务描述符和参数，`L_EXEC` 引用本地服务描述符。跨块数据由源端发往目的 S，目的实际写入后返回确认，源端随后释放数据。当前母控试验 RTL 支持两个目标和 8 个全局令牌，局控每块一个活动任务、一个在途服务。生成镜像要按所选接线、ABI 和受支持的指令子集校验。

## 按已验证的版本接续

旧 R7.3.5 的固定控制 RTL 基线为 `160c97f6e1c92fcca205cc8f7e7820bb3257137b`。64 bit 研究的当前源码和证据从 PR180 取用。

如果另一个分支只需要参照控制接口，在已有克隆中单独检出基线，可以并排对照两份代码：

```bash
git fetch origin task/179-local-block-continuation
git worktree add --detach ../llm-control-reference ec8b8acae39cf42fc74fe0e659a962eba93474e3
```

如果工作本身要从这套 RTL 接续，先确定对应 Issue，再用该提交建立独立任务分支和目录。将 `ISSUE_NUMBER-topic` 替换为实际 Issue 编号和主题。

```bash
git fetch origin task/179-local-block-continuation
git worktree add -b task/ISSUE_NUMBER-topic ../llm-control-next ec8b8acae39cf42fc74fe0e659a962eba93474e3
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
| C | 单 C 11/11，既有 RTL 回归 56/56。[证据](../../work/Melodydt/179/control-c-validation.json) | 真实 R256/E/G/S。消费者用真实 S 试验夹具，第二个局控待接。 |

后续由实现端提供同一版本的 Block 顶层、S 容量和端口、正向数据与反向确认端点。Melodydt 负责 A1 控制侧接入，生产 M11/M12 互连和组合时序待联合验收。项目登记 [PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 待合并，项目看板缺配置，生产顶层与审查人待指定。