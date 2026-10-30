# 五宏当前继续入口：V原生清零，最终接收仍待完成

最新补充见[CHECKPOINT-775](CHECKPOINT-775.md)：766已自然PASS，767进入独立验收。

Refs #121 / PR #122。M/V/R/S/T每种一个基础实现；300MHz、M1–M10固定，真实M10接点留给未来M11/M12。S16KiB、T6KiB均为标准单元存储。无裕量版、阵列或产品扩展。

2026-10-31 05:12 CST：V763真实31网联合已原生全片DRC 0项/0新增，765封存15原始/7稳定/355归档源Git；过孔以显式block VIAS随DEF交付，切孔/另一层pad不变，M3包围形状为原金属内的超集，所有562494普通NETS与预期路径/RECT精确核对。756六项OpenROAD均正常return0，但旧解码器不识别新名称，后处理自然FAILED（758：49原始/30稳定，六实际命令重叠97.159秒）；760仅对这六份既有数据库只读复核，全部31→30/新增0 PASS（761：43原始/30稳定/353源Git），未重跑EDA、未改写失败。766/93998/node16已启动该0项库的fresh RCX/finalreport，767全部新最终门及768全部端口/有限RC已stage；769仅跟进这三个V队列，PID1566692、配置SHA c4e5513d9992f20523d71d48cb9e51f8c37ceb6af3a087ef2e7e635d08137cfa，原634/R保持，实际四个Issue121 allocation。R404原GRT extra45，05:10原PID1987219 CPU增长。原生0项不等于最终接收；物理信号几何连通、fresh覆盖/时序电气、完整未改GDS、功能/LEC、六文件/完整已查看几何/接口均须同源完成，V仍accepted=false。M/S/T保持、五宏最终未齐。

最好的实际修复源：服务器 `block-v1-20261031-763/tasks/revision300-v-zero31-compose`，helper/source commit `b5ff644262e92b0255323810071c7c58ef4cbec7`，archive SHA `ae532472861c158d8ba6a4efb394c376b7cf0f6ef7fe282b1ad008ed8d9562b6`。实际原生报告为空。`v-joint31-combined-765/index.json`给出当前ODB/DEF实际SHA/大小，`verification.json`核对355归档源码Git blob和receipt输入/7稳定输出。

这是真正在705共同原31项源上组合31个不同网络：此前754的29网与两份760通过候选。运行时重核19份独立/审计receipt。两处M3过孔以block VIAS导出，原切孔和另一层金属pad精确相同，目标金属pad是原pad超集并完全在既有同网金属并集内；没有排除native规则，没有编辑PDK规则。全部实际路径/RECT/普通NETS精确核对；此证据不代替完整GDS、连通或时序接收。

766 source `9930912305d9e183c264c7999b947452fd0849b2`、archive SHA `5b4fcf1ed52158409b0569300530f929c72f5c38669e5aa73019d7bdea9853e1`，只继承629的RTL/单元/布局/CTS与实际修复几何，运行普通最终报告/重新RCX。必须证明全部普通NET记录和NETS以外的DEF（含VIAS/单元/pin/PG）与763完全相同，并重查native0。不得声称又做了综合/布局/详细布线。

767/768 source `91389d8a09b50b8ccae99069644f7dd39d367ca1`、archive SHA `a85eee762b92751933fa61b036e17d55f317b6eb7d078d98c3207d3b9fc19024`；共享新最终源，重跑物理、未改完整GDS deck、最终三初态功能、严格LEC、六文件/完整几何和全部端口/有限RC。`admission-769/deployment.json`记录仅这三队列的配置/实际源核验和PID；`live-771.json`记录769和原634均alive/watching及Issue121实际四allocation，其他Issue未计入本任务。不要重复部署或因日志安静取消EDA。

还必须补足全宏物理信号连通：已有native_physical的ITerm net membership和局部`changed-via-contact-744.json`都不能替代真实几何导通。767原有自动门还不能单独授予这项资格；最终总验收必须额外核对该项，保持accepted=false直到完成。后续可以以新最终源增加只读几何连通任务，并让最终汇总明确绑定该receipt。不要把原630的物理/功能/LEC通过转移至新源。

失败封存：722（720两项grid候选失败），730（724预EDA tuple/list错误），732（728两PASS四FAILED），733（729六PASS），742（734单例PASS），744（738联合31→5），747（741两PASS两FAILED），752（750六份覆盖RECT无改善FAILED），757（754联合31→2），758（756 postEDA解码失败，原native结果保留），761（760六份只读审计PASS），765（763实际联合31→0）。前述原始输入/输出和源归档不可改写。759继续入口保留阶段历史。

R404原进程继续，405/406等待真实前置；M/S/T现有300MHz结果保持。资源上限8个Issue121 allocation含旧/PENDING/UNKNOWN，c96默认6×16独立队列即完即补。当前最后一步是单个依赖链，不能复制EDA占满槽；就绪的独立最终门并行进入。

规则rayggxia-project-collab1.0.0；实际账号/负责人YUZE-LU，PR122 OPEN/draft，Issue121 OPEN/in_progress。登记PR5本次核验OPEN/未合并，pending；无config/board.json，看板unverified/同步pending，管理员/独立审查人待指定。五份当前最终结果尚未齐备。
