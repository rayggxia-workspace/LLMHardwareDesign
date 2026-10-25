# Issue80 首轮电路交付记录

[Issue80](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/80)，负责人 Liangruizhi/182389313；[PR81](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/81)，task/80-block-circuit，D:/Projects/LLMHardwareDesign-block-circuit，base PR77@889ca420181c932598c8e70c500dcdb01156b59c。用户批准计划1—3已执行，交付待审查合并；不标 done、不接管成员55/63、不自行合并。

## 成果和原始证据

[报告](../../../docs/experiments/issue-80-block-circuit.md)、[规格](../../../docs/BLOCK_CIRCUIT_SPEC_V1.md)、[参考映射](../../../docs/BLOCK_CIRCUIT_REFERENCES.md)、[入口与复现](../../../project/experiments/block_circuit/README.md)、[统一索引](../../../project/experiments/block_circuit/results/issue-80/index.json)。正式RTL和工具遵循项目目录，辅助记录留此处。

- execution.json：八 phase 的 commit/源码 SHA/上传 archive SHA、全部48个实际Slurm argv/资源/工作目录，及generic/功能/logic-map五份RTL逐源一致性。
- slurm-final.json：只核本人48作业，45COMPLETED/3FAILED，未中断其他作业；没有后台未完成实验。
- validation.json：16新/69相关轻量测试和管理结构、精选字节、123条原Git源码绑定核验；不代替服务器数学/RTL接收。
- start-audit.json / prepublish-audit.json：开始和交付前本人账号、任务/PR/评论/成员进度。原始2.18MB开始审计保存于完整包execution-controls/start-audit.json，当前文件为可审查摘要并保留原SHA。
- Nangate45来源/许可：nangate45-provenance.json、LICENSE-Nangate45.txt；官方固定版本、原库仅作为非制造研究模型逻辑映射，完整原库留授权服务器包，不引入fakeram/新PDK安装。
- collect.py：仅显式列出的本人Issue80目录归档，排除模型权重/cache/symlink；verify_sources.py核原Git blob，而非工作区近似文件。

全部真实提取/RTL/综合/接收只本人服务器 /public/home/yuzelu/RuizhiLiang/issue80-block-circuit-20261025，lrz-i80-*，旧Issue74/76数据只读。D:/Projects/Codex/block-circuit-20261025-01保留当前任务源码胶囊、轻量检查和字节接收；无新模型/其他机器/软件安装/凭据入库。

## 结果与限制

895×4命令完整frame逐位一致；每配置五状态reset/abort。相同资源/程序下局部frame执行cycles下降44.029%（静默）/42.476%（同外部事务背压），研究库logic-only面积增0.157%，不含共同frame/ROM wrapper。微码norm8仍平均约579万cycles，程序1.93MB，不能声称完整LLM速度或最终PPA。

完整118979927B/600成员留服务器delivery01；精选708937B/271成员入仓库。服务器两包/PC精选逐成员SHA、8phase/123条Git源码绑定均PASS。原编译selector错误、逻辑接收scope注释错误、两缺ROM pilot和早期非匹配背压结果保留，未列最终性能证据。

## 协作状态和恢复

Liangruizhi/182389313实际认证及push已核，成员55仍in_progress/PR58 draft，63为in_review/PR79 ready但物理绑定待资格。PR81基分支是task/76-granite-ports，依赖未合并；不擅自改main或父分支。

登记management-hub PR5仍open/unmerged、默认registry无本project_id，故pending；board.json404，实际Projects查询缺read:project，条目未核，看板unverified/同步pending，由管理员处理（待指定）。审查人待指定。最终上传/CI/Issue读回见PR回执，不能把本地文件或本批数值通过写成正式验收。

恢复第一步：重读最新AGENTS/Skill、Issue80/PR81/父77及成员55/63/PR79；先接收上述索引、再核最新PR head，避免重复跑完毕的895×4。下一任务为受限宽算术/SFU/RF专用化、真实M的完整消费者、合法宏/PVT/布局/STA；完整M/A/R与全模型质量仍未完成。
