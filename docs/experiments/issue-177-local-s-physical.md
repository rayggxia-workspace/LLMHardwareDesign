# 局部 S：布局布线与 300MHz 验收

2026-11-04，Asia/Shanghai。对应 [Issue177](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/177) / [PR178](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/178)。当前为运行记录，**尚未取得物理资格**。原有九实例 RTL 结论见[原报告](issue-177-local-s-results.md)。

## 实施对象与门槛

三种独立实现均含真实16KiB四bank标准单元存储及本块仲裁：P4保留四个普通客户与真实宽读feeder；N4为四普通客户；N5为五普通客户。N4/N5的feeder输入固定关闭并在综合时消除，不将未使用的feeder接口暴露为顶层端口。每个配置从自己的映射网表开始，不复用其他宏的布局或物理资格。P4仍是16KiB实验配置，未实现设计PR176中P.S32KiB容量。

采用Nangate45 typical、原生M1–M10、固定M10引脚、真实输入接收器与保护单元。约束为时钟3.333333333333ns、uncertainty0.1ns、transition0.05ns、输入/输出max0.8ns及min0.2ns、BUF_X2驱动、50fF输出负载。验收包括：

1. 六个原生阶段全部完成，保留最终V/SDC/DEF/ODB/SPEF与GDS。
2. 最终ODB/SDC/SPEF在新进程完成全部真实时序端点、setup/hold、电容/转换、RC覆盖、供电/连接、固定引脚及边界约束检查。
3. 最终完整ODB原生DRC为空，独立完整且未修改的FreePDK45 GDS规则集零项，不排除antenna规则。
4. 从实际最终ODB导出的完整信号网表保留保护单元，三种初始化做真实功能回归；严格LEC检查综合与最终状态边界，要求明确UNSAT、IDENTICAL、正数且完整匹配的输入/输出。
5. 四门绑定同一封存来源；六文件与实际版图图像按SHA-256实收核验。独立审查与合并另行进行。

输入型无时序功能的ANTENNA_X1只在LEC布尔投影中按原检查器精确处理；实际物理、负载及功能网表保留。已有检查器和正负控制重跑，不以默认ORFS日志未出现错误替代验收。

## 当前运行与来源

实际目标库映射源码为 `65cf33b6959bf9db292375447021221cb0ee42a3`；当前N4/N5续跑源码为 `68085600aef4d9ffcfddcbe8f78859d90b276475`，P4新轮次为 `b677a49ed370f01aee28ff78306a7b2571094145`。四份RTL哈希在映射和物理准备时重新核对，RTL未因本次物理适配而修改。上传使用Git原始blob，服务器运行前后检查完整输入快照。

全部输出位于获授权的 `/public/home/yuzelu/PingyangHuang/`，Slurm任务名均为hpy-*。当前使用node27/debug，每阶段16CPU、30分钟；阶段间以afterok依赖串联，三个配置可并行。运行目录如下，失败和取消记录保留原状：

| 目录后缀 | 实际用途/状态 |
| --- | --- |
| issue177-s-physical-20261103T160146Z | 分派函数名错误，未进入物理实现 |
| issue177-s-physical-20261103T160312Z | shell脚本CRLF导致调度拒绝；之后改为上传原始Git blob |
| issue177-s-physical-20261103T160337Z | ABC二进制固定路径不适用于当前镜像；改为从实际Yosys安装定位同包ABC |
| issue177-s-physical-20261103T160503Z | 三种目标库映射与准备/综合完成；floorplan修复停留在无放置寄生的线负载估计，交换大量引脚而未改善；核本人任务后取消，完整记录保留 |
| issue177-s-post-20261103T161022Z | 首轮最终门依赖队列；物理前驱替换后取消，未记为已执行或通过 |
| issue177-s-buffer-20261103T161454Z | 三种floorplan通过；N4放置setup修复转正，随后为130932个已有正hold裕量的端点逐个补20ps额外目标；核本人任务后取消，保留原件 |
| issue177-s-hold-20261103T162651Z | N4/N5完成放置；CTS以额外20ps目标插入大量反馈保持缓冲后达到上限，仍有真实负hold，失败。P4无界理想时钟优化96587最终TIMEOUT30:28，不构成通过 |
| issue177-s-path-20261103T164140Z | 只读P4全局放置检查点诊断，96628完成；尚未高扇出修复，不能据其极差未修复延迟推断最终时序 |
| issue177-s-5ps-20261103T165339Z | 当前N4/N5：核验前三阶段实际成功日志/文件，在新目录续跑CTS/route/finish，采用5ps额外hold目标 |
| issue177-s-p4bounded-20261103T165757Z | 当前P4：新完整轮次，理想时钟放置优化最多200次迭代，CTS及后续新进程完整优化 |
| issue177-s-route-native-20261103T172025Z | 当前N4/N5另一配置：核验并复制已成功的四阶段CTS检查点，原生SKIP_INCREMENTAL_REPAIR=1；完整布线及所有最终门仍执行 |
| issue177-s-drt-20261103T174611Z | N4接收实际完成的全局布线后单独详细布线，仍超过debug30分钟时限，96750超时；没有取得资格 |
| issue177-s-production-20261104T023042Z | 当前常规c96/UNLIMITED续跑：P4从成功CTS开始，N4/N5从成功全局布线开始；每作业16CPU，所有最终门继续执行 |

