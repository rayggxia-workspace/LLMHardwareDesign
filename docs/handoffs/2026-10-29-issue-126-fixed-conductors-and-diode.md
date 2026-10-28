# Issue126：实际256条固定导体、真实diode及新电气失败

更新时间：2026-10-29 Asia/Shanghai。仓库rayggxia-workspace/LLMHardwareDesign；[Issue126](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/126) / [Draft PR129](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/129)；负责人huangpingyang04-lgtm；分支task/126-full-block-pin-xy。本轮恢复head f2172cfff803c403d2834ca687d465996b6d733c已核实，两CI40733453132/40733452924均success；当前发布head以PR读回为准。上一轮为实际progress，本轮不重复启动原有作业。

## 新的实际里程碑

共同试验92855已实际写入256条M10共享资源导体和1029个新增父层适配接点。独立92930成功导出固定前GRT检查点DEF，但解析漏考虑缩进而失败；92931仅按输入/原生DEF SHA复用并修正解析，全部256个原生FIXED metal10、逐网/port绑定和实际矩形通过。每条中心线32μm、宽0.8μm，总8192μm；末端矩形有半宽endcap，bbox高度32.8μm不是新拓扑长度。source原生before.shared、实际DEF net语句和源码/工具环境均有索引。原失败保留，不重导出或重布线。

新common_shared_conductors_actual PNG/SVG包含真实六资源放置、M10导体/PG/OBS邻域和原生0.8×0.8μm父层施工port放大；不是via尺寸。256行实际逐导体CSV和SHA JSON同步交付。原叶M5/M6 pin不升级；施工port仍须在模式实现中合法降为固定几何。这里只证明原生固定导体属性/几何，并未证明两完整功能已实际复用、底层全部布通或已冻结。

GEMM实际diode92910已完成全部native路由、fresh DRC0、268637网/806621端点所检连通、VDD/VSS命令及真实RCX/STA。setup/hold 0.770727/0.039500ns；**两个新增max-cap失败保留**：_328822_/ZN (INV_X1) cap67.621605>limit60.730000fF，_332783_/ZN (XNOR2_X1) cap27.449909>limit26.016199fF。原功能单元位置/端点/原pin/PG/外框保持，新增636个真实ANTENNA_X1 master面积169.176μm²，每个真实输入cap0.023429fF；不声称block面积改变。Slurm COMPLETED0不能代替电气通过。

92929/driver60ebe4814132ba9dae6dd2e82560d0ab14af4166：全量原生数字图相对证明通过，原226775非filler、826710信号端点、3753端口及所有原master/网络/方向完全保持，新增636个单输入、无输出/状态真实diode，各接已核对的636条网。非RTL形式/模拟/RC时序等价，真实负载变化单列。直接读取实际DB定位两个违例的master，没有猜测。

## 源码/作业/存储

远程ROOT=/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027。

- passive_load_equivalence/r01/gemm：92929，全量相对数字图及实际电气target导出，driver60ebe481。
- shared_conductor_audit/r01：92930，原native DEF导出成功/解析失败，driver23e90abd6530377033742b17cf00af8d3545a9af。
- shared_conductor_audit/r02：92931，仅复用有SHA DEF、逐项FIXED检查通过，driver639c218f73270b80bc4f432571d83faa55732368。
- gate_milestones/gate-r13：92936，新不可覆盖raw/gzip双SHA快照，driverf914fa3d77e72484cd208755eb59b4b839768818；大型ODB/SPEF/GDS/DEF仍留授权存储，由执行回执索引。
- common_integration/r01/C：92855，六资源父层PG所检通过、真实固定线已写入，lower_global_route运行，未合格/未冻结。
- antenna_diode_eco/r01/gemm-C：92910，完整native/RC结果，电气cap2失败。
- antenna_diode_stream/r01/gemm-C：92912，实际严格GDS原deck执行中；最新状态须读实际execution，原1460项在独立终态前不能当作修复。

## 恢复后的第一条实际动作

先读回92912及92925/92690/92691/92841/92892/92855终态，不重复提交、覆盖活动驱动或按耗时取消。针对两个真实master读取原Liberty允许的同功能更强驱动，新增单列成本ECO，不删cap检查、不降外部负载；优先复用原生增量接线流程。必须保留636实际diode、全部原pin层/大小/语义、所有网络/端点、源PG/边界及M2–M10/M4–M10允许层；最终fresh DRC/连通/PG/RC/STA和原GDS deck分别检查。修复方案/作业以新发布回执为准，不把下一步写成已执行。

SYSTEM92925原同1262-buffer检查点已通过独立合法化及原连接/非选中位置合同，现真实重布线；92921 Signal11保留。VECTOR当前真实setup仍−4.140220ns，不能称时序闭合。LL完整窗口及父层继续；原缺SRAM GDS、原deck覆盖/最小周期和历史父层目标层缺项保持。旧父夹具不代表新成本叶视图已合格。

整个目标继续active；没有合格共同M1–M10冻结manifest、两完整M11/M12功能或公平端到端系统对照。下一份新终态快照gate-r14，不覆盖r13。旧[物理接续交接](2026-10-29-issue-126-physical-continuation.md)保留全部历史。

规则rayggxia-project-collab1.0.0；project_id=llm-hardware-design；登记management-hub PR5 pending；缺board.json/Projects能力，看板unverified/同步pending，管理员/审查人待指定。Issue in_progress、PR Draft，Refs #126，不合并PR120/129。
