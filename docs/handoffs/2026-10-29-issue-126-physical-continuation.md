# Issue126：全量数字合同、真实局部归属及天线修复接续

更新时间：2026-10-29，Asia/Shanghai。仓库rayggxia-workspace/LLMHardwareDesign；[Issue126](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/126) / [Draft PR129](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/129)；负责人huangpingyang04-lgtm；分支task/126-full-block-pin-xy。恢复核实线上head为0f1e43dc59d61005150dc8141c29b288832fa70c，两CI成功。新增驱动commit为9957f1aa7abcdfb3f0909bfbc94c55879f713be5、1d77813aa2dae753bcd368f9f5cb216142016c78、ed81920a56d5e60ab4fb61023b881834e37e59e0、e2b2974e8f25963dda99f3f624e1ebb60a994f49；发布head以PR最新读回为准。

## 已收集的新终态

- 92886，ROOT/buffered_equivalence/r01/opentpu_aux：实际原始与ECO映射数据库导出、所有原端点/方向、Liberty状态/逻辑、5829个新增identity缓冲和980换型逐项检查。438852原非filler、1539803原信号端点、2229顶层端口、529989原网分量、9723个独立NULL端点保持；有向同原驱动可达、无环、无新增多驱动/孤岛通过。5个正反向/循环/改网/NULL反例测试进入CI。固定相同硬存储合同条件下的相对网表证明，非RTL/存储器内部形式等价，原SYS提取setup/hold失败仍保留。
- 92891，ROOT/parent_region_audit/r01：旧MXU父层和旧/成本ECO叶块真实3×3μm局部几何。原生M6 act_data[12] marker重叠OBS 0.0238μm²完全由真实同网叶金属覆盖，旧/成本视图局部M6矩形及网标签相同。最近已导出异网M6几何gap 0.42μm，不是规则通过；各叶源仍有2条OBS变换未核对。新assets/mxu_M6_actual_ownership.png/svg已打开核验，实际pin/父via的M6落脚0.14×0.14μm不是切孔或整栈占地。原父层native2保留，不删OBS、不豁免报项。
- 92901，ROOT/antenna_netmap/r01：1460个原deck真实GDS金属多边形与原生全块导出正面积相交，全部唯一关联636网。后续库存解析错误导致SlurmFAILED，原失败保留。92903，ROOT/antenna_netmap/r02仅修正实际deck polygons/input解析并按输入/产物SHA复用上述完整关联，成功；没有重路由。
- 实际Nangate ANTENNA_X1 GDS存在，原deck `(nplus & active)-nwell` 识别面积0.0081μm²、与contact正交叠0.004225μm²。GDS bbox含well/implant，不能与0.19×1.4μm LEF site混淆。原Liberty输入cap非零0.023429，单位须读真实库头。636网关联不是LVS或修复；原1460项仍未消除。

原始证据在不可覆盖ROOT/gate_milestones/gate-r08（92906）及仓库data/gate_milestones/gate-r08，原文和gzip双SHA；大ODB/SPEF/GDS仍留授权远程路径由原回执索引。ROOT=/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027。

## 本次恢复核实的活动作业

92690 LL完整窗口、92841 GEMM父层单个新增M10落脚、92855六块共同集成、92872 VECTOR从真实检查点重布线、92892 MXU单个新增M10落脚均RUNNING；92691 PENDING Dependency。不重复提交、不按耗时取消、不改活动driver/输出。Issue55及其他工作树和任务不动。

VECTOR已从92867实际14resize/17buffer检查点继续，先去filler避免EST-0104，再时序修复/独立合法化/恢复filler；最终提取时序尚未取得。中间placement估算setup仍负，不当作修复成功。

## 仍失败或未验证

六块原24767信号pin/74301行ABC与完整功能归属不重做。GEMM/MXU C成本ECO已通过native/连通/源RC电气门槛及相对数字合同，保留内部分布；等成本Aopt同样实际完成，块内线长差异不代替系统比较。ACT父层hold失败、SYS源setup/hold失败、VECTOR原setup失败、LL PG-only native4/时序失败、缺匹配SRAM GDS及原deck覆盖缺口继续保留。旧父夹具不冒充新成本叶视图已验证。

六块共同集成92855仍是明确未合格研究试验，不是冻结底座。尚无实际合格M1–M10固定256共享导体冻结manifest、两完整M11/M12模式、全系统功能/RC/STA/电气/公平对照。研究12层两网探针不能替代完整系统。原叶pin层/尺寸/语义/允许布线层不变，新增父层M10中间点另列。

## 恢复后的第一条实际动作

先读回上述作业及execution.json终态，不复做已通过证明。发布当前中文HTML/机器矩阵/新图/原文快照并读回GitHub head/图片及CI。随后对636个已关联GEMM网按真实ANTENNA_X1、输入cap和原规则做单独成本化diode接入试验，原有实例/接口/PG/边界保持并重路由、fresh DRC、完整所检连通、RC/STA及严格GDS原deck；不虚构ANTENNAGATEAREA，不删天线规则或使用占位库。其他独立作业继续；新终态用gate-r09，不能覆盖gate-r08。

规则rayggxia-project-collab1.0.0；project_id=llm-hardware-design；登记management-hub PR5 pending；没有board.json及Projects能力，看板unverified/同步pending，管理员及审查人待指定。Issue保持status:in_progress，PR保持Draft，Refs #126；不合并PR120/129，不标整个目标完成。
