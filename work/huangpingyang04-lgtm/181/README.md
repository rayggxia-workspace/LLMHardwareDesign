# Issue181：多私有S／HBM供数验证

- 任务：[Issue #181](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/181)，账号/负责人huangpingyang04-lgtm；2026-11-04，Asia/Shanghai。
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
