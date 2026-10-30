# 当前继续入口：第一版五宏，尚未齐备

Refs #121 / PR #122。每种一个基础实现，300MHz、M1–M10固定，真实M10接点留给未来M11/M12；无裕量版/阵列/产品扩展。M/S/T保持当前300MHz验收；V/R尚未最终验收。

2026-10-31 05:00 CST：754真实联合29处把V原生31→2/新增0，757封存15原始/7稳定/351归档源Git；重核17份独立receipt、562494普通NETS/路径/RECT与原输入，仍拒收、不转移630资格。729六组M2全部PASS（733，原生27/27/27/28/28/28，六实际命令重叠98.405秒）；728两PASS四FAILED（732，重叠98.188秒），按新增涉事网及无改善剔除后738联合26处31→5/0新增（744）。734单例及741两通过修复已真正并入754；其余失败保留。720失败722、724预EDA路径tuple/list错误730保持；750六组覆盖RECT均31→31无改善FAILED，752封存55原始/36稳定/350源Git，实际命令重叠98.109秒，该方法拒收。756两处M3各三种包围形状候选以真实6×16运行：切孔/另一层pad不变，目标pad在既有同网金属内延长，全部native及最终门待验。局部41项过孔接触审计通过，但不等于全宏物理信号连通验收。R404原GRT extra45、04:53原PID1987219 CPU增长；M/S/T保持，五宏最终未齐。

当前最好的实际修复源为服务器 `block-v1-20261031-754/tasks/revision300-v-joint31-29-compose`，helper commit `31efe7ba143070be98088ce2ffd45f935ef97e35`，source archive SHA `12553c3090f6b58c24df8504e5c50f459703e0e5bfaa9a6ad57b765d34a005d4`。`v-joint31-combined-757/index.json`保存当前ODB/DEF实际SHA与大小；原生仍2项，不能晋升为最终源。它在实际705原31项源上真正组合21处M2+8处M3修改，不是把独立分数相加。

756六候选的实际source为 `5078fe952c4a70582681ca88d3678267b146a54f`、archive SHA `86c45aa654ab44426f487e8e2e534d031ec62da5023e72e5295f619a1e594051`、job93990。阶段模板原唯一网数断言不适合两网各三备选，在任何远程目录/任务创建前已修正本地stage guard为2网6候选；不是EDA失败。实际技术对象创建/形状读回/full native的结果仍待检查。API依据：[OpenDB dbTechVia](https://openroad.readthedocs.io/en/latest/doxygen_output/html/classodb_1_1dbTechVia.html)、[dbBox](https://openroad.readthedocs.io/en/latest/doxygen_output/html/classodb_1_1dbBox.html)；不改变工艺规则。原始技术过孔/源ODB不改写。

`changed-via-contact-744.json`是本轮41项改变过孔的局部接触审计，含两个边接触的原线连接见证；不是全宏导通资格。最终必须补充真实几何信号连通证据，不能把ITerm逻辑net membership等同于物理导通。

下一步：先查看756实际六报告并封存失败；选择真正消除原两项且0新增的候选，再在754效果的共同原705源上真正组合并检查全片0。成功后同一最终数据库重新提取RCX、检查覆盖/时序电气/PG及物理信号连通、原生/完整未改GDS deck、最终三初态功能、严格LEC、六文件、完整实际已查看几何、全端口P2/P4及有限P3/RC。不要沿用630资格；不取消/重启慢EDA。

R404原进程继续，405/406等待真实前置。634控制器无需因日志安静重部署。Issue121上限8个allocation含旧任务/PENDING/UNKNOWN，不计其他Issue任务；c96默认6×16独立任务即完即补，无就绪工作时不复制占位。

规则版本rayggxia-project-collab1.0.0。GitHub实际账号YUZE-LU；PR122 OPEN/draft，Issue121 OPEN/in_progress。登记PR5此前OPEN未合并，本次未再核验，pending；无config/board.json，看板unverified/同步pending，管理员/独立审查人待指定。
