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

实际目标库映射源码为 `65cf33b6959bf9db292375447021221cb0ee42a3`；当前物理/验收脚本源码为 `a14d26e312de86e8ad8e72c0725fad9b8a8c0079`。四份RTL哈希在映射和物理准备时重新核对，RTL未因本次物理适配而修改。上传使用Git原始blob，服务器运行前后检查完整输入快照。

全部输出位于获授权的 `/public/home/yuzelu/PingyangHuang/`，Slurm任务名均为hpy-*。当前使用node27/debug，每阶段16CPU、30分钟；阶段间以afterok依赖串联，三个配置可并行。运行目录如下，失败和取消记录保留原状：

| 目录后缀 | 实际用途/状态 |
| --- | --- |
| issue177-s-physical-20261103T160146Z | 分派函数名错误，未进入物理实现 |
| issue177-s-physical-20261103T160312Z | shell脚本CRLF导致调度拒绝；之后改为上传原始Git blob |
| issue177-s-physical-20261103T160337Z | ABC二进制固定路径不适用于当前镜像；改为从实际Yosys安装定位同包ABC |
| issue177-s-physical-20261103T160503Z | 三种目标库映射与准备/综合完成；floorplan修复停留在无放置寄生的线负载估计，交换大量引脚而未改善；核本人任务后取消，完整记录保留 |
| issue177-s-post-20261103T161022Z | 首轮最终门依赖队列；物理前驱替换后取消，未记为已执行或通过 |
| issue177-s-buffer-20261103T161454Z | 三种floorplan通过；N4放置setup修复转正，随后为130932个已有正hold裕量的端点逐个补20ps额外目标；核本人任务后取消，保留原件 |
| issue177-s-hold-20261103T162651Z | 当前运行；复用各自的已绑定映射，从新的准备与全部六阶段开始 |

当前轮明确采用ORFS的REMOVE_ABC_BUFFERS=1，在floorplan删除ABC插入的组合缓冲，随后放置阶段按真实位置重新分组高扇出网络并执行原生repair_design/repair_timing。删除的是实现缓冲，不更改RTL、时序约束或最终检查。最终LEC覆盖这一变换。共享物理脚本只为local_s_*放行这项明确选项，旧宏原有断言保持。

当前轮在放置阶段把额外hold优化目标设为0ns；CTS新进程重新加载配置的0.02ns目标。保持0.1ns uncertainty及最终全部实际端点setup/hold非负门槛，不增加false path或multicycle例外。此设置避免在理想时钟阶段给大量正裕量反馈路径提前补缓冲，不能替代真实CTS后修复。

当前轮作业链：P4为96584–96596，N4为96597–96609，N5为96610–96622。后续实际终态、时序/面积/DRC及文件实收将在完成后写入本报告。**排队、准备完成或floorplan完成都不构成300MHz通过。**

## 复现入口

`project/experiments/block_local_s/physical_job.sh`在Slurm分配内启动固定容器；`physical.py`支持map、prepare、stage、seal、physical、drc、function、formal、deliver。prepare只生成受校验配置，不把它报告为物理完成。stage必须严格按do-1_synth、do-floorplan、do-place、do-cts、do-route、do-finish执行；seal之后四门在新输出目录执行，formal依赖实际function，deliver依赖全部门。所有运行输出路径必须新建，禁止覆盖已封存轮次。

本次不包含层级Liberty、M11/M12接入、完整计算Block/母控/网络、三模型或代工制造签核。完整物理资格仍待上述门全部实际通过。
