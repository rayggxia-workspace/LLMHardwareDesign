# Issue181：多私有S／HBM供数验证

## 当前续作：分组仲裁与多S搬运RTL

- 同一[PR182](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/182)已增加实际RTL描述符/事务槽、组间/组内轮询、LOAD/STORE、响应ID与完成处理，C++只提供主机/外存模型及oracle。
- [RTL合同](../../../docs/HBM_GROUP_DMA.md)、[服务器报告](../../../docs/experiments/issue-181-hbm-rtl-results.md)、[独立检查](RTL_INDEPENDENT_CHECK.json)。
- 服务器最终97178（c64/node1、4CPU、UNLIMITED、COMPLETED0:0）；38正向场景、228个RTL拒绝检查、1个坏payload负控制、238矩阵/15232数值、6912294运行检查通过；4S/16S核心完整Yosys通用综合及check-assert通过。
- 输入commit `a216087e4e1b60b46f7ae35932baf8b4a6e4fdb6`。新证据在`evidence/rtl-release`，原件50项/18322759字节，完整综合日志保存在原压缩包和服务器，Git保留压缩原件及轻量文件。`check_rtl_evidence.py`核验包内全部原字节。
- 首次97176的Werror夹具编译失败及97177的中间成功证据分别保留`evidence/rtl01-failed`、`evidence/rtl02`。本任务作业均自然结束，不留运行任务。
- 当前接口是带ID原生事务口；不是完整AXI/HBM控制器，不授予物理/时序/扇出资格。[当前交接](../../../docs/handoffs/2026-11-04-issue-181-rtl-review.md)。

```powershell
python -X utf8 -B project/experiments/hbm_feed/check_rtl_evidence.py
python -X utf8 -B project/experiments/hbm_feed/summarize_rtl.py
```

## 第一阶段历史证据

- 任务：[Issue #181](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/181)，账号/负责人huangpingyang04-lgtm；2026-11-04，Asia/Shanghai。
- 成果：[PR #182](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/182)，已提交独立审查，未合并。
- 范围：用户确认架构与仿真验证，授权服务器运行、结果汇总及PR。分支`task/181-multi-s-hbm`从main `4b1df2c7`独立建立；不接管#162/#177及其他成员任务。
- [中文结果报告](../../../docs/experiments/issue-181-hbm-results.md)、[模型/复现说明](../../../project/experiments/hbm_feed/README.md)、[35组指标](metrics.csv)。
- 最终服务器源commit `48c26d1e19e80327653fa75d4f4f9bc3646988ed`；Slurm97162，c64/node1，4CPU，UNLIMITED，COMPLETED0:0。
- 最终35正例、5预期拒绝负控制、230矩阵/14720数值结果、3362870运行检查通过；原S/feeder/M逐字节未改。实际M输出经过S再STORE，不用oracle替换。
- [独立核验](INDEPENDENT_CHECK.json)、[原件SHA与远程大文件索引](evidence/release/reception-index.json)、[实收](evidence/release/LOCAL_RECEPTION.json)、[原始结果](evidence/release/result/results.json)、[Slurm终态](evidence/release/scheduler.txt)。47份原件210428字节实收；原始输入包和二进制留服务器。
- `evidence/preliminary`为初轮97159，尚无M结果回写；`evidence/final`为中轮97160，已闭环但保留4个排版警告；`evidence/release`为最终97162，Werror零警告且数值/性能与97160一致。历史目录不覆盖。
- `REPORT_MANIFEST.json`绑定最终结果输入、生成脚本、报告和CSV SHA；证据按原字节入Git。

核验：

```powershell
python -X utf8 -B project/experiments/hbm_feed/check_evidence.py
python -X utf8 -B project/experiments/hbm_feed/summarize.py
python -X utf8 -B scripts/check_project.py
```

原型含真实双时钟FIFO和S transport RTL；组仲裁、外存时序和回写编排仍为C++夹具。没有完整AXI桥、真实HBM控制器/PHY/封装、JEDEC合规、扇出/面积或500/300MHz物理资格。后续控制RTL需另行集成与验收。

协作规则rayggxia-project-collab1.0.0；项目登记management-hubPR5已读回open/unmerged，pending。本仓库缺config/board.json，当前连接器无Projects条目/字段工具，条目unverified/同步pending；[持久交接](../../../docs/handoffs/2026-11-04-issue-181-review.md)。PR供独立审查，不自行合并，Issue保持in_review。
