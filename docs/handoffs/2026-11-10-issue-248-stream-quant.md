# Issue248 接续247四轮研究交接

最新追加：先读[精度与FFN报告](../experiments/issue-248-precision-ffn-exploration.md)，运行 `precision_report.py --root work/YUZE-LU/248/precision`。源2ee939022、正式run19/102009；3包138成员、9策略与上轮精确回归、G4138包/转换4112帧、四FFN两路径有限down数值通过。用户实际INT8工件待确认，目前为浮点checkpoint自生成W8。整行A8不合格；分组A8需要真实组尺度对齐硬件；G需范围旁路/宽位门乘或经验证回退。下一步执行者待指定：先固定数值合同，再接上下文save/reload、局控/搬运与SystemC完整费用；不能凭容量可行就宣称硬件已支持，不能以新数值筛查修改既有7.171451条件吞吐。生产宏/peer任务不改，新有源底座物理验收另PR。

追加评估入口：[DMA/bank/G报告](../experiments/issue-248-dma-bank-g-evaluation.md)，源014b34818，run16/101997正式16场景；先运行 `python -B project/experiments/stream_quant_synthesis/bottleneck_report.py --root work/YUZE-LU/248/bottleneck`。只读包14/15/16共185成员通过；run14严格编译失败、run15的release2早于适配器/M消费而被拒绝，不能用其更快数字。正式context512 7.171451token/s仍是条件SystemC，非原生整机；prefill2有负收益。生产RTL不改。

下一步先统一K256 tile与K16 packet的真实输入消费、fill/输出ACK和上下文合同；G为固定S16/Q5.10，不能截S32低位套用；3P可分摊down部分和但已有8×8上下文不够，需有限SRAM换入/重放方案及真实端口费用。评估桥的gated为整burst固定配置，待两个FIFO/G排空后才能改变；若要逐包模式，必须把模式元数据入队。完整数值与物理资格仍缺。在线状态以PR最新head及回执为准。

仓库 `rayggxia-workspace/LLMHardwareDesign`，project_id `llm-hardware-design`；[Issue248](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/248)、[PR249](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/249)。负责人/执行身份 YUZE-LU，审查人待指定；规则 rayggxia-project-collab 1.0.0。分支 `task/248-stream-quant-synthesis`，源 commit 以各不可变 run 回执为准，正式完整矩阵 run12@a76a402589ea4a907084246f2e265a8f55de1385。PR最终文档提交以在线head为准。

本次起点 PR243@9d987151ee687322c0ce52d69a0a14f2275bd52b，叠在 peer 分支 `task/242-r-load-bounds`，不得强推他的分支或改他的运行记录。新代码在 `project/experiments/stream_quant_synthesis/`，报告在 `docs/experiments/issue-248-stream-quant-synthesis.md`，结果/失败/源码快照与每文件 SHA 在 `work/YUZE-LU/248/`。

恢复第一步：读取 AGENTS/Skill、Issue/PR最新状态，再执行 `python -B work/YUZE-LU/248/verify.py`；确认当前代码和某次归档快照的关系，再决定新 tag 复跑，不能覆盖旧 root。只有 Slurm 分配节点运行 EDA。本人 remote root 与所有作业号在工作索引，无定时监控，没有停止他人任务。

实际覆盖：独立 A8/A16 矩阵/有限包缓冲 RTL、四路转换 RTL、完整旧 RESULT精确复现、65 case条件SystemC、真实 checkpoint 小样本量化筛查与有限缓存DP穷举。没有完整原生P/DMA/局控或整数全模型、300MHz综合/物理资格、完整静态网/pin合同、DDR PHY或合格能耗。不能声称10token/s或20%算法加速达标。packet/tile粒度尚未统一，A8精度待另做方案，DP估计器对S与通道等待刻画不足。

下一步由接手研究者（待指定）先统一真实服务和数值合同，再独立PR做新有源资源物理验收；同资源对比DP与固定配方。不要直接把研究IR当 #180 ISA 或 #220 完整编译器；不要把102.4GB/s名义DDR当已实装吞吐。

登记：复用 management-hub PR5，pending，未合并不报registered。看板：缺 `config/board.json` 与Projects条目能力，在线字段unverified、同步pending；由项目管理员（待指定）配置并核验Issue248条目、Project ID/Status/Priority后读回。现有本地状态映射不是在线同步证据。

交付状态：待独立审查、未合并、Issue不标done；验证命令和远程终态见PR最终回执，不代审查者批准。
