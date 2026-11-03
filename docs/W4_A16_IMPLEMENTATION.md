# 主线四A16有界完整因果Attention实现

Issue151 / PR152；Melodydt；2026-11-02 Asia/Shanghai。输入f665230a，实际通过源码a32e5f1a61d137e9e2338b7717b66d5c18085351。新增H8、Sq=Sk2、head1、无bias/cache的有限整数A_plain流程，保留原A8/F16和所有既有源。

## 实现及工作原理

实际链为preRMSNorm→Q/K/V→Q/K RoPE→K/V布局转换→QK/缩放→因果前缀Softmax→PV→Wo→原始S16残差。输入27拍含两行S16Fin10 hidden、四份S8Fin7权重、S16Fin10 gamma及两行S16Fin14 adjacent-pair旋转系数；实际432B=336B有效+96B真实零填充。host可变数据不改变固定局部执行程序。

复用M1/N1/E1/S1/T1，G/R未实例化。local FSM唯一拥有普通S接口，服务的目的写ACK及响应消费完成后才移交owner；M单context按阶段复用，保存两行结果的真实写ACK后才能clear/加载下一矩阵。N先对两行做RMS，后以count1/count2分别归一化因果前缀；未来列即使计算了score也不进入第0行Softmax。不能用补零score替代mask。

S中K为n-major的8列S16容器：K0/K1及6列真实零；V为8个通道列，每列[V0[h],V1[h],0…0]。新增local双128bit holding及有限lane selector完成真实读写/转置，这是必须预制的有源逻辑。两行最终值写入T的两个字并COMMIT；每字分别握手，最后一字take及实际RELEASE之后才正常DONE。

数值为明确新profile：QKV/Wo A16Fin10×B8Fin7经RNE7；RoPE由E9执行成对复乘、RNE14；QK的Fin20累加乘11585，经RNE25得到scoreFin10；N输出P Fin14，PV经RNE14回Fin10，再和原X做S16饱和加法。各阶段饱和汇总到done_saturated，协议/原生错误汇总到done_error；已接受写或输出前缀不可回滚。

正常任务实测scoreboard核对103普通S事务（73W/30R）、42M命令、6loader/14宽读、12Abeat/8Bbeat、4N服务/20N命令、6E服务及2T字。预约S448..529包络82字1312B，T32B；实际触及69个S字。未触及孔洞仍不承诺免费并发共享。S16KiB/T6KiB原宏尺寸未缩减，预约字节不是面积或额外RAM单元数。

## 实际验证及证据

job95235在node1/c64/8CPU、Verilator5.042运行，Slurm COMPLETED0:0，build/sim均exit0，首次实际仿真30个预声明CASE各一次、最终PASS_W4_A16 cases=30。10组独立数学golden逐普通S写/读、M数据、N/E请求/返回、loader布局和两输出核对；不同阶段写入同地址按写历史匹配，未从DUT结果生成期望。

因果反例将未来token改变，第0行输出保持、第1行改变；零gamma时两行输出精确保留各自原始S16残差。另覆盖真实位置0/1非identity RoPE及quarter-turn、signedgamma、稀疏/随机、饱和、最终输入ACK门、N/M/loader/E返回背压、两输出间abort、DONE保持、reset与native N/QK/Wo/RoPE/residual及S helper错误恢复。S helper错误为边界注入，不冒称原生S存在error输出。

保留36警告：12TIMESCALEMOD、2既有T数组索引WIDTHTRUNC、22测试台WIDTHEXPAND；只-Wno-fatal，不屏蔽类别，非lintclean。全套统计Sreq3799/Sack3796、Mcmd1456/Mrsp1455跨越协调取消/复位，不能代替正常单任务守恒检查；三个S返回和一个保持的M返回由测试取消，正常任务仍按103/42分别核验。

