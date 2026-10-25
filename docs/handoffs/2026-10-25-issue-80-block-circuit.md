# Issue80 首轮 Block 电路交接

2026-10-25 UTC+08；Liangruizhi。仓库 https://github.com/rayggxia-workspace/LLMHardwareDesign；[Issue80](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/80) / [PR81](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/81)，task/80-block-circuit，D:/Projects/LLMHardwareDesign-block-circuit，base PR77@889ca420181c932598c8e70c500dcdb01156b59c。冻结整理源phase8为8f95edc5271719a594ae0a4c6c3b5b00248f30a1；数值phase5为7f0a562764eb23458b31aaf94379753fceb85939。文档交付commit以PR head/最终上传回执为准；本任务修改独立提交，最终工作区状态另读回，不覆盖其他worktree。

## 已执行

批准计划1—3：六模板电路规格/参考映射、实际PC/取指/宽运算/RMW/CALL/RET/错误完成controller、有限512B单口frame/单ROM、同库存BUS/LOCAL比较和generic/研究库逻辑映射。895×4命令独立数值/协议接收，每配置五状态实际reset；最终同外部事务等待避免时钟相位混淆。16新/69相关检查、管理结构、服务器两包/PC精选字节和8phase123条原Git源码绑定PASS。

局部frame降低本批42.476%—44.029% cycles，研究库logic-only面积增加0.157%，不含共同frame/ROM wrapper。完整512B frame四组逐位一致；两条norm8仍平均5787401 LOCAL cycles，约1.93MB程序，必须在下一阶段优化绝对代价。不是M/V融合、整模型收益、SRAM/ROM宏、STA或最终物理边界验收。

48本人Slurm作业45COMPLETED/3FAILED，原失败/两缺ROM pilot/旧背压结果均保留，没有未完成后台实验。所有实际计算只本人服务器新issue80-block-circuit-20261025目录，旧74/76只读；无新模型/其他机器/软件安装/Phi或成员任务接管。

## 接收入口

[正式报告](../experiments/issue-80-block-circuit.md)、[规格](../BLOCK_CIRCUIT_SPEC_V1.md)、[Blockv2第15节](../BLOCK_PARTITION_V2.md)、[工具及命令](../../project/experiments/block_circuit/README.md)、[执行记录](../../work/Liangruizhi/80/execution.json)、[索引](../../project/experiments/block_circuit/results/issue-80/index.json)。完整逐文件SHA在索引，实际数据/程序/ROM和源码均在授权服务器完整包，原74/76来源也有SHA引用。

- 主存储：/public/home/yuzelu/RuizhiLiang/issue80-block-circuit-20261025/delivery01/full-results.zip，118979927B，SHA256 368c06b6d779ce55d322d9f5b405944e15a21019292b64ab8eba7356d01b6b32，600成员。
- 仓库精选：project/experiments/block_circuit/results/issue-80/selected.zip，708937B，SHA256 c9448a6ebc539713dd4507b29f2726b02245de8f5b988502d52db4f6a1281dcc，271 metadata成员；不是完整数学重跑包。
- PC辅助：D:/Projects/Codex/block-circuit-20261025-01，仅本任务有用源胶囊、公开库来源、轻量验证和接收记录，保留供接续核验。

## 未完成与负责范围

1. 审查/合并：PR81及父PR77尚待独立审查；审查人待指定，Liangruizhi不得自行合并或标done。
2. 协作接入：登记PR5 pending，board.json404、Projects查询缺read:project，条目未核，看板unverified/同步pending；管理员待指定。已有状态映射不代表实际看板已同步。
3. 下一电路轮：受限宽算术/RF/SFU同精度资源对照、真实M partial到完整消费者、完整A/R状态发布与共享仲裁；未执行，任务负责人待下一Issue确认。
4. 物理资格：目标工艺、合法SRAM/ROM容量/端口/mask/latency、PVT/RC/频率/布局/STA与固定/定制层均待验；对接成员55/63既有PR，不自行接管。PR79 adapter为软件in_review，物理绑定仍有缺项。

恢复第一步：认证必须为Liangruizhi/182389313，重读最新AGENTS/Skill与Issue80/PR81/77、成员55/63/PR79和未合并交接，再核索引与来源commit。复用已通过的正式03批，不重复加载模型或覆盖旧输出；新实验使用新Issue/分支/目录，先固定改变哪项电路决策和验收标准。分别报告本地、远端上传、待审查合并及看板真实状态。
