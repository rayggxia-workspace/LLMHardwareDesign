# 共享32KiB原生实施接续

本阶段六页实施PDF已生成，全部237内容单元、8表/45行、两代码块、链接、嵌入字体及六页视觉QA通过。报告固定commit3e8dffdc9dce89cf7f04ff77b2b1cf711dae0039，64个新交付文件Git blob已读回；PDF SHA2630163765d8b0f6a0f97875ecd70749e18d83e4e925d3865da2456549984e32。PDF及QA由本次交付提交保留，原始报告来源保持冻结。本阶段转in_review；未合并、不done。

## 共享32KiB直供与本地1R1W实施（2026-11-10 Asia/Shanghai）

负责人/认证Melodydt，Issue247 / PR243 / task/242-r-load-bounds。两项可选RTL与真实双P包装层已完成本阶段验证，提交独立审查，未合并、不done。稳定测试源a7a36cbb76fa76f6162b666d1f5683cda2a8f7ec；修改前备份task/247-before-shared32-rtl@a8e793e4，候选备份task/247-shared32-native-a7a36cbb，均已读回。

run32/102006在c64/node1/4核1:16 COMPLETED0:0：单元3+4runs、双P四配置各三组、RELEASE/cold/lease、41472主数值+192重填数值及ECHO0生产面积通过。run29/10200340秒COMPLETED0:0：12组默认逐事件/周期精确比较+3组cold。run30/1020045:45 COMPLETED0:0：原评价体系32例端口宽度敏感性；16B共享A约束最高3.640199，prefill ideal3.496459，明确不是原生全图token/s。三路独立审计和完整本地SHA复核通过。

逻辑容量80KiB/物理112KiB/28宏；相对48KiB原配置新增64KiB物理SRAM。宏代理+1.4793928004mm²，池与两P后端标准单元净增0.07256081mm²（同ECHO0实际bank_rw基线），不含P外围和物理实现。完整DDR桥、母控/SoC接入、S32转换及真实模型生成仍未实现。

[实施报告](../experiments/issue-247-shared32-native.md)；证据work/Melodydt/247/shared32-native/evidence-index.json。服务器yuzelu@10.129.166.172，个人/public/home/yuzelu/Melodydt/issue247-area-speed/run26至run32；source/、slurm日志、results/、receipts.tar持久保存，全部终态，无活动作业，无自动监测。失败run26/28/31及修复经过保留。

本地完整快照python scripts/check_project.py通过，仅管理结构；GitHub validate在a7a36cbb仍failure且steps为空，原因未核实，未绕过。登记management-hub PR5 pending；缺board配置/Projects能力，看板unverified/同步pending；正式审查人和管理员待指定。下一步独立审查本阶段RTL/报告，确认A16B端口与实际DMA后续范围；管理员处理CI、登记和看板。此前run24/25研究报告证据包上传阻塞仍保留，本阶段不重传该包。

## 恢复信息

真实远端仓库rayggxia-workspace/LLMHardwareDesign（private），任务分支task/242-r-load-bounds，PR243 base main，未合并。原生产模块默认SHARED_A=0/S_TRUE_RW=0；新pu_p_shared_pair默认两项开启。失败LOAD可能部分更新操作数，需要完整重装。物理频率与全模型执行没有取得资格。

正式集成快照：work/Melodydt/242/r-load-bounds/repo，非Git本地副本；最新生产RTL对应a7a36cbb测试源，报告/分析器改动另按交付commit记录。独立源子集Git worktree位于work/Melodydt/247/shared32-rtl/{integration,pool,rw,tests}，根只写integration，子任务各写独占目录。其160a3de基线是本地source subset身份，不是上游commit；不要以它替代真实实验commit。已有无关及上阶段未上传改动没有被覆盖。

新轻量回执位于work/Melodydt/247/shared32-native，原始回收位于外层work/Melodydt/247/run26至run32/receipts；SHA索引逐run记录。下一位先读取最新PR head和实施报告，检查工作区与是否有新作业，不重跑已通过原件。需要复跑时另建个人run目录，按SHA清单部署；不得在本机或登录节点跑EDA。

实际查看命令：
sacct -j 102006,102003,102004 -X --format=JobID,State,ExitCode,Elapsed,NodeList
tail -n40 /public/home/yuzelu/Melodydt/issue247-area-speed/run32/slurm-102006.log
cat /public/home/yuzelu/Melodydt/issue247-area-speed/run32/results/result.json

成功判据：SlurmCOMPLETED0:0、原始result.passed=true、源输入输出SHA、全部功能和默认精确回归及条件模型控制门一致。任务保持待独立审查；负责人Melodydt，正式审查人/管理员待指定。没有聊天结束后的自动监控。