工具为Verilator5.042/g++11.4.0/Make4.3/Python3.10.12；容器SHA c742bf99ea498fb4da5135bc83fd1677abcebe0e64470e6a115f2baecb3905df。23输入在计算节点及导出时再次SHA核对，12文本证据/下载archive SHA核对。原始[结果回执](../work/Melodydt/151/a16-rtl-evidence/runs/r01/results/run-receipt.json)、[模拟日志](../work/Melodydt/151/a16-rtl-evidence/runs/r01/logs/simulate-a16.log)、[SHA索引](../work/Melodydt/151/a16-rtl-evidence/evidence-manifest.json)完整保留；build及二进制留本人服务器目录。归档助手曾因Path拼接失败，修复后在新c02导出，未重跑或修改仿真输入/结果，c01记录保留。

## 未接收范围及下一步

这是完整有界计算流程的RTL证据。真实样本的H、head/GQA、Q/K或postNorm、split-half RoPE/位置/cache、epsilon、训练权重的量化质量、超片上容量及参数供给尚未接收；不能把样本缩到8维后宣称真实模型已映射。adjacent-pair系数输入不是自动转换任意模型RoPE布局。

还没有A16→F16真实跨岛连线/目的storedACK；A16两字输出也不能直接当F16的17拍参数混合帧。当前仍L4，后续须按样本明确A/F入口、数值/参数和有界形状/存储准入，再以L5实现端点/母控/源释放；共同底座与M11/M12物理资格另验。本轮没有外存控制器，保留后续供参能力。

细节见[数值合同](W4_A16_NUMERIC_CONTRACT.md)、[独立源码/样本边界](A16_SOURCE_MODEL_REVIEW.md)、[A/F实施路线](AF_NUMERIC_STORAGE_PLAN.md)。

## 结构设计阶段记录

下述是RTL作者的源审阅/实现记录，其未执行仿真的措辞说明作者分工；当前实际结果以本报告及服务器回执为准。

# W4 A16 有界 Attention 实现草稿

Issue151 / PR152；研究输入 `f665230a392cbcf2422594167e1f163d5e5d1c80`；原生叶源沿用 `707878621b2add4ed218b8c43df2e95c9a56e2ba`。依据本轮冻结 `A16_PLAN.md` 新增 `block_w4_a16_top.sv`，旧 F16/F8/A8、N/E controller、S helper 和所有原生叶宏保持只读。

状态：实现及源静态审阅草稿，待真实服务器编译/仿真。本作者未编译或运行本地RTL仿真；文本检查不替代编译，尤其不能用它推断词法合法或功能通过。

## 1. 本次实际组合

固定 H8、Sq=Sk=2、head1、无bias/无cache的 A_plain causal prefill：原始 S16 X → 逐行 RMSNorm → Q/K/V → Q/K RoPE → scaled QK → 两个前缀 Softmax → PV → Wo → 原始 X 残差。顶层实际实例 M/N/E/S/T 各1，G/R0；M6个服务、N4个服务、E6个服务全部顺序复用，普通S只有一个helper及一个owner。

所有跨stage数据均经S保存并真实消费写ACK；不存在裸接N→M、E→M或一般宏间全互连。新增有限FSM、输出保持和V转置选择逻辑是有源电路，必须预制，不是M11/M12金属自动产生的bridge。

外部信号沿 F16：19个信号、282逻辑bit；in_valid/ready/data128，input_stored，start_valid/ready，busy，done_valid/ready/error/saturated，out_valid/ready/data128/index10/last，clk/reset/abort。端口宽度相同不代表帧相同；A16为27拍输入与两拍输出。

## 2. 固定入口、真实padding及存储生存期

input_index5bit，beat i 实际写 S(448+i)，i=0..26；每次请求和原生S写ACK各一次，最后一个ACK消费后才建立frame_stored。