当前轮明确采用ORFS的REMOVE_ABC_BUFFERS=1，在floorplan删除ABC插入的组合缓冲，随后放置阶段按真实位置重新分组高扇出网络并执行原生repair_design/repair_timing。删除的是实现缓冲，不更改RTL、时序约束或最终检查。最终LEC覆盖这一变换。共享物理脚本只为local_s_*放行这项明确选项，旧宏原有断言保持。

当前轮在放置阶段把额外hold优化目标设为0ns，CTS及后续配置为0.005ns。早期0.02ns目标下，N4插入108561个hold缓冲后触发RSZ-0060上限，最差hold仍约-0.642ns；该失败保留。5ps目标下实际需修复282个端点，N4首次修复插入6471缓冲并得到约+0.005ns，仍须后续布线及最终独立接收。5ps是优化目标，**不是允许负裕量的验收公差**；0.1ns uncertainty、全部接口预算及真实端点setup/hold非负门槛不变，不增加false path或multicycle例外。

P4理想时钟阶段曾反复在约-0.7ns的估计裕量附近修复，新轮次只在该阶段使用原生`-max_iterations 200`，避免无界优化；CTS新进程不继承此限制，最终门不变。参数语义见[OpenROAD官方Resizer说明](https://openroad.readthedocs.io/en/latest/main/src/rsz/README.html)。服务器实际二进制的help已核对支持该参数；不使用文档中新但本机不支持的优化功能。

N4/N5续跑由原作业96600/96613的完整放置文件、三个成功stage回执及日志SHA支撑。新目录中的placement-source保留逐字节快照和显式passed=false的原失败整轮适配回执；只继承已完成的三个阶段，不继承失败CTS资格。新CTS、布线、finish及全部最终门仍实际执行。

当前作业链：N4为96632–96641，N5为96642–96651，P4为96654–96666。后续实际终态、时序/面积/DRC及文件实收将在完成后写入本报告。**排队、准备完成或中间修复完成都不构成300MHz通过。**

N4/N5的完整增量优化布线轮次继续保留。由于全局布线后的额外电气优化耗时长，新配置使用ORFS原生`SKIP_INCREMENTAL_REPAIR=1`跳过该可选优化段（含该段的增量时序优化），不跳过全局/详细布线、保护/天线处理、寄生提取或任何独立最终验收。新轮次源码为`6f416c17231284b33aa151244e908c620c4b2744`，N4作业96685–96693、N5作业96694–96702。只有实际最终STA/电气、完整DRC、功能及严格LEC全通过的候选才可交付；优化段少执行不能自行赋予资格。当前尚无通过结论。

后续真实终态：96634/96644的全量增量优化布线、96686/96695的原生替代配置以及单独详细布线96750均因debug时限超时，不能记为硬件通过。P4的CTS96658自然完成22:52；CTS内原生LEC明确UNSAT/IDENTICAL，267511输入、268088输出边界全部匹配。N4/N5的全局布线子阶段分别实际完成10:05/9:40，其原生成功退出后才生成的哈希表与ODB/SCD原件一并校验，用于检查点接收。

当前常规分区源码为`7c5314374f2a458bdab7af5bc89a33ce52b6cc68`，任务根目录如上：P4为97022–97030，N4为97031–97039，N5为97040–97048。不再使用debug的30分钟窗口承载长布线任务。P4保留完整增量优化策略；N4/N5保留其已执行并封存的原生替代配置。KLayout缓存另设在各新任务目录。最终以实际输出及全部独立门为准。

## 复现入口

`project/experiments/block_local_s/physical_job.sh`在Slurm分配内启动固定容器；`physical.py`支持map、prepare、resume、stage、seal、physical、drc、function、formal、deliver。prepare只生成受校验配置，不把它报告为物理完成；resume只接收日志明确成功的前三阶段，并保存checkpoint原件/回执。stage必须严格按do-1_synth、do-floorplan、do-place、do-cts、do-route、do-finish执行；seal之后四门在新输出目录执行，formal依赖实际function，deliver依赖全部门。所有运行输出路径必须新建，禁止覆盖已封存轮次。

本次不包含层级Liberty、M11/M12接入、完整计算Block/母控/网络、三模型或代工制造签核。完整物理资格仍待上述门全部实际通过。
