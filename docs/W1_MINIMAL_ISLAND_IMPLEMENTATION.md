# 主线二首切片：固定DOT8、可变输入的共同岛壳RTL

Issue151 / PR152，负责人Melodydt。研究输入bfe62ad179af72aef591622aa5c7a000f5d8b681，原生叶源707878621b2add4ed218b8c43df2e95c9a56e2ba。本轮由W0候选合同进入实际RTL，实现W1_FIXED_DOT8_VARIABLE_TENSOR的有限首切片。它是共同岛壳的起点，不等于完整W1通用端点、完整六配置、芯片母控或物理大宏已经完成。

## 1. 实际新增与复用

| 文件/模块 | 本轮作用 |
|---|---|
| project/rtl/block_connection_w1/block_w1_mst_top.sv | 新入口、frame完整标记、唯一S访问选择、固定MST服务FSM及输出/错误/复位生命周期 |
| project/rtl/block_connection_w1/block_w1_mother_rom.sv | 新21×16bit固定SERVICE/WAIT/END本地顺序器，slot2为INPUT_CHECK，替代字面量S_INIT |
| project/tb/block_connection_w1/block_w1_mst_tb.sv | 独立整数oracle、五向量、真实端口/ACK/退休监测和28个有界检查标记 |
| work/Melodydt/151/run_w1_mst.py | 本地ModelSim运行器；固定14源校验、独立快照/新输出目录、工具/配置/输入/日志SHA与失败回执 |

现有block_p2_s_ctrl、block_feed_s_macro/storage/loader、block_v2_m和transaction6k复用原字节；P2三RTL/两TB及14核心源没有修改。新的ROM名字含mother，但这里承担岛内本地调度，不能把它称为芯片级母控。适配/holding/入口MUX写在新top及既有helper中，没有新增独立bridge硬宏，也没有裁剪原生端口/op。

固定程序仍为M_CLEAR→M_SCALE→INPUT_CHECK→LOAD→M_EXEC→M_STORE→T_BEGIN→T_FILL→T_COMMIT→T_DRAIN，每项SERVICE接单后WAIT真正应答，最后END。输入写入发生在start之前，RUN不再重写literal A/B。所有这些有源逻辑均为预制候选逻辑，M11/M12只可连接/永久选择已存在能力。

## 2. 对外接口和数据布局

| 接口 | 含义 |
|---|---|
| in_valid / in_ready / in_data[127:0] | 一帧8个按序128bit整字；每次只保留一个未完成入口写，ready低时源保持数据 |
| input_stored | 当前帧8次输入接受和8个实际S写ACK全部完成；RUN期间仍绑定当前帧，不表示可以再次start |
| start_valid / start_ready | 完整帧且本地生命周期安全时接单；早到脉冲不排队，持续valid可在ready后接受一次 |
| busy | 从首个输入被接受起覆盖partial/full-prestart/RUN/DONE，直到done消费或相应reset/abort |
| out_valid / out_ready / out_data[127:0] / out_index[9:0] / out_last | 四个按序S64-pair字；下游停顿时data/index/last保持；out_last只标此固定输出片段末字 |
| done_valid / done_ready / done_error | 完成保持到消费；正常成功必须实际输出take并T RELEASE，错误走明确终态 |
| reset / abort | 同步生命周期操作，硬reset与RUN abort、prestart abort、已有DONE abort分别处理 |

当前没有输入opcode/address/shape/scale/header加载口：只输入tensor数据，程序与几何固定。S8×S8、row1/tile1/K8/N8、bank0、factor1、left0、EXEC op10/index0/data0x9884。输出采用op3 raw S64，未实现op5量化出口或向N/G/R的格式转换。

输入beat0..3实际写S448..451（A保留区64B）；beat0低64为8个S8，其高64和beat1..3由硬件置零并实际写入。beat4..7写S452..455（B64B），B[n,k]按8*n+k字节顺序。有效A8+B64=72B，传输128B，其中56B为canonical padding。结果写S456..459，p包低64为dot[2p]、高64为dot[2p+1]，T使用4字64B。

独立数学参考为dot[n]=Σk signedS8(A[k])×signedS8(B[8*n+k])，精确范围[-130048,131072]；该固定整数profile不需要舍入且数学结果不可能S64溢出。首例[-4,-8,-12,-16,-20,-24,-28,-32]仅是五输入之一，不再是硬件内置输出。

## 3. 控制如何真正起作用

```text
空闲/收输入 → 捕获一字并canonicalize → helper发S写 → 等真实写ACK
    ↑                              第1..7字回到收输入
    └─────────────── 第8ACK后 input_stored ───────────────┐
                                                        ↓
                       接受start → 固定ROM+本地服务FSM
                       M清理/scale ACK → INPUT_CHECK
                       loader完成 → EXEC状态检查
                       四包op3 → 每包写S并等ACK
                       S回读 → T填充/commit → 输出take
                       T RELEASE → END/DONE保持 → 消费后新帧
```

入口与RUN都通过同一个S helper；其他逻辑不直接并驱S。共享held_data只在其所属事务结束后复用，helper捕获请求并持有响应，正常每次读/写均恰好一个ACK。最后输入握手本身不会使input_stored有效，须等其native写ACK经helper真正返回并消费。RUN没有S448..455写入，测试监测此点以发现literal覆盖。

