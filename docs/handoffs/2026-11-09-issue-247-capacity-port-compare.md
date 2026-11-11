# Issue247 容量与读写并发组合比较接续

2026-11-09 Asia/Shanghai；负责人 Melodydt；规则 rayggxia-project-collab 1.0.0。[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。

用户要求研究两个P各48/64KiB＋读写并发，以及两个P各16KiB＋读写并发＋8组部分和。两轮研究已完成、交付待独立审查；在线状态以Issue回执为准，不done。SRAM扩容仍只做模型研究，不实装生产RTL。复用已有Issue247联合消融范围，前轮五方向交付保留。

仓库rayggxia-workspace/LLMHardwareDesign；分支task/242-r-load-bounds；接续基线a7a80de349e33209eca3fef09167614e66511afc。实际本地源快照D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo是非Git目录；使用本人GitHub tree/commit/ref租约，不能称为本地pull或HEAD。修改前259个PR文件blob均与本地一致，无覆盖旧变更。子任务在work/Melodydt/247/compare-model、compare-audit、compare-contract独立目录开发，仅root整合正式源。

正式代码project/experiments/sram_port_compare；旧246/247功能源码和输入SHA保持。run04源c597a7d0f7e5ee03100cea5d4ac65dd22cb93a11、作业101665/mdt-sram-rw、c64/node1/4核/UNLIMITED，8分02秒COMPLETED0:0；服务器yuzelu@10.129.166.172的/public/home/yuzelu/Melodydt/issue247-area-speed/run04，代码source/，启动命令sbatch --parsable job.sh，日志slurm-101665.log、结果results/result.json。完整结果SHA966729e962ecde76f755a9da873f3fb7ac566e4dd454f45e7d4b6f8f76c73cce，149回收输出SHA核对；57完整trace＋6尾块＋4非法CLI通过，22轻量证据/44功能源一致性通过。本地证据work/Melodydt/247/compare，原始回收在外层work/Melodydt/247/run04/receipts。

run05已完成隔离policy对照：实际48/64KiB驻留保持，仅将预取判定固定16KiB；源49b3938ce8b55734520c56a79a7d5d7933af9cdc，101672/mdt-sram-policy，c64/node1/4核/UNLIMITED，3分58秒COMPLETED0:0。服务器同根run05，代码source/，实际在run05执行sbatch --parsable job.sh，日志slurm-101672.log，结果results/result.json；完整结果SHA4dcb0f01357e2f71fcf9f90deeab1d1dd50101b3d928b3e9866473c91c133777。30完整trace、先12默认回放、2非法CLI及每case6负例通过，81回收SHA及23轻量证据/49功能源一致性通过。新policy文件不改run04已测源，真实U/流量/工作保持。

源码提交均已上传task/242-r-load-bounds，最终文档/证据head以PR读回为准；本地非Git目录不称未提交Git变更。首轮证据在work/Melodydt/247/compare，追加在其policy子目录，完整回收在外层work/Melodydt/247/run04、run05/receipts。当前没有活动作业，不重复提交；没有聊天结束后的自动监测。

```bash
squeue -j 101665,101672
sacct -j 101665,101672 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList -X
tail -n 40 /public/home/yuzelu/Melodydt/issue247-area-speed/run05/slurm-101672.log
cat /public/home/yuzelu/Melodydt/issue247-area-speed/run05/results/result.json
```

最终W8/context512 A48/A64为3.541567/3.543921，B为3.496169，增量1.30%/1.37%；默认容量联动预取的A慢约2.4%，不能省略调度干预。prefill2 A对B+20.84/+23.01%；仅大容量端口增加到1.25拍时A64低于B1拍。两P＋U的S总量B48KiB、A48/64为112/144KiB，B另加1344B部分和数据寄存器与控制，物理面积未知。[报告](../experiments/issue-247-capacity-port-compare.md)/[取舍](../decisions/issue-247-capacity-port-routes.md)。

验收先回归246容量和247读写并发的旧完整结果，再做容量×端口及两路线的W8/context512、W16、长context/prefill对照、全A驻留与多contexts重叠、切换和端口占用敏感性。独立核对容量、所有P读/写服务、U端口/16KiB不变、ACK与流量/源锁。只能报告抽象端口代价，不等同于改变整个芯片频率或取得物理资格。

恢复第一步：确认本人身份、最新规则与Issue/PR head及评论；本地运行python scripts/check_project.py、旧work/Melodydt/247/verify.py、work/Melodydt/247/compare/verify.py及其policy/verify.py，核对同源/Job/完整结果SHA。然后独立审查研究证据；下一项工程先验证共有的读写并发宏/前端/同址冲突与生命周期，校准代价后再决定容量或上下文实现。真实宏、96位上下文RTL、DDR/权重/KV和生成质量未验收；实施/独立审查负责人待指定。

登记management-hub PR5 pending，缺board.json/Projects条目能力，看板unverified/同步pending，管理员待指定。CI前轮42594203013失败、无steps且日志404，不能报告通过；不改工作流绕过。没有配置自动监测，任务未验收合并不done。
