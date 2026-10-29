# M/S/T真实生产者—消费者互联有限实验

## 补齐交付（2026-10-29）

[代表性互联补齐报告](../../../../docs/reports/2026-10-29-block-v1-representative-link-closure.md)为当前结论，以下48项说明属于历史阶段。三种实际预制接口通过原生完整P&R/DRC/LEC；MT17/TS15根完成新层实际详细布线与独立几何检查；41项新测量全部收尾，17项仅在各自声明条件通过。相向切换加20%裕量的当前组合仍失败，MT/TS分别9/8项电容违规，TS另1项slew违规；全宽275/281根尝试未收敛，不授予组合资格。

入口：[41项及31条端口预算](closure-results.json)、[生产18文件不变/16轮源与资源审计](closure-source-and-resource-audit.json)、[有界证据包](closure-evidence.tar.gz)、[每成员SHA清单](closure-evidence-manifest.json)、[执行源归档映射](closure-source-history.json)。将证据包解开到本目录evidence/，可运行linkclose_summarize.py重新核验；展开目录只在本地保留，Git交付确定性压缩包。大数据库及完整报告仍在授权服务器，index明确列出被排除原件的SHA。

强BUF_X16中继可从首段≤1mm/扇出≤4起步；弱端口至第一级中继需逐信号预算，不能套强中继距离。全部本侧线作业已终止，原生产结果未动；Issue121整体保持in_progress，独立审查待指定。当前不能把原M/S/T标为可任意组合。

## 历史阶段交付（14:45 CST）

