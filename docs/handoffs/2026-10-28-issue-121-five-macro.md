# Issue121 五宏实施接续

2026-10-28 00:20 CST。仓库rayggxia-workspace/LLMHardwareDesign，负责人YUZE-LU；[Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)持续in_progress，[PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)草稿、未合并。分支`task/121-block-v1-twelve-layer`；本记录正文对应代码0a34c7ad8cff2d364517ea24e283890d9d219aa8及随后本次文档/交付提交，以实际远程head读回为准。

## 主线和实际结果

用户已冻结M/V/R/S/T，每种一个基础实现，必须全部得到最终原生M1–M10布局布线及同源独立接收。旧四边界方案/裸M8/混合VS无效为最终边界。阵列、两个产品及一般十二层提取留下一轮。持续目标尚未完成，不能关闭Issue或自合并。

- **M已完成单块原生最终接收，待项目审查**：204精确单网M2补铜，完整GDS所有多边形层差分仅预定新增矩形；205重生全部最终产物/RCX；203四项独立接收全部通过。560×560um，有源115631.264um²，物理专用153645.856um²，275个真实0.8×0.8um M10信号pin。10ns/2fF条件下全部端点setup/hold最小1.737254/0.014780ns；原生及完整FreePDK45 deck均0。三初态最终网表功能通过，严格LEC10558输入/10549输出全匹配、UNSAT/IDENTICAL。大文件在服务器，真实路径/字节/SHA与四项来源回执见[交付入口](../../work/YUZE-LU/121/delivery/M/README.md)。PNG已查看；SVG是实际ODB接点图，XML/边界/计数检查通过。通用层次Lib/M11-M12系统资格仍false。
- **V**：196原样RTL416344检查，函数域逐Q16.16实际RTL6291472检查，两路3级II=1；映射388350单元/543387.726um²，唯一外框1210×1210um。203/92475正运行独立P&R。206同源RTL命令周期测量8243检查通过：八元素函数7拍，reciprocal/rsqrt130/196拍；RMS/L2=197+5ceil(N/8)，Softmax=134+5ceil(N/8)+ceil(N/2)，N256为357/422拍；40选8为328拍。组件II不冒充宏命令II，输入/输出/背压另计，见[命令合同](../BLOCK_V1_COMMANDS.md)。
- **R**：195原样RTL397971检查，240组GDN/SSM与100组四抽头卷积；映射707287单元/145877DFF，1328464.116um²，唯一外框1870×1870um。196/92462在place；最后日志timing-driven resizer可能长时间不刷新，不凭日志静默判断挂起。
- **S**：190/92446已完成global route（实测53:32，阶段峰值约8GiB），正在detailed route。376059单元/131201DFF，1610×1610um；尚无最终接收。标准单元16KiB单1RW，不称SRAM。
- **T**：沿用已接收C叶块，6KiB标准单元结果交接，1120×1120um；既有完整DRC/时序/三初态功能证据未重跑。[交付入口](../../work/YUZE-LU/121/delivery/T/README.md)。

## 服务器与恢复入口

服务器`yuzelu@10.129.166.172`，任务根`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121`。本次任务最多八allocation，pending/未知提交也计数；其他成员作业不计入且不可操作。c96为96CPU，默认6×16独立任务，完成即补位；只按实际依赖/有依据的RAM不足降并发。

旧178/92362于4:31:25自然FAILED，A全deck通过、C检查/接收失败，输出已收回索引；不扩展旧C8修复。空出槽位由203/92475于00:00 CST接上，node23/96CPU。当前五个旧baseline（92045/92046/92047/92062/92386）加190/196/203共八allocation，不能追加第九个。

203不可变队列SHA256`efb011875050301a8084ac2f09f05bc718309e46069e53b0e3cf22e5160cc36a`，source73b50a85395c6195d84fdb31c5faed4a51e77d20，archive15ac4bd9b3356d0f30fdef996054360d115437968185690fdf2f3a32f2b3684f，21项DAG。初始Vroute与M三项接收四个16CPU并发；M功能完成立即补formal；M全deck完成立即生成交付。当前其余S/R/V接收只受各自最终布线依赖限制，已实际记录queue-live，不能冒称六路正在运行。不要改运行中的manifest或重复领取。

194无job且已被195替代，不能再提交。197/201/202失败、198/199只读API失败、200仅诊断通过均保留；204/205/206为196现有allocation内带硬时限、CPU/RAM预检的短step，已全部终态。204误日期目录仅部署预检失败、无EDA/job，保留；不能据该目录再提交。192被父191提前结束终止的经验仍适用，长P&R/完整接收用独立allocation，不能借旧parent生命周期碰运气。

下一步：只读采集190/196/203终态；203自动运行各块同源物理/完整原生+GDS DRC/精确最终网表三初态功能/严格LEC，四项都通过才生成最终索引、pin与PNG。原始失败不覆盖；真实违规按唯一基础版、原外框/接口进行冻结前修复，再重生寄生并重跑全部接收。源码/回执恢复路径见`work/YUZE-LU/121/results/`；本地`.local/issue121/collect_five.py`可采集标准队列，短step用`collect_steps.py`，不将step伪称新allocation。

## 提交和协作未完成项

已执行`python scripts/check_project.py`、相关Python编译、`git diff --check`；硬件结果以原生回执为准。M只完成本块接收，V/R/S未完成，整个五宏任务保持in_progress。管理中心登记PR5未合并为pending；无config/board.json和Projects能力，实际看板unverified/同步pending，管理员和独立审查人待指定。不得描述为登记/看板已完成、不得自审/自合并/关闭。
