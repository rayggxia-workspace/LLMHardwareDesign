# Issue162 continuation checkpoint21

捕获：2026-11-03T01:49:37.376457+08:00；YUZE-LU；[Issue162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162) / [PR163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)，持续in_progress，未合并。

[116项远程源绑定记录/104项原文件、6项实际队列/交付辅助脚本及3项精确Git发布回执](continuation-proof-21/index.json)逐字节SHA核对。大文件保留获授权路径、大小与SHA；运行中日志仅代表捕获字节。此检查点不表示停止工作或验收完成。

## 实际最终原生时序

四个source118原始S候选均完成原始P&R/普通LEC，均有788个实际内部BUF_X32驱动。独立最终RC结果如下；setup/hold计数是违例端点数，绝不是被检查端点总数。

| 原始候选 | setup违例 | hold违例 | setup WNS ns | hold WNS ns | 实际资格 |
|---|---:|---:|---:|---:|---|
| 1180 | 25 | 11 | −0.080825128 | −0.571921945 | 独立物理失败 |
| 1181 | 0 | 0 | +0.017822854 | +0.005294543 | 独立物理通过；四处dout[58]/M10间距失败，仍不合格 |
| 1182 | 1 | 5 | −0.065838449 | −0.599560320 | 独立物理失败 |
| 1183 | 20 | 0 | −0.061375797 | +0.014983403 | 独立物理失败 |

四候选已返回的电气检查cap/slew/fanout违例均为0。1181的其他物理接点/全部实际端点/原生RC覆盖/PG/放置/输入接收器等检查均通过，但不能用这一项通过替代完整四门或组合验收。其余完整GDS DRC仍收尾中，不能据部分空报告判通过。

## 局部M10迭代与真实收尾

source133第一次L形简化只改dout[58]，旧四处违例减少为一处，但实际完整native DRC仍明确失败：bbox(878.8950,419.6700)–(879.0950,421.0700)，位于固定2um pin旁内凹。保留原失败，不放宽M10间距或改pin。

source134改另一侧等长L形：实际完整native DRC报告零违例、命令返回0。原pin坐标(880.095,420.07)um和via9(878.495,424.07)um、全部过孔及M1–M9、所有单元/pin/PG/非目标网和逻辑保留；M10线长仍5.6um。真实DEF规划回归通过，两个错误pin坐标被拒绝。该准备随后因过窄dry-run判断要求文本含“-- do-6_report”而拒绝，实际ORFS输出是唯一flow.sh 6_report final_report。该失败只是准备/发射防护，不是完整硬件资格。

source135精确commit190fae4275d70482036ca062e1d14bbe5bb64085，939文件，归档SHA34eccef3031b36ed15c8a73a63bfcd2456f03af28e1f1d50de34b887a2d60c0f。代码改为严格匹配唯一真实final_report阶段，加入额外前序flow、synth和缺报告三种拒绝对照；全部本地防护检查通过。不删除防护来放行。

1350显式复用1340中已核验的准备文件与零完整native DRC：逐项绑定其失败回执、实际成功DRC命令、文件SHA、原始ODB相同、重放另一L规划/补丁、完整DEF读回及逻辑相同。只复用几何准备，绝不把失败准备记作合格叶。实际do-6_report已启动并正在普通原生LEC；新鲜最终RC、最终ODB/DEF/全网表读回及完整native DRC、788个BUF_X32审计仍待后续完成。原始驱动与全部修改均归S M1–M10，无新增寄存器、协议或周期延迟。

后继12项实际原生/固定PG验收排队：封装、完整实际端点/电气/300MHz、独立完整native+GDS deck、最终全部单元三初态功能、严格全部状态边界LEC、六文件/版图、固定PG与新鲜RC。修复版必须重新完成，不能继承1181旧物理通过。全部独立门仍在，不改SDC/时序例外/目标频率。

## 实际组合及交付入口

1350新真实组合六项与精确native SPEF地电容/上层必要界一项已经追加，等待新S全部原生与固定PG通过；其他20类精确合格叶复用。源码及已有pending/active/completed spec不改写。上层四候选1360–1363及后继24门的发射脚本已准备，实际前置缺失返回ready=false，**尚未发射**；它严格要求新S真实图已无外置S Link8、同一新鲜驱动证明、全部实际原生STA及low/base/high必要电容界为0违例、路由回归源绑定，随后才排实际M11/M12几何/全场景PG/三角点分布RC/300MHz/联合交付。

新单块六文件/版图表收集器也仅准备，实际运行返回ready=false，尚未改写旧单块交付表。它等待真实新PG manifest与boundary-graph，复用其余20类完全相同的合格文件/图片及回执，只接收新S实际全门通过的六文件/原PNG，实例数从实际图重新计数，逐项源绑定；不会用旧335计数代替新图，不把单块通过写成系统通过。最终完整系统收集仍由system_accept要求真实程序三初态、实际ODB/DEF/GDS/PG和low/base/high真实native+upper RC共同通过。

## 资源、发布与协作

八自有节点仍为2/3/4/5/6/7/25/26，c96最多6×16、c64最多4×16动态补位。node2新自有分配95341/source133控制器支持最高256GiB；1350完整收尾及严格LEC预算256GiB，以先前实测约145GiB峰值为依据。保护保持sum(forecast)×1.2+16GiB，不改既有规格。本次捕获附实际sstat；1350仍在消耗CPU收集状态边界，当前增长未超过保护预算。其后RC/门有真实依赖，不能把只有一个ready关键步骤说成满槽。

仅精确停止自有旧335图搜索95098.57给1180实际物理门补位；UID/父任务/进程命令与原spec SHA、停止回执已存。其余旧搜索、完整DRC/功能、父分配及其他任务不动。原始记录全部保留，中断旧搜索不作物理失败。此前node2替换及node26精确补位证据见checkpoint20。

Git传输网络重置后，checkpoint20/source134/source135均经Git Data REST按原始本地commit/tree/blob身份发布，force=false，远程读回一致；三个原始回执随索引。#162/#163已更新并另行读回checkpoint20、source135发布和并行R修正文段。R保留，由并行任务修改；不删除R、不接管该任务、不自行合并PR164/165或本PR。

实际本地检查：check_project、相关Python py_compile、git diff --check、真实DEF另一L规划及错误pin阴性检查、实际唯一final_report计划与三项前序/缺失拒绝检查通过。没有把准备脚本或管理检查当物理验收。

协作规则rayggxia-project-collab1.0.0；登记management-hub PR5 pending；board.json缺失，看板unverified/同步pending、处理人待指定；审查人待指定。负责人YUZE-LU继续完成新S全部门及真实新组合M11/M12/PG/300MHz/程序/六文件、版图和源绑定索引，任务尚未完成。