关联[Issue #121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)，主线[PR #122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)。本侧线使用独立工作树/分支`task/121-interconnect-study`，起点`b451039b3d6083a9dcc8e4db7b46fa4440ed87ac`；不覆盖主线工作树和生产宏、不操作其他运行任务。

## 范围与状态

用户2026-10-29明确授权开始有限互联实验。保留原M/S/T最终资格和high失败；不新增宏裕量版本、阵列、产品或通用NoC。研究固定底座中端口驱动/接收缓冲及少量预制中继的必要性，顶层仍只定制M11/M12和对应通孔。

2026-10-29 14:45 CST：[48项有限实验报告](../../../../docs/reports/2026-10-29-block-v1-interconnect-study.md)已完成并逐项核验。MT为0/24项、TS为19/24项在声明电气和时序条件下通过；实验PASSED只表示测量成功，电路资格由独立的`declared_model_passed`表示。**没有授予新增缓冲的放置布线或真实十二层制造资格。**

核心结果：实际接点距离下，T→S的BUF_X8发送/中继+BUF_X2接收在两种声明电容条件通过，section链路setup+0.308616ns；M→T即使电气违规清零，ready组合路径setup仍为负。不能把所有接口都归因于驱动强弱，必须同时约定控制路径时序。

run907/93222与run908/93236均在node26自然COMPLETED/0:0，34:05/14:07；峰值六个独立16CPU任务、即时补位，单任务RSS采样峰值约6.10GiB，未因虚构RAM限制减并发。首轮释放allocation后才准入补充轮，Issue121共享8项预算保持。原始九个Verilog/SPEF/SDC及三个physical回执实验后SHA保持，见[原输入读回](production-source-readback.json)。

已确认的首例：M→T在568µm/base没有电容、slew、hold违规，但ready跨宏组合路径setup−0.159452ns；T→S相同条件下全项通过。M→T在1200µm/high出现130项电容违规。这里的base/high都是声明的RC敏感性条件，不能称为制造工艺角。

run901–905为前置工具/路径/单位接口调通失败，原始回执保留。run906实际小电路工具控制及两份完整RC准备通过；其真实宏拼接遗漏交付Verilog中被省略的输入天线保护器件，并错误声明部分向量端口，故整批真实宏结果拒收。核验精确job ID/目录/账号后只取消本侧线93214，保留通过的RC准备；没有取消主线或其他成员任务。run907按原生physical回执及清单恢复M142/T190/S143个原有保护器件到实验副本，并使用真实向量端口；原生产Verilog/SPEF没有改动。图准备代码AST、原始输入、复用文件与物理清单SHA均检查，不复用run906失败的STA结果。

## 有限矩阵

- M.rsp_data/valid → T.write_data/valid，T.write_ready → M.rsp_ready。
- T.read_data/valid → S.din/req，S.ready → T.read_take。
- 每组128位数据+valid+ready，合计130根线同时进入STA。T的lease/index和S的写模式/地址等由外部控制输入承担；不冒充完整调度器或端到端协议功能验收。
- 三种电路：原生直接连接；增加BUF_X4输出与输入缓冲；相同端口缓冲再加一级BUF_X4中继。
- 线长250/568/1200µm，base/high（R/C同时1.5×），共36项候选。是长度特征扫描，不承诺给定宏摆放下的几何可达性。
- 端口缓冲的两段局部线各8µm，按同一声明模型计价；中继主线等分两段。每段计两via10加一可能via11的0.24Ω预算。实际缓冲位置/M10接入、新层耦合和制造模型仍待物理验证。

run908的12个有界补充案例已全部测量：采用已接收M10接点的逐bit Manhattan下界，R0相邻摆放、间隔80µm；在四方位中选最小最大距离，M→T向东916/1348/1548µm，T→S向北880/1468/1688µm（最小/中位/最大）。比较直接、BUF_X8发送+BUF_X2接收、再加一个BUF_X8中继，分别使用现有high电容和独立理想截面敏感性值。它不证明130根线能够同时布通，也不授予新增单元的物理资格。仅经Issue121共享dispatcher空出预算后准入。

独立二维截面检查见`cross-section-sanity.json`和`interconnect_cross_section.py`：2µm宽/厚、0.8µm下间隔、εr3.9的理想无限长截面，单下平面/加接地邻线/再加上平面的C′分别为0.219417/0.249961/0.336772fF/µm。三档网格、外边界加远、能量/电荷守恒、解析平行板正例与错误面距反例均通过。连续平面与实际M10/M12图案不同；该结果只表明原high0.233086fF/µm不是普遍上界，不能把新值直接当成真实工艺标定或上界。

完整原生门级宏同时载入，原生连接、所有ground/coupling C与R逐条保留并用计数、SHA-256记录指纹反查；不以虚拟BUF_X2替代真实连接的生产者。非连接的外端口保留原0.8/0.2ns、BUF_X2和50fF条件。连接口使用真实下游输入，避免重复再加接收负载。300MHz/0.1ns不确定度保持；理想共同clock根连接双方原生CTS，不能据此授予共同底座CTS资格。

## 执行与证据

先用真实Liberty的四DFF、保护器件、真实向量端口及分开的原生SPEF检查图合并，实际运行直接/端口缓冲/中继图消费正例和大R/大C负例；通过后才运行真实宏。弱DFF直连本身的电容/slew失败也保留，图正例不等于电路通过。电容、slew/fanout、全局setup/hold和每根真实源驱动至接收负载的路径分别记录。实验成功执行与电路通过分别使用`experiment_completed`和`declared_model_passed`。

远程使用原Issue121共享dispatcher锁及最多8allocation预算，pending/unknown计入，不另开独立预算。一个c96内默认六个互斥16CPU任务、即完补位；16GiB/任务预测参考原S4.523GiB、T1.973GiB实测，另保留1.2系数和16GiB node guard。现有主线任务不取消、不改写。

正式实现：`project/experiments/block_v1/interconnect_{spef,experiment,stage,launch,collect,pin_profiles,cross_section}.py`。`interconnect_collect.py`仅取已关闭回执并逐文件校验SHA；过大原始报告留在授权服务器，仅在源SHA核验后把全零扇出驱动字典替换成计数/字典SHA，派生摘要明确标记，其他结果不改变。大数据库与完整原始记录保留获授权服务器。

复现本地控制：

```powershell
python -m unittest discover -s project/experiments/block_v1 -p test_interconnect_spef.py -v
python scripts/check_project.py
```

证据入口：[原始捕获边界](evidence/README.md)、[36项结果](evidence/run907/measurements.json)、[12项结果](evidence/run908/measurements.json)、[8轮精确归档索引](runs.json)、[原Git历史备份](source-history.json)、[主线交接](../../../../docs/handoffs/2026-10-29-issue-121-interconnect-study.md)。

本地Git HTTPS两次发布连接重置，采用当前成员GitHub连接器发布相同Git树的独立快照；不改写作者、不强推。原实验源commit及代码交付基准e3b129e保留本地和已校验的服务器Git bundle，可恢复全部源码历史；线上快照commit与本地实验commit身份不同，不应盲目再次push覆盖。最终线上PR/树读回见当前任务的提交回执。

协作回执：规则rayggxia-project-collab1.0.0；账号YUZE-LU；project_id=llm-hardware-design。有限实验已交付、独立审查待指定；不改主线Issue121正文/状态或PR122内容，不把V/R或整系统宣布完成。登记pending（复用management-hub PR5待合并证据），无config/board.json，看板unverified/同步pending，管理员待指定。
