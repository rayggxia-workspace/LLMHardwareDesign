# 主线二首切片可执行交接

仓库：https://github.com/rayggxia-workspace/LLMHardwareDesign

Issue：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151

PR：https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152

## 2026-11-01T20:02:36+08:00：主线二固定DOT8/可变数据岛壳RTL首切片

- Issue151 / PR152，Melodydt；task/151-six-connection-study，base task/143-seven-block-v2；输入bfe62ad179af72aef591622aa5c7a000f5d8b681，输出commit/CI/远端上传以本轮PR回执为准。
- 新增block_w1_mst_top及block_w1_mother_rom，真实8×128入口/56B canonical padding/8实际S写ACK后start；slot2 INPUT_CHECK替代literal S_INIT；唯一S helper、M状态/结果分流、T输出/RELEASE和frame/DONE/reset/abort。固定S8 K8/N8/op/地址/factor1，无runtime程序/shape配置；七叶与旧P2不变。
- 实际本地ModelSim2020.4沙箱外运行：regression-r01旧P2 19CASE；w1-r01声明顺序compile2失败保留；w1-r02 28CASE/4422周期通过后独立review提出DONE计数门；最终w1-r03 TB178318...强化公开DONE+abort同拍exactly-once与frame busy，28CASE/4422周期通过。source/input/tool/config/log SHA在w1-execution-index，完整证据在w1-rtl-evidence。
- 正常frame16S请求/ACK（入口8+RUN8）、7M/应答、T4take/release按每帧检查；全局abort/reset有意丢弃的pending事务差额逐项说明，不能写成全程无条件守恒。28是检查标记，不是28完整任务。无N/E/G/R功能资格或物理/模型推理新增通过。
- 独立源码与根执行证据审阅另记，不代替外部PR审查。完整W1/general endpoints/跨岛stored ACK、NUM/MEM/六profile/P2整体退出仍未完成，主线三及后续未开始。
- 隔离API包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/w1-bfe62ad/integrated；非完整Git clone，无HEAD/暂存；其他会话/旧包保留。源码快照/仿真二进制只在包外本地run目录，正式仅相关源/日志/索引；早期不同的W1源码作为小型失败/先前输入附件保留。
- 后续服务器仿真授权保留，已读REMOTE_RULES；本轮使用现有本地工具，无服务器目录/上传/作业，无安装/PATH/license/凭据查看，无ref-project修改/扫描或接管#143/#153。
- 部分交付in_review，PR未合并，审查人待指定，不done。登记PR5 pending，看板无board.json及条目工具而unverified/同步pending，处理人待指定；最终在线事实见PR读回。
- 接续第一步：本人连接核Issue151/PR152 head/base/评论/CI，核w1-index及final r03 source SHA，再依据未完成门决定扩展主线二或按用户安排进入主线三；不把有限DOT8当完整大Block或物理冻结。

相对输入的未提交/上传白名单在包外upload-manifest.local.json；无Git暂存区。四个真实运行在本地runs/，正式证据索引固定SHA；服务器没有对应本轮结果目录或作业号。恢复先重读Skill和在线回执，按ARCHITECTURE核原证据/源，再用全新目录重跑，未决实现与审查处理人待指定。
