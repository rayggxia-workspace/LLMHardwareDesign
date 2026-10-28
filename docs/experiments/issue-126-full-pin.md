# 全功能分块、全块二维 pin 与实际接入（Issue126）

任务：[Issue126](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/126)，进行中。
起点：[PR120](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/120)，已重新核实 open、未合并，head `4f91e098127b4320ce50dcb29165a7af1fca559c`。
本分支在其上增量提交，不合并或覆盖旧成果。

直接查看：[中文交互 HTML](issue-126-full-pin/report.html)。

## 2026-10-28 接续：真实接入与六块共同底座（进行中）

用户明确确认六块资源并集、交错布局，并让两功能共享实际固定预连；本轮包含研究M11/M12建模。下方旧阶段的“不扩展M11/M12”和优先边界结论不替代本轮范围；保留内部方案继续系统比较。

- ACT新740-pin接入窗口叶视图：独立native0、4819网/15659端点连通，setup1.255988ns/hold0.031533ns、违规行0。
- GEMM新3021-pin窗口视图：独立native0、268637网连通，setup0.773657ns/hold0.036870ns，但3项最大电容失败。
- MXU新1931-pin窗口视图：独立native0、191438网连通，setup0.246862ns/hold0.040715ns，但1项最大电容失败。
- VECTOR新1022-pin窗口视图：独立native0、375495网连通，setup−4.195674ns/hold0.036847ns，118项时序/电气违规行。独立成本化ECO正在执行。
- 上述四块实际9031个信号pin均与完整增量CSV逐项回读匹配；原功能/层/网络/方向/尺寸和单元/PG/外框保持。新窗口法是完整信号重布线，不能混入此前局部rip的纯XY线长收益。
- 两个SYSTEM的新完整窗口视图仍在执行；llSYS PG修订前26pin/44对直接接触保留，修订后实际13507pin回读、PG指纹相同且直接接触0，不等于完整布通。

ACT256-bit父层实际接入：Aopt和新C均已达到当前native/所检几何/双PG门槛。C的r_data[195]仅修改新增父层M10中间接点，原ACT M5/M6不变；92719独立native0、860网/1720端点连通、PG逐字节保持。新增[真实修复PNG](issue-126-full-pin/assets/act_parent_landing_actual.png)/[SVG](issue-126-full-pin/assets/act_parent_landing_actual.svg)已打开核验；旧1项/后续2项失败都保留。此夹具不等于完整共同底座/系统通过，后续RC/STA采用相同明确研究I/O约束和2/10/50fF负载敏感性，结果单独记录。

该RC/STA已于92732实际执行：原时钟/SDC相同，明确新增研究I/O策略0.2T/0.05T max/min delay、BUF_X4驱动和上述负载。Aopt/C均有约−0.074ns hold失败；10fF时setup分别1.424290/1.353438ns、hold−0.074562/−0.073476ns，C另有4条VIOLATED标记。两者均保留604个零线长接触网的寄生未标注提示，源ODB保持不变，尚无完整RC/STA资格。标记行数不包含所有setup/hold报告行，不能当完整违规总数。先前92726的工具命令兼容性失败也保留，未假写已执行提取。

推送后新增终态：openTPU SYSTEM完整1768-pin窗口版92688/92689已独立native0、460503网/1462823端点所检连通通过；setup−1.779887ns、hold−0.389230ns、2016条VIOLATED标记，仍失败。新增小型terminal_updates/openSYS-r01原生回执补入HTML，旧快照不变。至此五块的11260个实际pin已逐项核对，llSYS完整窗口版仍未终态。

成本化ECO不等于修复成功：VECTOR A/C的原时钟ECO虽然native0/所检几何通过，setup仍−4.136094/−4.162278ns；GEMM/MXU电气专用增量ECO仍有3/1项电容失败。GEMM未增加功能单元；MXU增加1个buffer、标准单元主矩形面积+1.862μm²，但未修复该电容项。两个新ECO拷贝分别移除345005/258099个CORE_SPACER，后续若使用还须恢复填充并完成适用规则；不能说成计算资源或block面积节省，原始数据库不变。

共同构造网表已原生链接：34,954端点与17,686固定逻辑连通分量逐项双射，全部原24,767信号pin及原层保留。两模式逐bit图计划复用同一组256资源，分别770条适配图边；37个常量输出驱动各自独立，另有1个闲置时钟驱动。这是逻辑/原生链接检查，未实现共同布局/预连/时钟/PG、未冻结M1–M10、未仅通过M11/M12实现两套功能。内部施工端口还须在冻结前降为真实保留金属，不能用此网表作已完成底座。

研究M11/M12已实际完成2网/4端点小例与独立native0/几何检查，规则/层高/RC由M9/M10外推，明确研究假设，不具制造签核资格。新增[实际小例PNG](issue-126-full-pin/assets/research_upper_actual.png)、[llSYS PG修订PNG](issue-126-full-pin/assets/llsys_pg_revision.png)、[共同布局proposed PNG](issue-126-full-pin/assets/common_base_proposed.png)，各有SVG；报告连同原图共24幅可查看图像。