M配置/清理ACK、EXEC状态与op3结果分流；只有M_STORE的成功payload进入结果写S。loader done不当作计算完成。T最后一次输出take后仍须RELEASE，再关闭服务/程序，不能仅见out_last就报任务成功。done未消费时不接新输入；done消费同拍也不接下一帧，下一周期按全新8字重建输入完整性。

## 4. reset、abort与错误

- prestart的partial/full frame遇abort：清frame标记/计数，不制造尚未接受RUN的任务完成；重新从beat0收8字。
- 已接受RUN遇abort：协调reset本地child/helper/leaf，ROM产生一次保留error完成。已经被接收的S写或外部输出前缀不回滚。
- 已有DONE遇abort：保留原done_error；若done_ready同拍为1，公开完成握手计一次并退出DONE，不重复产生完成。
- hard reset：清控制、有效性和完成，不制造error完成；S RAM内容不保证清零，下一帧必须重写全部保留输入区。
- 原生EXEC错误：检查rsp_error/fault_rows，停止后续结果发布，进入error完成；实际注入非法描述符并用新帧验证恢复。普通S无原生error pin，helper的rsp_error=0不提供额外存储故障检测。

这不是无reset取消/排空或全局原子回滚。多任务、跨时钟、跨岛/MEM晚响应与R状态发布仍为后续合同。

## 5. 本轮真实验证与失败记录

实际使用已有本地ModelSim SE-64 2020.4。沙箱内版本查询因Windows DLL重定位不能启动；经授权在沙箱外运行同一已安装工具成功，未安装工具或查看license/凭据配置。运行器只读任务声明源并写全新任务输出目录。服务器没有创建目录、上传文件或启动作业。

| 运行 | 实际结果 | 解释 |
|---|---|---|
| regression-r01 | helper6＋MST13，共19 CASE_PASS | 原P2当前字节真实重跑通过；范围仍仅原fixture |
| w1-r01 | compile exit2 | 新top首次引用leaf_reset/service_rsp_valid早于声明，日志保留；修复声明顺序，未修改功能逻辑 |
| w1-r02 | compile/sim exit0，28 CASE_PASS，4422周期 | 首版计数测试通过；独立review随后发现同拍DONE+abort计数需补强 |
| w1-r03 | compile/sim exit0，28 CASE_PASS，4422周期 | 最终TB公开DONE握手仅受hard reset屏蔽，所有finish严格检查+1，并补partial/full-prestart busy；最终源SHA与此运行一致 |

28是检查标记数，不等于28个独立完整任务：部分标记检查同一任务的不同条件，恢复流程还会运行额外完整帧。验证五向量、脏RAM/padding、最后ACK前禁止启动、早脉冲与持续start、入口/输出/DONE停顿、两帧不同数据、分阶段计数、partial/pendingACK/full未RUN/RUN/prefix/DONE的abort/reset与恢复，以及真实原生EXEC错误。

正常完整frame的每次nominal_counts分别检查：入口8写/8ACK；RUN4结果写＋4回读/8ACK；合计16 S请求/16ACK；7 M命令/7应答、一次loader/A/B、T BEGIN1/FILL4/COMMIT1/TAKE4/RELEASE1。全程含主动中断，不能写成全局无条件守恒：inputAccept240-ingressReq239=1次native前capture后abort；ingressReq239-ACK237=两次输入pending ACK分别abort/reset；resultReq97-ACK96=一次RUN结果pending ACK abort；Mcmd176-Mrsp175=一次pending响应hard reset；readReq96=readACK96。Ttake92含已消费的部分前缀。

所有14核心文件参与语法编译，不因W1/P2运行而授予N/E/G/R功能组合或物理资格。测试为有限定向场景，含明确TB-only force（固定许可线及一次非法EXEC）；不当作所有边界随机反压、形式活性或全操作/全参数通过。

## 6. 主线二状态与未完成项

当前交付仅W1有界最小岛壳切片，待独立PR审查/合并；W0外部设计审查仍待完成。原P2全部剩余门没有整体关闭，主线三及后续未开始。下一层需要通用形状/slot/分片、各端点gather/serializer和N/R phase、跨岛stored ACK、NUM/MEM及完整产品程序/资源/数值/物理；本轮没有用DOT8代替这些要求。

新wrapper输出到外部ready/valid sink，不代表已经有另一个大Block的输入存储ACK。全系统命令/事件编码仍是候选，此切片没有实现通用64bit任务包、运行时程序装载、完整芯片母控或独立bridge硬宏。七宏原生接口/op未裁剪，同一预制底座多模型能力并集与物理冻结仍需后续验证。

正式验证日志、源/工具/配置/输入/输出SHA与覆盖索引在work/Melodydt/151/w1-rtl-evidence/及w1-verification.json；复算命令见ARCHITECTURE。分支上传、审查、登记和看板以本轮PR读回回执为准，不把本地通过或PR创建等同于已合并/验收。


## 7. 证据入口

- [测试覆盖与限制](W1_MINIMAL_ISLAND_VERIFICATION.md)、[独立源码/执行证据审阅](W1_MINIMAL_ISLAND_REVIEW.md)。代理审阅不替代项目要求的外部PR审查。
- work/Melodydt/151/w1-execution-index.json与w1-rtl-evidence/保存四次真实运行、失败/先前TB源差异、工具/配置/输入/日志SHA；w1-verification.json重新核验源与日志。
- w1-index.json给当前首切片与八主线实际状态；w1-checks.json记录本轮管理/静态命令及准确源/产物SHA。旧w0-index及phase1/phase2回执是原生成时刻记录，本轮不改写其历史状态；当前进展以w1-index和PR回执为准。
