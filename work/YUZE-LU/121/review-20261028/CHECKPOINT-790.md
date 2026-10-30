# Issue121 继续入口（2026-10-31 06:09 CST）

Refs #121 / PR #122；负责人YUZE-LU。目标保持两份审阅修改建议下的五宏各一个基础实现及最终300MHz布局布线/全部端口引出。完整范围与此前证据见[789](CHECKPOINT-789.md)、[785](CHECKPOINT-785.md)。

本轮767新三初态最终网表功能PASS（786：27原始/8实际大文件SHA/358归档Git源），每种574942检查/425971拍；新严格LEC也已实际UNSAT/IDENTICAL PASS（787：16原始/8实际服务器大文件SHA/358归档Git源及receipt输入/稳定输出）。54010输入/53999输出全部匹配、diff0/1输入输出全部0，不是弱匹配或仅RTL功能。

787精确绑定同一最终源receipt f06b8e147dfb8bde4e5cdd662bfbbad97b873e661b3b47c9667a6386a6d06005，以及786功能receipt 266646ae4dffdd8a60d45ba821b373aaa955d951464b1eb7908148a7d39e613b；物理777/全信号几何784也是此源。原630资格不转移。

live-790-queue-state.json是当次实际远端队列字节快照；live-790-refill.json记录SHA与实际事件，功能完成后0.050312042秒formal claim，未等仍运行的DRC，证明真实即完即补。当前767仅完整未改GDS DRC在运行，原生0此前已复查，但不能以此代替完整GDS门。

## 剩余实际工作

1. 等767/94002完整未改GDS DRC自然终态，保留成败。`.local/issue121/collect788.py`仅在终态后封存实际native/完整GDS及输入输出来源；不得因静默或耗时重启。
2. 原767队列随后按真实门生成六文件、pin与全GDS图、完整原生几何；实际查看全图/接口放大，核实完整DEF RECT和原生几何保持。
3. 原769控制器接768全部端口P2/P4和有限RC；实际证明通过后才生成V当前总接收，额外绑定782信号几何证明与8a347ce6强制接收门。旧767/768归档不改写。
4. R404/93555原布局布线继续，405/406按真实前置。最近06:05原PID1987219 CPU增长，GRT extra46；634原控制器保持。M/S/T已有结果保持。

**V总accepted=false，五宏当前最终交付尚未齐。** 新V当前1260²µm/277信号位，fresh物理setup+.012848834/hold+.029884208ns；仅代表该子门，不授予完整系统性能/制造/任意RC资格。M/S/T的high RC已知失败保持。

交付入口delivery-300mhz/README和一页对照已更新当前状态，所有旧实验原样保留为历史。服务器base `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121`。本任务最多8allocation含旧/PENDING/UNKNOWN，其他Issue不计入；c96按6×16独立队列即完即补，真实依赖不足不复制EDA。

目标active、PR122 OPEN/draft、Issue121 in_progress。登记management-hub PR5本轮核验OPEN/未合并pending；无board配置，看板unverified/同步pending，管理员及独立审查人待指定。
