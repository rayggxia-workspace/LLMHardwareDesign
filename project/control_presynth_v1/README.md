# 第9步：控制侧综合交付冻结

Issue179 / Draft PR180，Melodydt。固定现有九种有界配置，不新增产品拓扑或改变控制RTL。执行镜像仍v2、64 bit、little endian，目标周期3.333333333 ns。

## 顶层与参数

| profile | top | KIND | 实际两端 |
| --- | --- | --- | --- |
| five/U、F、C、P、J | five_boot_top | 0、1、2、3、4 | U/U、F/F、C/C、P/P、J/J |
| recovery/U、F、C、J | recovery_boot_top | 0、1、2、4 | U/P、F/P、C/P、J/P，源0→目的1 |

全部综合配置PM_USE_SRAM=1。MC/LC STALL_LIMIT=4096，LC DRAIN_LIMIT=128、LOCAL_S_BYTES=16384、BLOCK_ID=0/1、ENABLE_NATIVE=1；恢复监督DRAIN_LIMIT=1024。ABI/capacity/topology及类型以[freeze.json](freeze.json)和[统一目标表](../control_task_compiler_v1/targets.json)为准，工具要求一致。不要套用早期通用Block编号。

每端一常驻任务、一在途服务，两个CALL后共同WAIT。16种已实现opcode与候选指令分开；G_PARAM、循环及未接入算术/FAIL仍不准入。编译器面向固定原生配方，不是完整LLM图前端。

## 两份清单与实际边界

package.py从本分支和冻结stage生成可搬移包，核对67份控制SV/SVH来源锁及实际使用的原生源SHA。包内包括profile.json（顶层/参数/边界/实例/源SHA）、full.f、control.f、boundaries.f、相对路径synth.ys、constraints.sdc、锁定Nangate45 typical Liberty及标准单元tech/macro LEF、逐项SHA的manifest.json。

full.f保留真实控制、原生组、计算/存储连接及功能bank，排除tb文件。control.f综合控制/胶合逻辑及PM接口，原生计算组以原声明生成的port-only边界代替。原生group只是逻辑综合分区，不是新组合硬块，不假定存在group LEF。全RTL清单与控制分区的资格不能混用。

控制分区预期1 MC、2 LC、2原生group、12个PM bank。Block内S、计算宏及J的片段/T资源保留在原生边界内，不能把12解释为全芯片SRAM数量。每PM为16KiB、128 bit访问、16B对齐、单在途、四个256×128 1RW bank；三PM共48KiB。PM_USE_SRAM=0仅功能对照，不进入综合发布。含任意延迟的行为bank仅用于功能，综合只读接口声明。小型控制寄存器/FIFO仍照常综合。

本包不提供原生group/SRAM的完整Liberty/LEF物理绑定；组合STA须展开实际叶宏并绑定合格视图。标准单元库固定TT1.1V/25°C，不转移PR213/214独立组资格。USE_POWER_PINS未定义，无新电源门控/UPF。

## SDC与复位

沿用[既有接口预算](../control_native_timing_v1/constraints.json)：输入max/min=0.5/0.05 ns，输出max/min=0.5/0.05 ns，输入转换0.05 ns，输出5 fF，setup/hold uncertainty=0.05/0.02 ns。周期3.333333333 ns不放宽，理想时钟、CTS前。主机同步于clk_i；rst_ni包含在输入预算，不用false path压掉recovery/removal。

OpenSTA的set_units是单位核对，本SDC按ns/fF写5.0 fF负载；参考[官方SDC实现](https://github.com/The-OpenROAD-Project/OpenSTA/blob/master/sdc/Sdc.tcl)。检查会读回单位和序列化SDC，逐位核对输入输出max/min。夹具端口来自真实Yosys展开顶层，但没有伪造计时路径：这是语法、对象、预算核验，不报告WNS/TNS或组合STA通过。单时钟合同也不等于多时钟CDC/RDC签核。

## 复现

RTL/综合在授权服务器经Slurm执行，本机仅做管理及软件静态检查。占位路径由有权使用输入的人提供。实际源、工具、包和结果SHA见[验证索引](../../work/Melodydt/179/control-synthesis-freeze-validation.json)。

```bash
python3 -B project/control_presynth_v1/check.py
PROFILE=recovery/J NATIVE_STAGE=/inputs/stage SRAM_BANK=/inputs/bank.v \
PLATFORM=/tools/platforms/nangate45 VERILATOR=/tools/verilator \
YOSYS=/tools/yosys OPENROAD=/tools/openroad \
bash project/control_presynth_v1/run_freeze.sh /results/new-recovery-J
```

运行九个profile；package输出须不存在，禁止覆盖冻结证据。validate.py分别做full/control lint、Yosys hierarchy/synth -noabc/check -assert、实例/SRAM计数和SDC对象核验。test_package.py拒绝六类损坏，包括自洽重算SHA后的行为bank误入、推断PM和false path；这不是六个RTL场景。

control-handoff.tar.gz可搬移，filelists和synth.ys使用相对路径。新目录仍可运行同版工具：validate.py --package NEW_PACKAGE --out NEW_RESULTS --verilator ... --yosys ... --openroad ...；也可在包目录执行yosys -s synth.ys。使用本交付commit的工具及目标表，输入/库SHA改变必须重验。

结果保留归档/执行commit、包manifest、lint、通用结构网表/JSON、SDC读回、tar SHA及逐文件索引。大包留授权实验存储，仓库留技术索引和工具。第8步1690 RTL/1359软件属于此前功能证据，本轮不冒充重跑。

下一阶段为选定配置的同版映射/组合STA与等价，再绑定宏物理视图推进CTS/布线/物理验收。PR审查/合并、登记及看板同步各自记录。
