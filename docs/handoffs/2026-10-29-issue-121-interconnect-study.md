# Issue121侧线互联实验交接

仓库：rayggxia-workspace/LLMHardwareDesign；Issue：[121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)；主线PR：[122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)。账号YUZE-LU；2026-10-29 14:45 CST。

独立工作树`D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-121-interconnect-study`，分支`task/121-interconnect-study`，起点b451039b3d6083a9dcc8e4db7b46fa4440ed87ac。闭合实验代码/证据基准e3b129e2b8a55c70b5be9e5843ad9c5b172b0cb5；其后仅补交接、进度与发布回执。原运行源分别为7383a79/run907及b591fd8/run908，不转移新源码的物理资格。

## 已完成

- [报告](../reports/2026-10-29-block-v1-interconnect-study.md)：两组完整真实宏、每组130根线，36个长度/RC案例及12个实际接点距离/强缓冲案例。48项测量完整性门均通过，MT为0/24项、TS为19/24项在声明条件通过。
- T→S实际最长1688µm，8→8→2候选在high和section均通过，section最小链路setup+0.308616ns。M→T长线的电气负载可分段处理，但ready组合时序未闭合；568µm/base直连最差−0.159452ns，实际距离section加中继仍−0.313493ns。
- 原生连接、ground/coupling C和R逐条指纹反查；恢复原清单的M142/T190/S143个保护器件到实验副本，无警告豁免。原生产Verilog/SPEF/SDC九文件和三个physical回执末次SHA保持。
- 93222/93236在node26自然COMPLETED/0:0；6×16互斥CPU队列、即时补位、Issue121共享最多8allocation保持。仅停止经身份核验且模型已确认无效的本侧线93214；其他作业未取消。
- 七项本地控制、项目结构检查、48项源SHA/原生图/原始全局与逐线时序一致性核验通过。数值截面三档网格、域、能量/电荷、解析控制及错误面距反例通过。

## 主线恢复入口

先读报告与`work/YUZE-LU/121/interconnect-study-20261029/README.md`。当前不需重投这48项或重新运行已验收M/S/T生产P&R。

主线下一项应明确M→T的控制路径预算：用真实控制器的输入到达、外部输出延迟和寄存器时序检查`write_index→write_ready→rsp_ready→cmd_ready/busy`；若预算不足，再比较正确处理在途数据的弹性缓冲/信用或局部寄存控制。不要直接插ready寄存器、加false path或无依据改I/O约束。

驱动候选应预先放置在固定M1–M10底座内或固定中继小宏中，随后重做所影响宏的完整同源验收；需要验证8µm局部线假设、合法位置/供电/M10接入、全局setup/hold。M11/M12只定制连线，不能临时增加有源器件。尚未完成这些P&R，不将候选写成最终积木。

完整共同CTS、130线同时布通、新层真实三维提取/串扰、制造、广播/多跳、全协议控制器及整模型吞吐未验收。原有单宏验收对应其原边界条件，本实验不自动授予组合资格。保持一套基础宏，不增加阵列/产品/裕量版任务。

## 源码与发布恢复

本地Git HTTPS两次连接重置；采用YUZE-LU GitHub连接器发布与最终本地提交**相同Git树**的独立快照供审查。线上快照和本地分支的commit身份不同，不强推也不盲目覆盖。线上PR提交回执给出最终snapshot SHA和tree等值读回；侧线PR目标应为主线feature分支，不能关闭Issue121或替换PR122。

原实验历史Git bundle：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/interconnect-study-history-20261029-e3b129e/source-history.bundle`，287918字节，SHA256 `dc8acf4aaa17ffca4901748c1e6cd4f1972a3a595a08dfc0afeb9e5ef2fe2e69`。它要求已有b451039b3d6083a9dcc8e4db7b46fa4440ed87ac，恢复出e3b129e及所有原运行源commit；`source-history.json`保存同份索引。恢复应另建分支，不在主线工作树reset。

大数据库/原始回执仍在获授权服务器run901–908目录；仓库保留原SHA索引及代表原始小报告，完整捕获可用报告中的`interconnect_collect.py`命令重新获得。已保留901–906的失败及拒收原因，不视为硬件失败或删除失败记录。

协作：规则rayggxia-project-collab1.0.0；project_id=llm-hardware-design。Issue121仍是主线in_progress、PR122为其原状态；本侧线只交有限实验审查，不代替独立审查/合并。审查人待指定；登记pending（已有management-hub PR5待合并），缺config/board.json，看板unverified/同步pending，管理员待指定。未向主线聊天发送消息。
