# Issue #42：固定底座两控制锥的算法提炼

负责人 huangpingyang04-lgtm；2026-10-23（中国标准时间）。[任务](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/42)，分支 `task/42-control-cone-closure`，PR 链接以 Issue 的关联记录为准。

结果：原生实验已实现同一两门底座、M1–M10 固定，仅 M11/M12 与接入通孔改变的两个组合控制片段。此次把冻结比较、全局导体连通及组合逻辑求值提炼成参数化程序；原生 EDA/SAT 证据复用，不重跑旧实验或新增功能。

入口：[代码与使用说明](../../project/experiments/frozen_control_cones/README.zh-CN.md)、[算法/参数](../../project/experiments/frozen_control_cones/ALGORITHM.zh-CN.md)、[原证据索引](../../project/experiments/frozen_control_cones/evidence.json)、[本次验证回执](../../project/experiments/frozen_control_cones/validation.json)。

- openTPU 的 b_req 输出为 0001，llaccel do_push 为 0010（输入00/01/10/11）；各四个组合与原生结果一致。
- 原生主实验 89888 和闭环复核 89890 通过。89889 在最终未绑定源码路径处失败，前序保存 ODB 读回和 SAT 已完成；主机只读复核后以保存证据闭环，不能把失败作业算成功。
- 本次 Slurm 89894：COMPLETED 0:0，单核13秒；15项测试、两案例重放、60项证据哈希和管理结构检查通过。89892 是增强前13项版本；89893 因新脚本换行转义语法错误失败，修正后89894重新执行。失败日志保留，不计为验证通过。
- 改名、输入顺序、坐标平移通过；实际故障导出及模型、资源、供电变异被拒绝。对照的是这两个小组合锥，不是完整核心、FIFO状态或正式 Block。
- 仅标量金属间距/网格重放；原始 cut/OBS/track/PG 通过保存证据关联。假设新增层，未做完整 DRC/LVS/RC/STA，也没有证明自动详细 router 成功。

成果目录：`/public/home/yuzelu/PingyangHuang/pending/control-cone-algorithm-pr-20261023T073506806184Z`。旧物理结果保持在 `/public/home/yuzelu/PingyangHuang/pending/paired-function-physical-20261023T062933908806Z`。本次只在新任务目录写入代码、审查快照、配置、样本副本、测试临时文件和日志。PR 不含 ODB、完整日志、库或工具。

登记 pending：管理中心 main 未含此项目，已有登记 PR #5 尚未合并；本次只读核对，不向管理中心上传。看板 unverified、同步 pending：业务仓库无 config/board.json，当前工具没有 Projects 字段查询/更新能力；处理人待指定。审查人待指定，未合并前任务保持 in_review，不标 done。

下一步：先评审和归档此方法，再增加一个有状态的小功能；新增主动资源形成新底座候选，两个目标在同一候选上重验。
