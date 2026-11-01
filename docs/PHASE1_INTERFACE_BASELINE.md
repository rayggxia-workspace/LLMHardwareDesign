> 2026-11-01 P2更新：用户要求同步最新PR144并开始第二步；当前14核心RTL采用707878621b2add4ed218b8c43df2e95c9a56e2ba，仅R相对643变化，七顶层接口不变。新增MST控制原型及实际验证见[第二步报告](PHASE2_MST_IMPLEMENTATION.md)。以下P1/既有研究保留原版本与证据边界，不将旧回执重标为新源通过。

# 七宏接口研究P1：版本、合同与最小MST验收输入

任务[Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151)，交付[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，负责人Melodydt。用户已将[七阶段路线](SEVEN_MACRO_INTERFACE_ROADMAP.md)作为本研究路线，本轮仅执行P1，产出可审查的版本/接口/数值参考/测试范围，不提前进入P2 RTL实现。

## 1. 本轮固定的版本与固定边界

研究输入为343f4d4775ffab61b2ed2df13de243cc659c157a。P1及首个MST组合沿用研究分支已导入的643c6012a11cbf461146ac40fbf61485223fe946；14核心RTL/include的Git blob与SHA-256为本轮合同输入。这里“固定”表示实施输入被显式选定，不表示叶宏、共同底座或M11/M12物理实现已新获验收。

开始时读回PR144头adb819c4d49516008e971a201a7d52c0248df8f9，并对相同14路径逐文件读取：13个Git blob相同，仅block_v1_r.sv不同，七个顶层端口规范化声明一致。该观察点为2026-11-01 06:00:34 UTC（14:00:34 Asia/Shanghai），后续源分支前进不会自动进入本合同。比较记录见[phase1-version-comparison.json](../work/Melodydt/151/phase1-version-comparison.json)。

R新版本将rne输入/返回和中间数值检查扩到S128，并调整符号扩展；这不是本轮已证明的数值/周期/物理等价。当前先锁定已审计的旧R合同，不混用源码与物理视图。R最终资格继续由Issue143跟踪；M/N/E/G/S/T上游报告的叶宏结果也不转为新MST组合或完整模型结果。

后续升级必须记录新ref、逐文件/接口/数值/周期差异，重跑受影响参考与RTL/物理门；只有接口相同不足以自动接收。当前不改PR144分支、研究树内叶宏、服务器或ref-project。

## 2. P1的规范交付物

| 交付 | 用途 | 当前证据性质 |
| --- | --- | --- |
| [七阶段路线](SEVEN_MACRO_INTERFACE_ROADMAP.md)及seven-stage-roadmap.json | 顺序、依赖、每步产物/退出门 | P1可评审；P2–P7未开始 |
| [七宏原生合同](PHASE1_NATIVE_INTERFACE_CONTRACT.md)及phase1-native-contract.json | 端口方向/宽度、op/字段/状态/响应/错误与外侧owner | 选定字节的源码观察＋集成侧合同，二者分开 |
| phase1-version-comparison.json | 选定版本、上游观察点及升级规则 | 14路径读取、7接口匹配；非R等价证明 |
| phase1_mst_reference.py及phase1-mst-vectors.json | 为P2提供独立整数预期与命令/存储布局 | 受限软件参考，非RTL仿真 |
| phase1-verification-plan.json | 七宏要求对应到P2–P7测试与证据 | 未来RTL验收清单，不写成测试已完成 |
| phase1-checks/verification回执 | 实际命令、输入/输出SHA与未执行项 | 按实际结果填写，不将管理检查当业务验证 |

角色、类型、尺度与布局仍主要放在编译期契约中。运行时保留原生op/参数、选路、握手、计数、阶段锁与错误处理；本轮不恢复通用role包头或强制通用handle表。

## 3. 首个P2组合的具体输入profile

首个原型只连接S、v2 M、T，选择无额外数值转换的原样结果路径，先验证真实的数据交接，而不是同时引入所有格式服务。

- M：S8×S8，bank0，rows=1、tiles=1、K=8、N=8，clear_result=1，factor=1、left_shift=0。
- S：A448..451保留4个128bit字（含未用行padding），B452..455为n-major的64个S8，结果456..459为8个S64成对打包。共12字192B计算区；旧P0其他预留不因此被偷用。
- 命令：显式CLEAR_ALL后SET_SCALE(op4,data=1)，loader交付完成后EXEC(op10,index=0,data=0x9884)，收到成功计算应答后用op3依次读取index0..3。
- T：BEGIN words=4，顺序写4个结果字，COMMIT，按read_valid/take读4字，末字后RELEASE。输出的逻辑类型是S64，不伪装成八S16。

一份literal整数向量为A=`[1,-2,3,-4,5,-6,7,-8]`，B第n列的8个值均为n+1，预期结果=`[-4,-8,-12,-16,-20,-24,-28,-32]`。四个128bit结果字的低/高64分别对应相邻两列，S与T仅保存和交付同样的位模式。

```text
S初始化并逐笔消费写ACK
→ S loader A/B真实握手并排空done
→ M EXEC应答，检查故障行mask
→ M op3读4字，逐字写S并消费ACK
→ T BEGIN4/顺序写/COMMIT
→ 消费4字，核对index/last与位模式
→ RELEASE，允许下一轮重用
```

P1仅产生这条链的输入和预期。S_macro本身没有实例化M，母子控制器及这些箭头上的跨宏胶合尚未编码或仿真。P2应据此实现唯一端口所有者、S helper、M结果过滤/保持和T批次控制，再接受随机背压、尾部、错误、取消和重复运行的RTL证据。

## 4. 不可混淆的同步事实

loader done只表示装载交付完毕，不代表M已执行；M EXEC成功应答不是结果张量。S写也产生应答，必须消费；S busy不表示普通端口全空。T末字take之后仍需release，提前BEGIN/COMMIT等行为按原生ready/错误逻辑判断，不能把所有不握手都当native报错。

N统计/原score回放求EXP（op3）与EXP回放求概率（op6）分开；BEGIN不自动清TopK上下文。E/G没有有效数输入，尾部由外侧控制。R身份位域在OPEN/EXEC/COMMIT中不同，局部COMMIT前先保存输出；op7接受后COPY窗口不接新命令，op8不能中断或回滚已经提交的active/history/epoch。R op8 REVOKE没有原生身份比较，不能当系统权限检查或自动回滚。

多个普通输出即使valid互斥也不能短接。所有所需MUX、保持、控制器、数值运算及有源中继仍需在共同M1–M10底座冻结前实现；M11/M12永久选择已有路径与程序。系统有外存，但本轮不研究其具体接口/带宽/调度，也不把P0容量不足当永久不支持。

## 5. 交付与下一阶段门

P1完成的是版本/接口合同及P2测试输入的准备。它不等于独立审查、PR合并或硬件冻结；路线中的P1最终接收仍需要求的审查。P2开始前应读回当前ref和本合同，确认没有未经登记的源漂移，按验证矩阵明确范围和证据保存位置。

正式运行与检查命令维护于[ARCHITECTURE](ARCHITECTURE.md)，实际回执为work/Melodydt/151/phase1-checks.json及phase1-verification.json。未执行RTL/SystemC、模型推理、服务器或EDA；无作业号，不宣称后台监测。审查人待指定，Issue交付保持in_review而非done；登记和看板缺项分别在PR及交接回执。
