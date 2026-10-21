# Issue #7 三节点第二轮：电容裕量、验证及顶层准备

- 日期：2026-10-21，中国标准时间（UTC+08:00）；具体观察时刻见各 `latest.json/observed_utc`。
- 用户明确同意三个节点并行；延续 [Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)／[草稿 PR #10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)，负责人 YUZE-LU。本轮读回整体Issue标签为 `status:in_review`，由主线维护，不改回；本并发实验仍运行，审查人、优先级待指定。
- 只维护本分支专有目录；不修改主线 PR #8 的 VECTOR／PG、工作树、输入、状态页或作业。源码、工具、small 参数、SDC及研究模型边界沿用[首轮记录](issue-7-parallel-blocks.md)。
- runner：[wave2](../../project/experiments/parallel_blocks/wave2/README.md)。每次新远程根均禁止覆盖，位于 `yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-XX/`。计算节点 SHA 清单绑定实际脚本与输入；后续提交不倒填为已执行版本。

## 已启动的工作线

| 线 | 首次作业／资源 | 内容 | 当前接续 |
| --- | --- | --- | --- |
| A | 89480／node7／64 CPU | ACT CAP_MARGIN=0、10、20各16 CPU，原RAM／连接验证8 CPU，原GEMM回归8 CPU | 验证已结束；三路物理任务在新根06由 **89497／48 CPU** 重跑 |
| B | 89481／node8／64 CPU | GEMM裕量10／20、MXU裕量20、ACT＋MXU裕量20，四路各16 CPU | 新根06由 **89498／64 CPU** 重跑 |
| C | 89482／node9／8 CPU | 在新目录从首轮实际最终ODB／SDC／SPEF导出LEF／时序模型，保留电容失败 | COMPLETED0:0，2:16；后续1 CPU任务完成接线和共同边界准备 |

所有提交均 `--time=0`，提交及计算开始双重核实 `TimeLimit=UNLIMITED`；不设测试墙钟超时。step 用 `srun --exclusive --cpu-bind=cores`；A 首次总3×16＋8＋8=64，B总4×16=64，接续A不重占已完成验证的16核。轻量诊断在A空出的核执行；一次性审计实际由调度器分配1核，有的与主线位于同一节点，但不共享其目录、CPU allocation或进程。

当前正式物理接续根是 **`parallel-blocks-wave2-06/`**，runner commit **`05074e2`**，另有 **89499 afterany:89497:89498** 一次性终态审计。三路ACT均已完成（A批次6:00），四路大块仍在运行；最新实际阶段见[06轻量索引](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-06-latest.json)。06原审计只列计数门槛，后续发现需核对最差电容余量，因此另有下面的独立严格审计，不能把06计数门槛当成最终接受条件。

## ACT对照与改进后的严格门槛

三路均DRC／天线0、setup／hold TNS0、max-slew／fanout计数0，最终日志均报告VDD／VSS所有shape连通，宏LEF／Liberty／详细OBS已导出。**电容计数0不能单独证明最差余量非负**：裕量10的详细报告余量仍负，原因尚待核对；本次采用计数0且最差余量及其归一化metrics均非负的双条件，不将该路接受为通过候选。

| CAP_MARGIN | step耗时 | Setup WS ns | Hold WS ns | Max-cap计数 | 最差电容检查余量（原报告值） | 非filler实例面积µm² | 严格工具门槛 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 0 | 5:57 | +1.22599 | +0.0322719 | 2 | −2.65367293 | 35,870.1 | 未通过 |
| 10 | 5:06 | +1.21024 | +0.0300581 | 0 | **−0.77620065** | 35,899.1 | **未通过** |
| 20 | 5:01 | +1.26007 | +0.0322258 | 0 | +2.44165897 | 35,985.5 | 本次列出的门槛通过 |

电容余量章节未声明单位，保留原值不擅自标单位；对应 `finish__timing__drv__max_cap_limit` 为−0.0438616／−0.0128295／+0.152397。面积含synthetic SRAM；裕量20的面积比0增加 **0.321716%**。0基线的WS、面积及电容计数与首轮一致，为本次固定配置对照提供复核证据，不代表其它块可直接复用其结论。

新根10／**89508（node9、1CPU，23秒）**独立核对三路每路825项源文件和154项输出manifest，全部通过；89497三step及该审计均COMPLETED0:0，89509后续产物审计通过。[10冻结回执](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-10-completion.json)字节SHA `79eb9f76f92047beecde861cbc3dc9ade5b6c7b0c1a272f2a30f1aa551efc60a` 已核对。**act-cap20只是下一步宏视图资格检查的候选**，仍未完成完整arc／外部边界／源到物理等价或制造签核。

完整七路的同类严格审计已在新根11提交 **89510／node9／1CPU／afterany:89499**，结束后 **89511** 封存；均UNLIMITED、等待时不占核。其runner `f46deb0`已在ACT上实际验证。该链会逐case保存最差余量与所有失败门槛，即使06原审计失败也运行。恢复时同时读取06与11，完整结果的严格判读以11为准。

新包装先按原probe的固定顶层名探测存储，随后只对本次包装顶层使用唯一名字 `llhd_opentpu_act`／`llhd_opentpu_mxu`／`llhd_opentpu_act_mxu`，LEF／Liberty／网表同名，避免三个旧视图均为 `otpu_asic_top` 的身份碰撞。原源RTL、参数、宽读端口、容量、寄存器数量、周期语义不改。电容裕量显式写入配置；0同样重跑，不能把旧运行的随机差异当成裕量收益。

## 验证结果及各自范围

**openTPU：89480.3，COMPLETED0:0／1:26。** 原 `tb_tech_ram` 的generic与ASIC模型逐周期比较12组：原6种端口／深度组合，加实际ACT／MXU使用的6种维度。每组超过10000条周期记录，固定seed3，全部一致。另对三种实际elaboration检查ACT–MXU连接逐bit一致，外部端口与合并包装一致，分开与合并的fakeram类型／实例数量相等。这不是完整MXU数值回归，也不证明源RTL到最终物理网表等价。

**GEMM：原回归实际1000例通过，首试采集器失败单列保存。** 原 `tb/Makefile gemm`、seed1、EPILOGUE_FUSION0／1各500例，含原denial测试；`make`退出0，日志明确两行 `500 passed, 0 failed`。首试采集脚本误匹配成cases／failures格式，造成89480.4及validation标失败1，未改写为成功。新根02的 **89484** 独立核对原日志SHA与原 `make_exit_code=0`、两组summary及seed／denial记录，COMPLETED0:0；**没有重跑模拟**。89485产物审计也通过。日志SHA `a2eaafcc9f6171aa517661a1a93f55107ef529fbe2f983ed82ed7438948c061c`；[冻结回执](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-02-completion.json)保留 `original_collector_task_exit_code=1`。物理GEMM只对应fusion0，fusion1通过不授予fusion1物理结果。

**基线宏视图：89482.0，COMPLETED0:0／2:14。** 三块由真实首轮最终ODB／SDC／SPEF生成详细OBS LEF和时序模型，派生视图别名为 `llhd_baseline_opentpu_*`；原ODB与源输入不改。信号pin与elaboration核对一致，ACT860、MXU2172、合并1662 bit。三块仍明确 `qualified_hard_macro=false`，保留首轮max-cap=2／12／41，不能拿旧宏直接宣称正式对照通过。

**顶层准备：新根03／89487（node9、1 CPU），COMPLETED0:0／9秒；89488审计通过。** 根据核对过SHA的视图元数据生成两个黑盒宏及实际连接Verilog，Yosys `hierarchy -check`／`check -assert`通过，再从生成JSON逐位核对全部跨宏连接和共享clk；恰好两个宏、40外部端口、1662 signal bit，没有新增状态。684 bit为地址／数据连接，另1 bit是computing反馈；computing同时保留为外部输出，不重复扣除。横排／竖排均R0、80µm通道，提出共同 **1670×1670µm** 外边界。该边界只是待验证候选；未来flat合并实现也要在相同外边界重跑，不能用旧合并块不同die或独立面积之和替代。

三块导出的时序模型均未含 `minimum_period`；顶层STA不能覆盖块内时钟检查。尚未完成完整Liberty arc覆盖审计、相邻块驱动／负载与预算模型、顶层PG及几何via审计，**尚未执行正式顶层PNR**。[03冻结回执](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-03-completion.json)保留接线、候选位置及正式比较前检查清单，不生成可误跑的PNR配置。

## ABC执行故障及修复依据

首试7路均停在ABC返回等待：ACT的 `output.blif` 已在18:52生成，大块也在18:53–18:55生成，ABC进程却处于 `core_sys_select`，CPU账单不再推进。源、配置、stage日志和临时映射文件保留；[只读进程快照](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-abc-wait.json)记录自有作业cgroup、管道、脚本，未附加调试器或注入运行命令。

最小探针只改变TMPDIR：新根04／89491的长路径探针也产生映射输出后停在同一等待；默认短路径能返回。其短路径首次测试夹具漏加载标准单元声明，随后 `check -assert`失败，首试仍记录失败。补齐同一标准库声明后，新根05／**89493** 使用默认临时路径，ABC、`check -assert`和映射JSON均通过，7秒；**89494**审计通过。[05冻结回执](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-05-completion.json)。

上游[ABC完成检测问题 #5495](https://github.com/YosysHQ/yosys/issues/5495)及[完成检测源码](https://github.com/YosysHQ/yosys/blob/main/passes/techmap/abc.cc)说明持久ABC进程通过prompt／完成标记结束回执；这是本地诊断的支持线索，**不证明本镜像UNKNOWN源revision与该历史bug完全相同，也未证明具体长路径解析机理**。本地已证实TMPDIR配置与复现差异，并在真实ACT接续中确认恢复默认路径后能继续。

约19:10，仅终止7个已确认停滞的物理step及长路径探针：89480.0/.1/.2、89481.0/.1/.2/.3、89491.1；[精确终止回执](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-stall-retirement.json)含调度器身份检查、原因、目标与返回码。**没有按耗时终止，没有修改主线作业。** 原89480／89481均FAILED1:0，物理step为CANCELLED0:9；原数据不标作有效物理结果。

接续06恢复首轮已成功使用的工具默认临时目录；其它RTL、SDC、ABC脚本、库、物理配置、16线程不变，CAP_MARGIN仍为各自原定值。未安装／升级工具，未放宽任何电气、时序或功能检查。不能直接把新旧runtime差异当作物理参数收益。

取消会使7个物理step没有最终退出／输出manifest，首试审计 **89483失败**、`artifact_audit_failures=7`；长路径探针审计 **89492失败**、failures=1。原audit.sh在非零退出后未写completion SHA。为保存而非掩盖失败，新根07／**89501**只复制已存在的两份失败completion原字节并在计算节点计算SHA，**89502**审计新副本通过；两份原记录已按该SHA取回，仍分别保留7／1项失败。[01冻结失败记录](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-01-completion.json)、[04冻结失败记录](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-04-completion.json)、[07封存回执](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-07-completion.json)。后续版本audit.sh无论审计退出码如何都封存已生成的completion，同时保留非零退出；不改已提交06的冻结runner。

## 继续与验收

```powershell
python project/experiments/parallel_blocks/wave2/monitor.py --attempt parallel-blocks-wave2-06
python project/experiments/parallel_blocks/wave2/monitor.py --attempt parallel-blocks-wave2-11
```

监视器只读取轻量远程报告／调度器，保存本分支索引；现在还显示最近flow日志、大小与修改时间，不能只凭RUNNING判断进展。运行后的终态由89499一次性afterany审计保存；它不是周期助手监视，临时侧聊不支持定时唤醒。新监视器取得计算节点SHA后下载不可改写的completion，并核对已封存失败副本。

首先判断各路最终提取的电容计数及最差余量、setup／hold、slew／fanout、DRC／天线及PG。大块各自验收；ACT20通过本次严格工具门槛不自动代表GEMM／MXU通过。物理结果不因产物SHA通过而接受。选择实际合格的ACT／MXU／合并块后，补齐视图及边界模型，再实施真实两宏顶层／同边界flat对照。synthetic SRAM、LEC_CHECK=0、功能／物理等价缺口继续显式保留；无制造、系统签核或H2固定底座结论。

严格审计本身也保留失败尝试：89504／根08首次在容器调用status时缺 `sacct`而退出1，并未重跑物理实验；修正为明确记录调度器命令不可用、继续读取实际报告后，89508验证成功。未开始的旧根09审计89506／89507因此取消并保存[行政取消回执](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-09-retirement.json)，由根11接替；08失败completion仍保留。源作业身份和资源以06提交／allocation为准，不伪填容器内缺失的调度器查询。

本地结构、Python编译、Bash语法、Git whitespace及实际验证／接线／SHA检查均按回执执行；CI状态见PR最新head，管理CI不代替物理验收。登记management-hub PR5再次读回仍OPEN未合并，pending；无board.json／已知缺read:project，看板unverified、同步pending，管理员待指定。统一更新原[Issue并发回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7#issuecomment-6312241685)，不覆盖主线正文、不创建重复PR或自合并。
