# Issue121 当前运行与继续入口

2026-10-27 18:03 CST。目标仍为批准的完整P0–P6，不是只交单个探针。仓库rayggxia-workspace/LLMHardwareDesign，Issue121、草稿PR122，分支task/121-block-v1-twelve-layer，172生产源码5614eff28472bf2bf54329c4f40b59c200ae7dfe。全部有源资源/位置/PG/CTS及M1–M10先冻结，后续两产品只改变M11/M12/via10/via11。当前没有冻结宏。

## 恢复先读实际作业

明确的本任务活跃allocation为92045/92046/92047（旧057）、92062（067完整映射功能）、92333（167 C8新原生最终输出）、92341（172完整C8严格LEC重验）；18:00六个均RUNNING，实际队列与部署SHA见work/YUZE-LU/121/run172-deployment.json及stage168-manifest.json。不得只按manifest中的旧PENDING判断实际状态，不重复sbatch；预算基础6/最多8含PENDING与提交不明。其他成员不计入且不操作；不因耗时取消旧任务。

根目录/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121。167位于block-v1-20261027-167，group native-c8-finish-group，node20/16CPU，A/C各8CPU；172位于block-v1-20261027-172，group native-c8-tie-lec-group，node21/4CPU，A/C各2CPU，200GiB/路加20%内存预检。worker保持各自日志/receipt，peer失败互不取消，独立目录。第一步用squeue/sacct和实际receipt读取终态；两路都成功前不启动完整接收消费者。新诊断/导出等串行代码按1CPU/路，不能仅增加单任务NUM_CORES凑96核。

## 已确认与未完成

161实际T6K A/C完整物理18门及三初态真实最终存储单元功能通过；168同源供电修正/完整时序Verilog交付原生读回通过；169固定PR128工具完整原生占用导出通过。交接inventory为work/YUZE-LU/121/t6k-qa127-handoff-168.json，两路30角色。完整SPEF flat必须使用candidate-timing.v或实际ODB；旧6_final.v过滤189保护单元而只保留作原流程来源。169原始source-occupancy.tsv与完整receipt在服务器，主线没有把导出成功写成独立覆盖通过。#127继续负责独立模型/覆盖；其新结果按已发布固定源码/报告核验，不能仅靠聊天消息宣布验收。

165实际有限C8几何11门通过，但只是upper诊断子集。162旧完整原生49/37违规、134/141严格LEC拒绝均保留。170图诊断确认前后已用输入bit/顶层输出均有驱动，原未匹配数恰等于1004/1032个tie。171实际0/1两种常量对照均通过：原生改名tie每侧产生1个未匹配PI，按真实库常量函数作可逆Boolean编码后严格4输入/4输出全匹配、UNSAT/IDENTICAL通过；错误tie极性和DFF时钟仍明确SAT拒绝。172将该严格编码用于134封存完整图，保留真实物理tie、源失败及native_formal.inspect全部门，当前未终态；即便通过也只是旧同源完整图形式资格，不能直接资格新的167物理源。

若167和172成功：下一步把常量编码以实际171/172控制与完整来源绑定接入新的C8正式物理/最终功能接收，重新读167最终源，严格全状态/接口正向LEC、全部STA/电气/RC、PG/驱动/连接、完整独立GDS/DRC及四profile+C8/S16K/T6K/glue精确最终功能仍须全部通过。不能改旧回执或只沿用原route DRC0。

当前宏Lib仍有独立min/max边界问题。已读[固定OpenSTA源码](https://github.com/The-OpenROAD-Project/OpenSTA/blob/bc7af6f02679074eaf43657488ca117c05f98eed/search/MakeTimingModel.cc#L76)，构造选择max；原生单套输出表不得未经min/hold实测就当作同时准确的min/max模型。#127正在做独立短/长路径反例及有效工作域，主线保持168为候选。可考虑经明确控制的分离min/max导出或可证明安全包络；本轮尚未实施，不通过放宽误差或吞掉warning来冻结。

一般多网分布耦合十二层提取/原生拼接和窗口归属、全部glue物理、共同底座、有源/原生层差分固定、仅新增层两产品、敏感性/参数库和独立审查合并仍未完成。python scripts/check_project.py、变动Python py_compile、git diff --check及各处声明的真实控制均通过；它们不替代上述业务验收。

规则rayggxia-project-collab1.0.0，实际账号YUZE-LU。管理中心PR5未合并为pending；无board.json及Projects工具，实际看板unverified/同步pending，管理员/审查人待指定。Issue保持in_progress，PR未合并；没有自行标done、关闭或合并。持续工作的入口为本文件、Issue121实际在线快照和当前Slurm终态。
