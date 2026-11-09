# Issue247 容量与读写并发组合比较接续

2026-11-09 Asia/Shanghai；负责人 Melodydt；规则 rayggxia-project-collab 1.0.0。[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。

用户要求研究两个P各48/64KiB＋读写并发，以及两个P各16KiB＋读写并发＋8组部分和。SRAM扩容仍只做模型研究，不实装生产RTL。复用已有Issue247联合消融范围，当前in_progress；前轮五方向交付保留。

仓库rayggxia-workspace/LLMHardwareDesign；分支task/242-r-load-bounds；接续基线a7a80de349e33209eca3fef09167614e66511afc。实际本地源快照D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo是非Git目录；使用本人GitHub tree/commit/ref租约，不能称为本地pull或HEAD。修改前259个PR文件blob均与本地一致，无覆盖旧变更。子任务在work/Melodydt/247/compare-model、compare-audit、compare-contract独立目录开发，仅root整合正式源。

计划新正式代码project/experiments/sram_port_compare；旧246/247功能源码和输入SHA保持。服务器只在yuzelu@10.129.166.172的/public/home/yuzelu/Melodydt/issue247-area-speed/run04新目录，4核Slurm，作业名mdt-sram-rw。当前尚未提交，作业号、源码commit、实际节点/日志/结果与输出SHA均待取得真实回执后填写；此前101631/101635/101638已结束，不重复提交。

验收先回归246容量和247读写并发的旧完整结果，再做容量×端口及两路线的W8/context512、W16、长context/prefill对照、全A驻留与多contexts重叠、切换和端口占用敏感性。独立核对容量、所有P读/写服务、U端口/16KiB不变、ACK与流量/源锁。只能报告抽象端口代价，不等同于改变整个芯片频率或取得物理资格。

恢复第一步：确认本人身份与最新Issue/PR head、当前源/未提交文件；本地运行python scripts/check_project.py和旧work/Melodydt/247/verify.py。新runner、独立audit及前置完整结果SHA准备完毕后冻结源commit，再提交新作业并立即给启动回执。实际实施/独立审查负责人待指定。

登记management-hub PR5 pending，缺board.json/Projects条目能力，看板unverified/同步pending，管理员待指定。CI前轮42594203013失败、无steps且日志404，不能报告通过；不改工作流绕过。没有配置自动监测，任务未验收合并不done。