旧openTPU父层终态native11失败，旧llaccel父层GRT拥塞失败，92476/92477后续RC/STA未执行。缺SRAM GDS、天线/规则覆盖、模型minimum_period/外部资格及所有STA失败不豁免。详见[本轮交接](../handoffs/2026-10-28-issue-126-common-base-continuation.md)、HTML增量阶段表和原始SHA索引。PR129保持Draft、Issue126保持in_progress。

## 2026-10-28：真实叶模型与后续父层分析

已导出20份与真实叶块版本匹配的研究时序模型：六块A/C共12份，以及ACT/MXU的原XY重布线、Aopt、B和GEMM原XY/Aopt共8份。所有原始信号bit及方向核对通过，匹配SPEF重读的最差setup/hold与原试验均一致；文件、源ODB/SPEF/SDC/Lib SHA、完整端口表和实际失败探针均入库。llaccel SYSTEM C模型只对应8pin局部，不代表已失败的13184pin全C。

这些模型来自实际SPEF及现有研究Lib，区别于路由阶段零电容占位；仍缺minimum_period覆盖和完整外部I/O约束/器件级SRAM资格。原叶块时序/电气失败不删除。两个新父层已通过双电源连通，仍在实际路由。后续独立RC/STA92476/92477已排队，必须先通过native/所检全块连通/PG门槛，并精确匹配模型物理ODB与回执SHA；没有父层签核通过声明。

## 最新完整C与增量物理结果（早期8pin记录见后文）

全部六块A/B/C覆盖已完成；实际完整C和补充修订按下表分别记录。**独立native DRC与OpenDB几何连通通过不等于完整GDS/LVS、父层或系统时序资格。**

| 块/修订 | 实际移动 / 信号pin | 独立native DRC | 所检全块多端连通 | setup / hold ns | 时序/电气违规行 |
|---|---:|---:|---|---|---:|
| ACT 原C | 740 / 860 | 0 | 通过 | 1.259268 / 0.032872 | 0 |
| GEMM 原C | 3039 / 3753 | 0 | 通过 | 0.771186 / 0.041430 | 2 |
| GEMM 增量C_electrical_r03 | 3021 / 3753 | 0 | 通过 | 0.771255 / 0.041530 | 0 |
| MXU 原C | 1964 / 2172 | 3（与VDD短路） | 通过 | 0.245821 / 0.048919 | 5 |
| MXU 增量C_mxu_repair_r03 | 1931 / 2172 | 0 | 通过 | 0.247994 / 0.048823 | 0 |
| VECTOR 原C | 1022 / 2246 | 0 | 通过 | -4.166987 / 0.026787 | 103 |
| openTPU SYSTEM 原C | 1768 / 2229 | 0 | 通过 | -1.765776 / -0.400698 | 2101 |
| llaccel SYSTEM 原C | 13184已place_pin / 13507 | 实际26pin/44对固定PG直接冲突；完整DRT停止 | 完整终态未检查 | 完整C未提取/STA | 不以局部结果代替 |

GEMM恢复真实字节29/30的16data+2strobe到A；MXU恢复完整33pin写lane0，并修复pf_uv[109]、b_rdata[174]两个M5内部PG冲突点。原A/B/C未改，补充完整逐pin表在HTML新增节中，均保持原层/尺寸/网络/单元/PG/边界及相同重布线cohort。真实物理失败是修订依据，不隐藏旧结果。**GEMM/MXU当前优先边界**：修订C实际线长4548300/3132185μm，相对同组原XY重布线4494984/3003026μm分别约+1.19%/+4.30%，并无块内线长收益。VECTOR同样优先边界，两个SYSTEM不建议直接全C替换；ACT有约6.40%实际块内线长收益，仍待父层与完整规则验证。

严格GDS新增结果：GEMM原始及8pin局部C均严格合并成功，但未修改deck分别1346/1358项天线违规；ACT缺2个fakeram GDS，MXU缺4个，不能补造器件。其他GDS检查继续执行，逐项见HTML。没有面积节省声明。

后续严格GDS：VECTOR原始/8pin局部C都能严格合并，但deck均36项天线；openSYS原始缺4个fakeram，诊断deck52486项，含46014项WELL。不能把不完整宏GDS上的诊断当完整规则签核，也不能删除原基线失败。

llaccel SYSTEM完整C的实际place_pin回读已与全部13507信号pin逐项核对，原始/移动后PG指纹逐字节相同。26个pin/44对矩形与固定VDD/VSS同层直接相交，不能靠重布线消除；保留moved/ripped/global ODB和日志后，只停止该新无效试验92369。直接接触证明、实际回读与停止守卫均在HTML链接中；它不是完整DRC检查，也不表示完整C已布线。其他作业继续。