| beat | 内容 | S普通字地址 |
| --- | --- | --- |
| 0 / 4 | X0 / X1，各8S16 Fin10 | 448 / 452 |
| 1..3 / 5..7 | 硬件实际zero，不信任host值 | 449..451 / 453..455 |
| 8..11 /12..15 /16..19 /20..23 | Wq/Wk/Wv/Wo，各64S8 Fin7，n-major | 456..471 |
| 24 | gamma，8S16 Fin10，真实可变 | 472 |
| 25 /26 | 两个token的RoPE系数，各8S16 Fin14 | 473 /474 |

432B传输=336B有效+96B实际padding。系数为相邻pair交错 `[cos0,sin0,cos1,sin1,...]`，不是未经转换的split-half模型布局。原始X448/452及各自padding整个RUN保持，不被Norm覆盖；最终残差直接使用它们，不做S8降宽或移位补偿。

RUN先顺序实际写零482/483、518/519、522/523六字，分别是Norm、P、context的rows2 A容器padding。Norm480/481，Q488/489，K490/491，V492/493；K staging496..503，V transpose504..511；score512/513，raw EXP514/515，P516/517，context520/521，Wo524/525，最终528/529。

本候选按448..529包络预约82字=1312B，T两字32B。包络中的hole不被自动回收或分给其他并发任务。S/T仍分别属于16KiB/6KiB宏，不是共享容量；此数字不接受完整产品shape、KV缓存或外存供给。

## 3. 真实服务、描述符与数值

| projection | 两行服务 | A base / B base | EXEC / factor / op5 read |
| --- | --- | --- | --- |
| 0/1/2 | Q/K/V | 480 /456、460、464 | 0x11885 /1 /0x107 |
| 3 | scaled QK | 488 /496 | 0x11887 /11585 /0x119 |
| 4 | PV | 516 /504 | 0x11887 /1 /0x10e |
| 5 | Wo | 520 /468 | 0x11885 /1 /0x107 |

全部rows2、tiles1、K8/N8、A16；0x11885为B8，0x11887为B16。每服务CLEAR6→SCALE4→loader→EXEC10→READ5索引0/1/8/9，依次取row0/row1两half；两次响应各四个S32槽，拼接各槽低16成完整一行。row0实际S保存ACK后才读取row1，row1保存ACK后才进入下一服务。ACK/status与read payload继续分相位处理，不能把EXEC返回当张量。

Norm为mode1/count8/epsilon_code1，两个服务src448/452、gamma472、dst480/481；gamma Fin10，X Fin10时epsilon_real=2^-20。QKV/Wo的 S16Fin10×S8Fin7 用factor1和RNE7返回S16Fin10。QK的S16Fin10×S16Fin10先乘近似1/sqrt8的Fin15常量11585，RNE25返回score Fin10；PV的P Fin14×V Fin10用RNE14返回Fin10。各阶段保持原生饱和语义，不将这些单位替换成FP32质量结论。

E stage0..3分别旋转Q0/Q1/K0/K1：op9/shift14/count8，srcA488..491、srcB473/474按token选择、dst原地覆盖。controller完整读A/B后才发native并写目的，允许这里有限原地操作；全写ACK及服务rsp消费后才释放owner。E stage4/5用op0/shift0，读524/525与原X448/452，写528/529。RoPE与残差clip均保留saturation。

Softmax两服务真正使用count1和count2，score分别512/513，raw EXP514/515，P516/517；前者只允许第0个key，后者允许第0..1个key。统计、EXP回放及概率回放都由真实count约束，controller把tail置零；不是给8lane未来score填0来模拟mask。原始EXP按U16原位保存，概率为非负S16 Fin14，不能混为同格式。

## 4. K/V staging 的实际逻辑

K：唯一普通S owner顺序读旋后的490/491，分别写496/497；随后六次真实写零498..503。B16 n-major矩阵的column0/1分别是完整K0/K1向量，其余column真zero。QK的A488..491宽容器虽然也读入后两字K，但loader rows2只退休Q0/Q1，后两字不冒充padding或另加有效row。

