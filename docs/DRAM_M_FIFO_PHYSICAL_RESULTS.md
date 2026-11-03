# 500MHz内存侧经FIFO直供300MHz M：物理验证

2026-11-03；Issue173 / PR174；huangpingyang04-lgtm。本报告补充首次RTL报告，原18组/2340矩阵和全部原件保留。

**已完成服务器综合、完整布局布线、实际寄生提取和独立STA：500MHz用户读接口→异步FIFO→装载适配→300MHz原版M，在下述接口预算和Nangate45 typical条件下通过。setup、hold、电容、转换时间违例均为0，详细布线原生DRC=0；实际最终单元网表3组、393个矩阵全部正确。**

完整结果见[独立STA回执](../work/huangpingyang04-lgtm/173/physical-evidence/j96378/output/audit-summary.json)、[最终门级回归](../work/huangpingyang04-lgtm/173/physical-evidence/j96377/output/gate.json)、[原件索引](../work/huangpingyang04-lgtm/173/physical-evidence/evidence-index.json)。原来的18组/2340矩阵及47份轻量证据没有删除或替换。

## 布线后实际结果

余量为正表示满足对应预算；表中数值单位均为ns。异步跨域行是max/min传播预算，不是对第一级采样器作同步相位假设。

| 检查路径 | 最大延迟/setup最差余量 | 最小延迟/hold最差余量 |
| --- | ---: | ---: |
| 300MHz域普通setup / 同域hold | +0.250699 | +0.015965 |
| 500MHz域普通setup / 同域hold | +0.092419 | +0.017511 |
| 请求方向300→500MHz，跨域2ns/0ns预算 | +0.980983 | +0.082946 |
| 返回方向500→300MHz，跨域2ns/0ns预算 | +1.013540 | +0.082713 |
| 返回FIFO→装载器的实际数据路径 | +1.013540 | +0.148034 |
| 装载器A→M银行 | +2.131186 | +0.094185 |
| 装载器B→M银行 | +1.693003 | +0.059613 |

另对20位Gray源→第一级同步器逐位检查，2ns上界的最差余量为+1.848850ns；20对同步器第一级→第二级的0.30ns上界最差余量为+0.088553ns，普通hold最差+0.017511ns。最终这20对之间共有**40个非反相CLKBUF缓冲**，两级触发器身份、时钟归属和纯缓冲连接均经核对。

全局max/min检查最差余量分别为+0.088553168ns、+0.015965285ns；前者来自额外的同步器0.30ns约束。普通300/500MHz域setup余量已在上表单列，不能把额外max-delay约束误说成M的普通setup关键路径。

覆盖检查：两个实际传播时钟分别覆盖26475/2260个触发器，与综合一致；检查61890个STA端点、680057个信号引脚。功能端点漏约束0、输入开路0、输入无唯一驱动0、未放置0、活动信号寄生漏标0、部分寄生漏标0。31730个非功能例外逐项归因：28438个无负载输出、3288个未连接输出、4个明确的原始复位同步器异步引脚；31726个未标注驱动均实际无负载。完整大表留在服务器，SHA和位置见回执及原件索引。

最终实际逻辑/时钟/修复单元面积为335095µm²（不计填充），die为910×910µm。已生成匹配的最终ODB、DEF、Verilog、SDC、SPEF；本次没有宣称生成GDS或取得制造工艺全规则签核。

## 实际执行与修复对照

| 阶段 | Slurm / 终态 | 实际执行源 |
| --- | --- | --- |
| 完整顶层综合 | 96278，COMPLETED 0:0，1分35秒 | `e1e51bb1f3b1864d2bae13a386b1081c60cab9c0` |
| 生产RTL回归 | 96279，COMPLETED 0:0，3组/393矩阵 | 同上 |
| 综合单元网表回归 | 96289，COMPLETED 0:0，12分21秒，3组/393矩阵 | `0ef554ad8edb86f80870d9fbbde36c6c76c7c60c` |
| 本次完整顶层CTS检查点 | 96296，综合数据库/布局/CTS已完成，首试布线被常量网拦截 | `1970d1998a97038a206379ce3204a22f39da186d` |
| 最终修复版route/finish | **96364，node1/16CPU，COMPLETED 0:0，28分40秒** | `ae0425db21954aa5cd64549ceddb2e91ff0181a0` |
| 最终独立SPEF/STA | **96378，node1/16CPU，COMPLETED 0:0，1分13秒** | `456336eeb4658e591ea7c75d22d21142b48bf62a` |
| 实际最终单元网表回归 | **96377，node1/16CPU，COMPLETED 0:0，7分26秒** | 同上 |