用户授权补充缺失材料后，新建两个**受控父层**，不冒充历史父层：openTPU 6618端点/3408网已在PG与路由前核对通过，双电源连通通过，正在详细布线；llaccel 27050端点独立启动。新TOP_IO/PG策略与37个固定tie cell成本单列，端口Liberty仅物理链接，父层STA禁止据此资格化。历史handoff仍UNKNOWN，详见[决策0004](../decisions/0004-controlled-parent-pin-access.md)。
图像：[ACT](issue-119-pin-xy/assets/act_comparison.png)、[MXU](issue-126-full-pin/assets/mxu_comparison.png)、[openTPU SYSTEM](issue-126-full-pin/assets/opentpu_aux_comparison.png)、[GEMM](issue-119-pin-xy/assets/gemm_comparison.png)、[VECTOR](issue-126-full-pin/assets/vector_comparison.png)、[llaccel SYSTEM](issue-126-full-pin/assets/llaccel_aux_comparison.png)；每块包含局部放大、真实端点图，新增四块PNG/SVG均入库。

复用 Issue55 已有真实 SYSTEM 包装补齐完整功能归属：openTPU 为 ACT/MXU/SYSTEM；llaccel_core 为 GEMM/VECTOR/SYSTEM。18项功能完整归属，两个父层未归属叶单元均为0。外部DRAM/host/封装、llaccel_core外部SRAM存储本体不虚构为已实现block。ACT+MXU合并版是替代粒度，不重复计数。

六块共24,767原始信号pin，A/B/C共74,301行；名称、位宽、方向、层、网络、矩形尺寸和逐pin对应保持。父层逻辑连接及对端pin原层已绑定；原父层真实handoff层/穿层路径仍未知。完整表、来源、候选/冲突/密度与阶段结果见HTML，不把几何L1当实际线长/RC/面积收益。

初步推荐：ACT/GEMM值得稀疏内部数据簇试验；MXU收益有限需局部对照；VECTOR本轮优先原边界；两SYSTEM建议选择性混合布局，全C冲突较多。单块保留边缘pin有可查询理由，不强迫全内移。

已在独立授权目录实际启动匹配8pin的A/Aopt/B/C重新接入，并增加原XY重布线控制A_replay。ACT已完成局部真实重接、fresh native DRC、选中网络真实几何连通及OpenRCX/独立边界STA；其他块按回执分别列示，未完成与失败不改写为通过。
完整全块连通、GDS/LVS/适用完整规则、版本匹配父层可访问性、完整系统RC/STA与电气资格仍待验证。

源码/命令：[full_pin_xy README](../../project/experiments/full_pin_xy/README.md)；完整候选覆盖回执：[coverage_gate](issue-126-full-pin/data/coverage_gate.json)；物理分阶段回执：[physical_summary](issue-126-full-pin/data/physical_summary.json)。
大体积ODB/DEF/SPEF保留于 `/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027`，远程源只读挂载，历史活动作业不修改。

验证入口：

```sh
python scripts/check_project.py
python project/experiments/full_pin_xy/validate_repository.py
```

ACT完整740-pin C现已实际完成接入和详细布线：提取前路由母本经独立进程native DRC=0、全块多端信号/时钟几何连通通过；独立边界setup/hold最差余量约1.259268ns/0.032872ns，电气违例报告为0，仍非完整系统签核。当前OpenRCX后的ODB序列化状态与DRC不兼容，已通过逐阶段对照定位并隔离，所有物理母本使用提取前routed/clean ODB，RCX/STA单独记录。新增四块候选按真实制造网格r02增量修订，r01与失败保留。

## 历史首轮局部C接入记录（后续完整范围见上表）

下表只说明已执行范围；所有六块的当前C试验均独立clean native DRC=0、全块多端信号/时钟OpenDB几何连通通过。GDS/LVS、完整规则和真实父层接入均未由此通过。

| 块 | 实际C范围 | 独立块setup余量ns | hold余量ns | 当前模型结果 |
|---|---:|---:|---:|---|
| act | 740 pin（完整C） | 1.259268 | 0.032872 | 现有独立边界模型下通过，完整系统未验证 |
| gemm | 8 pin（局部；全C未实施） | 0.775029 | 0.051618 | 现有独立边界模型下通过，完整系统未验证 |
| mxu | 8 pin（局部；全C未实施） | 0.242632 | 0.051323 | 现有独立边界模型下通过，完整系统未验证 |
| vector | 8 pin（局部；全C未实施） | -4.166532 | 0.025641 | 实际时序/电气未通过，原基线失败保留 |
| opentpu_aux | 8 pin（局部；全C未实施） | -0.402281 | -0.382246 | 实际时序/电气未通过，原基线失败保留 |
| llaccel_aux | 8 pin（局部；全C未实施） | -2.153024 | -0.547887 | 实际时序/电气未通过，原基线失败保留 |

ACT相同740-pin cohort的原XY重布线/B子集/C：DRT提取前总线长271,186 / 271,833 / 253,825 μm，via为37,557 / 37,833 / 36,918。C比原XY控制组线长−6.40%、via−1.70%，setup余量略变差；这是单次真实路由统计，不是几何L1、RC或全系统PPA，也不能证明优于所有边界优化。外框相同，不计面积节省。

父层材料继续检查了Issue55的44份已完成parent/union/top元数据，5份含精确原叶ODB哈希，但这只提供placement等来源线索，仍未建立逐pin原始handoff/实际层序；不据此指派M8或宣布父层可访问。
