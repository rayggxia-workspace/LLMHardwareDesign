# Issue66 实验与交付记录

负责人Liangruizhi；[Issue66](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/66)/[PR67](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/67)。分支task/66-scale-state，根工作树D:/Projects/LLMHardwareDesign-scale-state；base PR65@ec3008c665709fa3126d55719ad084d33af44428。完整[报告](../../../docs/experiments/issue-66-scale-state.md)/[交接](../../../docs/handoffs/2026-10-24-issue-66-scale-state.md)/[SHA索引](../../../project/experiments/scale_state/results/issue-66/index.json)。

## 实际记录

- startup.json记录身份/Issue/PR/成员与资源接续；所有远端操作使用Liangruizhi/182389313/指定邮箱，服务器用户名不代替GitHub身份。
- jobs.json是实际sacct -X读回：90059–90082共24个lrz-i66-*作业均COMPLETED0:0，node13/c96。capture24CPU，其他2CPU；科学双轮并行、各自输出，日志/源码/数据互不覆盖。未中断89448，Phi封存，无新权重下载。
- phase*-binding.json为冻结commit/逐文件SHA（成功运行是phase1b/2b及3–15；phase1/2仅准备失败，未运行）；phase*-staging.json记录源码ZIP SHA。全部15阶段/21份源文件已与原Git blob及ZIP capsule核对，不拿最终文档HEAD冒充原实验源码。*-submit.json是完整实际sbatch/argv/资源/输出命令；runner.py及launch_*.py保存调度实现，仅在核现有作业/新输出后恢复，不盲重跑旧脚本。
- returned/是原manifest、小型结构化metrics、独立receiver及归档receipt原文；较大的state-results.json原文保留在精选ZIP/完整ZIP，正式results/issue-66/state-metrics.json给出省略逐步commit列表的逐条件视图（不改原误差/范围/成本，附原SHA和first/last commit）；字节数/数据SHA以各manifest为准。norm01/02旧成本留存；norm03/04另冻结补源重读/fresh A8账本，全部NPZ两版一致。长48条件实际24×256+24×1，其中独立数学全重放3个256见证及2个coupled；未把全48称第二内核重放。
- selected-intake.json验证精选外SHA/132个索引成员、15源capsule/21Git源；selected-review-actual.json是本机NumPy2.5.4从实际编码数据独立重放2个32步R+2个完整H消费者，而非另跑完整模型。selected-review-boundary.json是分开的合成整数/commit负例。不能把小精选接收当所有原始capture/整数norm质量。
- preparation-failure.json及原准备/连接失败记录保留：Windows CRLF和建连超时发生于数值作业前，修复UTF8 bytes/新phase/仅建连失败重试。数值Sat_state属于定义的输出，代码执行成功仍不能称范围合格。
- local-newline-normalization.json明确本机日志/接收JSON的CRLF→LF存储转换及原始字节SHA；原件保留D盘，不改数字。validation.json及对应日志记录最终管理结构、已有业务、新参考与接收边界测试实际结果；未运行目标RTL/EDA/PPA，不写成通过。

## 大文件位置

本人授权服务器/public/home/yuzelu/RuizhiLiang/issue66-scale-state-20261024。full-results01.zip为5,207,960,397B/SHA cf07db65cb9207bd1aea0efd50b2338fa535edee6f2cae760a116df912dfb548，位于该目录delivery01/；不下载到C盘/不提交仓库。精选19,581,351B/SHA 36791d8b553490c914fc720df31abc179bb1442c2ca0c5a93645c139ab6bca0b在正式results/issue-66。完整权重未入任一ZIP；实际坏码NPZ保留其独立接收路径（归档含索引/接收JSON，未把所有坏码复制入ZIP）。

## 协作回执

rayggxia-project-collab1.0.0；project_id=llm-hardware-design。源码/报告/索引/精选及个人进度经任务分支PR交付，待指定审查人/合并，Issue in_review而非done；最终远端head/CI以PR读回为准。登记management-hub PR5仍pending；无board.json/Projects能力，看板unverified、同步pending，管理员待指定。未代他人审查/合并或改Issue55/63。

下一步先定义R范围guard/rescale epoch及V有限调度合同，再建立相同精度/库存/辅助流量的V/R/S服务配对。报告不承诺整图加速；仍有FP桥、真实端口/时序/物理资格未验证。所有恢复先读最新AGENTS/Skill/Issue/PR/成员/交接，核现有作业及结果SHA，已完成作业不重发。