最终布线从本次自己的完整顶层CTS只读副本继续；全部继承检查点、父回执和输入SDC均核对SHA，记录在[physical.json](../work/huangpingyang04-lgtm/173/physical-evidence/j96364/output/physical.json)。没有继承其他任务的M物理资格。

| 物理候选 / 独立审计 | 原生DRC | setup违例 | hold违例 | 电容违例 | 结论 |
| --- | ---: | ---: | ---: | ---: | --- |
| 96320 / 96361：级间数据网被保护，默认电气修复目标 | 0 | 0 | 20 | 26 | 不通过 |
| 96360 / 96371：允许合法级间缓冲 | 0 | 0 | 0 | 23 | 不通过 |
| **96364 / 96378：级间缓冲 + CAP_MARGIN=40配置** | **0** | **0** | **0** | **0** | **通过** |

前后使用相同500/300MHz、IO预算、0.30ns同步器上界和原始库验收阈值。40%的电容裕量是修复优化目标，用于加强驱动/分担负载；最终独立STA重新读取原始库和原SDC验收。先前失败的[完整审计摘要](../work/huangpingyang04-lgtm/173/physical-evidence/j96361/output/derived-audit-summary.json)及[只修hold版本](../work/huangpingyang04-lgtm/173/physical-evidence/j96371/output/audit-summary.json)一并保留。

## 完整实现流程

```text
DRAM ↔ 内存控制器/PHY（本次物理顶层之外）
                  ↕ 500MHz用户读事务接口
          单在途读请求/返回控制
           ↑                    ↓
 请求异步FIFO 49bit×16    返回异步FIFO 138bit×16
     300→500MHz              500→300MHz
           ↑                    ↓
  LOAD描述符/地址生成       A128保持 / B128×4→B512拼接
                                ↓ 300MHz ready/valid
                       原版M的A/B银行→矩阵计算→结果
```

这条方案绕过S。FIFO位于控制器的用户时钟接口与片上300MHz逻辑之间，不是放在DRAM物理引脚前。请求和返回各有一条FIFO；返回同时携带装载位置、格式、银行和错误，不能只跨数据。

物理顶层`dram_m_direct`去掉原测试顶层的停顿开关与操作数观察端口，直接接同一份loader和不变的`block_v2_m.sv`。M也同步释放复位。所有FIFO存储及M内部存储均由这次RTL实际综合成标准单元，未替换成行为RAM、S宏或已有M的物理数据库。软件只给描述符和M命令，矩阵结果由实际M计算。

## 约束与检查口径

500/300MHz来自用户目标；IO延迟、负载和裕量是本次采用的接口预算，尚未绑定真实DDR控制器的时序规格。选定控制器后应按其用户接口时序重新核对。

| 项目 | 固定要求 |
| --- | --- |
| 内存用户时钟 | 500MHz，2ns |
| M与装载器时钟 | 300MHz，10/3ns |
| 时钟不确定度 / 转换 | 0.1ns / 0.05ns |
| 内存侧外部IO max/min | 0.4ns / 0.1ns |
| 片上侧外部IO max/min | 0.8ns / 0.2ns |
| 端口驱动 / 输出负载 | BUF_X2 / 50fF，显式指定ns、fF单位 |
| 全部跨域路径 | max 2ns、min 0ns，忽略双方时钟插入延迟 |
| 同步器第一级→第二级 | 20对各自max 0.30ns，并保留正常同域hold检查 |
| Gray源→第一级 | 20位逐一检查，并约束在2ns上界内 |

SDC没有将两个时钟组整组设为false path。唯一原始reset例外精确指向复位同步器实际异步引脚。同步器两级之间允许为hold插入非反相缓冲，仍受0.30ns最大延迟约束；最终逐一核对两级触发器身份、时钟域和中间只能包含BUF/CLKBUF的连接。时钟与复位网允许合法缓冲。