V：读492/493进入 `v_hold0/v_hold1` 两个128bit holding；`transpose_v_column` 用lane选择生成列h：低16为V0[h]、次16为V1[h]、其余96bit为真zero。8次真实写504..511，每次等实际ACK再推进 `v_column_index`。第0列用当前第二个读响应和已保存row0生成，避免nonblocking赋值读取旧row1；第1..7列用两个已锁存holding。没有依赖软件离线伪造转置结果。

6次loader共14次512bit宽口读：A每服务一个容器共6读，B8四服务共4读，B16两服务各2读共4读。退休A共12个128bit row，B共8个512bit beat（B16带0/1half）。这些宽口读不计入普通S103次事务。

## 5. 正常成功路径计数

| 阶段 | 普通S写 | 普通S读 |
| --- | ---: | ---: |
| 入口27拍 | 27 | 0 |
| Norm/P/context容器padding | 6 | 0 |
| 两次RMS服务 | 2 | 6 |
| Q/K/V两行结果保存 | 6 | 0 |
| 四次RoPE | 4 | 8 |
| K复制及zero | 8 | 2 |
| V读出及转置保存 | 8 | 2 |
| QK两行保存 | 2 | 0 |
| 两次前缀Softmax | 4 | 6 |
| PV两行保存 | 2 | 0 |
| Wo两行保存 | 2 | 0 |
| 两次残差相加 | 2 | 4 |
| 两个最终结果读入T holding | 0 | 2 |
| **合计** | **73** | **30** |

因此正常路径103个普通S请求/真实ACK/helper响应。M为6×7=42条cmd/rsp，6次loader。N为RMS2×[0,1,2,5]加Softmax2×[0,1,2,3,4,6]，共20条native cmd/rsp、4个service，原计划预计16已由根任务纠正。E6个service/native请求/响应。T一BEGIN2、两WRITE、一次COMMIT、两次输出take、一次RELEASE。上述是源码意图的期望计数，故障/reset场景不强求守恒，也不是已测统计。

## 6. 控制、背压与失败

LOCAL0、E1、N3共享唯一普通S helper；E/N从service请求到最终写ACK和rsp消费保持owner，叶宏loader在独立M加载阶段运行。任何held req/rsp的内容不能因下游背压改变。所有permit_s_req/rsp、permit_m_cmd/rsp、permit_load、permit_e_req/rsp、permit_n_req/rsp仅供有限TB观察/故障注入，不是host配置。

主state沿F16编号；projection0..5如上，m_phase0clear/1scale/2exec/3..6四read。n_stage0RMS0/1RMS1/2SM1/3SM2；e_stage0..3RoPE/4..5残差。local_tag0INIT/1MSAVE/2KREAD0/3KWRITE0/4KREAD1/5KWRITE1/6KZERO/7VREAD0/8VREAD1/9VWRITE/10FINALREAD0/11FINALREAD1。

最后两次S读分别保留到 `final0` 和 `held_data`，真实T BEGIN2后用t_write_slot写index0/1，完整COMMIT后才DRAIN。输出index0,last0和index1,last1，T持有背压输出，实际RELEASE接受后才正常DONE。两个V holding256bit、两个最终输出holding256bit、M半行64bit都是显式数据存储；不能称布局转换无硬件或把它们直接当综合FF/PPA。

reset为高有效协调复位，不保证S/T RAM清零；每帧通过实际ACK重建有效性。prestart abort丢帧无DONE；RUN abort/internal错误协调reset叶/helper/controller并形成保持的error完成；既有DONE不被abort撤回，同拍ready仅消费一次。阶段saturation OR累计，与error分开；N错误poison由协调reset清除后才能复用。已写S及已消费输出前缀不可回滚，done_error没有partial/原因/输出进度字段。

本地out_ready、out_last和DONE都不是跨岛stored ACK。未实现芯片母控或L5端点，未接受完整模型、一般形状、多head、KV缓存、外存、质量或PPA。提交/真实仿真归根任务，必须绑定实际源码SHA与服务器回执。
