# Issue126：实际256条固定导体、真实diode及新电气失败

## 2026-10-29 增量终态（gate-r14，优先于下方历史）

恢复核验PR129仍open/draft，在线head ddf59eee8b004bd871b68942cb3fecaa96f8a10c；本人账号huangpingyang04-lgtm/id239819021。共同资源选择不再询问，整个目标继续active。

- GEMM92940完成：ROOT/diode_cap_eco/r01/gemm-C，driver98342d02aa1c008f9aa8a2757e7d346bd855db79。INV_X1→X2及XNOR2_X1→X2原Liberty逻辑/状态严格相同；全部原端点/网络/端口、636真实diode及pin/PG/外框保持。fresh native0、268637网所检连通、双PG及真实RCX/STA完成，setup/hold 0.770752/0.039624ns，文字VIOLATED=0。单列2换型、1移动、master面积+1.330μm²，非block面积/纯XY收益、RTL形式或完整规则通过。
- 第一diode版严格GDS92912已FAILED：ROOT/antenna_diode_stream/r01/gemm-C，merge和不修改的原deck命令均0，但实际37项天线（M3:2、M4:6、M5:13、M6:9、M7:1、M8:5、M10:1）。原1460及新37分别保留。换型后严格GDS92943在antenna_diode_stream/cap-r01/gemm-C、driver4949a34c8b5dca34345d9655a2411c32e10dd0af仍RUNNING，不能混用两个物理版本。下一步按匹配SHA的多边形定位剩余网，先查现有636个diode是否覆盖，不盲目重复插入。
- SYSTEM92925终态FAILED，ROOT/output_chain_resume/r01/opentpu_aux-C。GRT/DRT命令已执行，但preserve_contracts导出坐标遇到空句柄：resume_output_chain.py选中字典值为{}，后续$i getLocation失败。最终routed ODB未保存，fresh DRC/RC/STA未执行，空route.drc不是通过。原合法化检查点及合同保留；修复按名字查找真实实例后在新目录复用，不重选或重复移动buffer。
- gate_milestones/gate-r14由92963/driver2919390bb231d2d4ad62b901ee9c7cc0d390325e不可覆盖收集，raw/gzip双SHA。大体积原生物理文件仍留授权ROOT；原30图及24767 pin/74301行A/B/C不重做。

本阶段上传/在线读回后，执行已编写run_full_upper_adapter.py/full_upper_adapter_job.sh的770-edge双模式适配试验（尚未提交，实际作业以回执为准）。只读取同一个真实但私有下层未完成的fixed_prewires_NOT_FROZEN.odb，明确adapter-only/unqualified；不是两完整系统/合格冻结。原pin M5/M6不变，新父层M10 hook与via10 landing独立核查。其他活动92690/92691/92841/92892/92855/92943继续，不按耗时取消。

VECTOR/SYSTEM时序、LL窗口终态、缺真实SRAM GDS、原规则/模型覆盖、历史父层目标层、RTL功能/共同冻结/完整对照均未闭合。Issue/PR保持in_progress/Draft；登记pending、看板unverified/同步pending、审查人待指定。发布head/CI以PR读回为准，不以本地成功替代在线结果。

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