OpenSTA以寄存器CK为有效起点，包含clock-to-Q与目标setup；没有把Q引脚的不生效约束算成通过。`-ignore_clock_latency`的含义见[OpenSTA命令说明](https://opensta.readthedocs.io/en/latest/Commands/#set_max_delay)。这里用每条跨域路径2ns的保守上界限制传播差异，没有冒称工具执行了不支持的`set_bus_skew`命令。

STA在新OpenROAD进程重新读取实际最终ODB、提取后的SPEF、原精度SDC，传播两个实际CTS时钟；同时检查setup/hold、电容/转换限制、端点覆盖、信号输入连通和寄生标注。另单独报告“返回FIFO→装载器”“装载器A→M银行”“装载器B→M银行”，避免只看M内部一条好路径。

## 功能与综合

综合实际得到157365个标准单元，其中28735个触发器，core/mem分别26475/2260；综合库面积292596.276µm²。使用Nangate45 typical与项目既有ORFS容器，综合、布局、双时钟CTS、详细布线、寄生提取均针对完整顶层。

生产RTL、综合单元网表及**实际最终布线单元网表**各运行3组500/300MHz测试，各393个矩阵，均通过；对应日志中数值与计数一致。每组131个矩阵包括128组随机/尾K/尾N/双银行/S8与S16、读错误恢复、协调复位恢复，以及实际M银行锁造成的装载阻塞。请求FIFO满5128–5204个core周期、返回FIFO满361–368个mem周期后均恢复。每组3589个接受读、3588个返回，差1个属于明确的在途协调复位放弃；未用测试门控替代M阻塞。

三个版本的坏数据负控制均翻转实际内存返回的一位，以`independent matrix oracle mismatch`拒绝。零/一/随机初态与0/3/7时间单位相位的检查属于数字零延迟功能验证，不是SDF或模拟亚稳态仿真。最终门级使用的网表SHA-256为`a25b4f3c559bdd5d99eafa4fa759ec7e400aa0f20c5b62f8f7fa99dcc6471131`，与实际物理回执和独立STA一致；没有行为RAM替换或网表功能改写，编译程序及外部Verilator二进制身份见gate.json。

## 来源、执行与历史失败

- 不变M：main基线`4b1df2c7cbdaa0fa6f9f468f2b5b854cec875609`，Git blob `d91ffdf904bc77c19d5d0ecfd4cd11560b44a417`，SHA-256 `5825adcd3364d4315afd1aa4addae85379fb36df2802ca8ab60026e0b0f44d1e`。
- 成功综合执行源`e1e51bb1f3b1864d2bae13a386b1081c60cab9c0`；物理与后续审计执行源分别记录在实际作业表及`source-snapshot.json`。复用时校验RTL、网表、库的哈希。
- 镜像SHA-256 `49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a`；Nangate库SHA-256 `8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1`。
- Yosys自报0.68+post、源码版本UNKNOWN；OpenROAD自报unknown；Verilator5.042。保留工具自报值，以固定镜像/库/输入哈希识别环境，不编造工具commit。
- 所有新文件位于本人`/public/home/yuzelu/PingyangHuang/issue-173-physical-*`新目录；c64 Slurm、本人hpy前缀、UNLIMITED。未覆盖旧输入、原功能结果或其他人的目录/作业。

失败尝试也保留：ABC完成BLIF后在返回握手等待，表现与[Yosys #5495](https://github.com/YosysHQ/yosys/issues/5495)相符；严格核对进程身份后仅终止该故障子进程，弃用该次映射，改成任务目录绑定的短`/tmp`后正常结束。其他失败涉及无端口层次注释清理、CDC元数据白名单、数据库初始化、原生SDC命令、IO放置、同步器起点、脚本语法与过宽dont-touch阻止复位缓冲。首版实际布线的20个hold及26个电容问题见上表。

此外修正了复位同步器两个恒0输入的物理tie-low单元、Tcl报告对`$auto`实例名的引用，以及新增tie实例/网同名造成的Verilator限制。实际连接与两级同步器拓扑均重新检查。32核电气修复请求96362尚未启动，因当时仅21核空闲改为16核96364；仅撤回严格核验的PENDING请求，[调度回执](../work/huangpingyang04-lgtm/173/physical-evidence/j96364/scheduler-replacement.json)保留，运行中的作业未因此中断。全部实际计算均UNLIMITED，没有按耗时取消运行任务。

采集包SHA-256为`49959c3aa1109ed5a83d55568559c4741f857c03efedca65b87807deb39e801a`；501份轻量原件/派生摘要逐一验SHA，精选162个证据文件/索引进入本PR。完整大表、数据库及剩余轻量原件保留在本人服务器目录，见[完整原件清单](../work/huangpingyang04-lgtm/173/physical-evidence/raw-index.json)。派生摘要明确链接到其原始完整audit.json的路径和SHA。

## 结果边界

本次验证对象是内存控制器用户接口之后、两个FIFO、适配器和完整M的数字实现。仓库main没有完整DRAM控制器/PHY，外存仍是读事务模型，未做DDR器件或板级验证。Nangate45 typical的实际寄生时序不能替代目标制造工艺多PVT/OCV签核，也没有量化同步器MTBF。端口达到目标时钟不等于真实DRAM能持续喂饱M；当前仍是只读、单在途协议。

复现命令与完整接口合同见[实验说明](../project/experiments/dram_m_fifo/README.md)。本报告不转移任何已有宏、共同底座或整机的物理资格。
