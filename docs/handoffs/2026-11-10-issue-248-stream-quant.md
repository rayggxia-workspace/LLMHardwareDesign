# Issue248 接续247四轮研究交接

仓库 `rayggxia-workspace/LLMHardwareDesign`，project_id `llm-hardware-design`；[Issue248](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/248)、[PR249](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/249)。负责人/执行身份 YUZE-LU，审查人待指定；规则 rayggxia-project-collab 1.0.0。分支 `task/248-stream-quant-synthesis`，源 commit 以各不可变 run 回执为准，正式完整矩阵 run12@a76a402589ea4a907084246f2e265a8f55de1385。PR最终文档提交以在线head为准。

本次起点 PR243@9d987151ee687322c0ce52d69a0a14f2275bd52b，叠在 peer 分支 `task/242-r-load-bounds`，不得强推他的分支或改他的运行记录。新代码在 `project/experiments/stream_quant_synthesis/`，报告在 `docs/experiments/issue-248-stream-quant-synthesis.md`，结果/失败/源码快照与每文件 SHA 在 `work/YUZE-LU/248/`。

恢复第一步：读取 AGENTS/Skill、Issue/PR最新状态，再执行 `python -B work/YUZE-LU/248/verify.py`；确认当前代码和某次归档快照的关系，再决定新 tag 复跑，不能覆盖旧 root。只有 Slurm 分配节点运行 EDA。本人 remote root 与所有作业号在工作索引，无定时监控，没有停止他人任务。

实际覆盖：独立 A8/A16 矩阵/有限包缓冲 RTL、四路转换 RTL、完整旧 RESULT精确复现、65 case条件SystemC、真实 checkpoint 小样本量化筛查与有限缓存DP穷举。没有完整原生P/DMA/局控或整数全模型、300MHz综合/物理资格、完整静态网/pin合同、DDR PHY或合格能耗。不能声称10token/s或20%算法加速达标。packet/tile粒度尚未统一，A8精度待另做方案，DP估计器对S与通道等待刻画不足。

下一步由接手研究者（待指定）先统一真实服务和数值合同，再独立PR做新有源资源物理验收；同资源对比DP与固定配方。不要直接把研究IR当 #180 ISA 或 #220 完整编译器；不要把102.4GB/s名义DDR当已实装吞吐。

登记：复用 management-hub PR5，pending，未合并不报registered。看板：缺 `config/board.json` 与Projects条目能力，在线字段unverified、同步pending；由项目管理员（待指定）配置并核验Issue248条目、Project ID/Status/Priority后读回。现有本地状态映射不是在线同步证据。

交付状态：待独立审查、未合并、Issue不标done；验证命令和远程终态见PR最终回执，不代审查者批准。
