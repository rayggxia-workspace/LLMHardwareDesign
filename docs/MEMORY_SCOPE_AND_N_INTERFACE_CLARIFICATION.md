# 外存研究边界与N宏接口澄清

日期：2026-11-01 Asia/Shanghai。Issue151 / PR152；负责人Melodydt。输入研究提交86d564850d8f539934a6356e3a26c4dfbab65657；N源码继续固定643c6012a11cbf461146ac40fbf61485223fe946。本文修正此前将“暂不考虑外存”扩大为架构禁止的表述，不修改七宏RTL。

## 1. 系统有外存；当前研究先聚焦宏间连接

用户已明确系统有外存，本阶段暂不开展其接口、容量、带宽及调度研究，保留后续接入灵活性。当前片上验证profile命名为P0；onchip-contract.json中external_memory_enabled=false、DMA_enabled=false、EXT credit=0/valid=0，以及family-spec中的external_memory_assumed=false，均只约束P0评估。旧检查中的REJECT_EXTERNAL_OR_SPILL表示该请求超出P0评估范围，不是产品禁止外存。

已有片上容量计算仍有效：S计算区9KiB、T批次spool、loader capture等描述的是声明调度下的局部缓冲需求。GAP_ONCHIP_WEIGHTS/KV/STATE说明P0放不下；完整系统可在后续研究外存驻留和搬运，不能据这些缺口要求所有权重/KV/state永久片上，也不能直接宣称外存已解决带宽或容量。

保留的扩展边界：

- 数据handle继续用region/instance/base/length和类型/尺度/布局/版本描述存储，避免把所有地址永久绑定为S的10bit字地址。现有region保留编码在P0仍拒绝，待外存接口版本定义后分配；外存地址宽度可用版本化描述符或映射间接层，当前不冻结具体位宽或控制器。
- 后续在明确MEM服务后增加外存控制器/PHY、搬运、缓冲、credits、带宽及错误处理；这些未计入当前十服务及32KiB控制预算，不是新增硬件已存在。
- 继续保持数据类型与lineage。DATA_READY必须等待实际传输完成并满足可见性，未来补齐排序/一致性/错误语义；母控管理依赖，数据大载荷不必经过母控。
- M1–M10冻结前必须确定并预制需要的有源接口、缓冲及控制逻辑。仅靠M11/M12不能在冻结后生成新的PHY或DMA；当前保留的是设计扩展边界，不是保证任意未来外存都可无代价接入。

## 2. N是一个顶层宏，命令决定当前操作

源码见[block_v2_n.sv](../project/rtl/block_v2/block_v2_n.sv)及[内部group](../project/rtl/block_v2/block_v2_n_group.sv)，详细命令见[N原生审计](rtl-contracts/NEG_NATIVE.md)。

顶层只有一个block_v2_n，cmd_op为4bit；BEGIN(op0)的cmd_param=0/1/2分别选择Softmax/RMS/L2上下文。内部显式实例化一个block_v2_n_group，提供共享U64除法/平方根；EXP用include函数表；TopK有40项score/id数组。普通统计/归一化和TopK保留不同状态，但命令经同一phase状态机执行、共用应答端口，不是各有可独立对外调用的Softmax/Norm/TopK宏。

## 3. 应答总线统一128bit，载荷格式由命令决定

所有应答共用rsp_valid/rsp_ready、rsp_data[127:0]、rsp_error/rsp_saturated。

| 命令 | rsp_data含义 |
| --- | --- |
| op3 EXP | 低count个U16，UQ1.15；raw32768代表+1.0 |
| op5 NORM_REPLAY | 低count个S16；尺度按gamma及调用合同解释 |
| op6 SOFT_REPLAY | 低count个非负S16 Q1.14概率，raw范围0..16384 |
| op7 READ_STATS | [15:0]count、[31:16]max、[47:32]min、[79:48]sum、[127:80]sumsq |
| op10 TOP_SELECT | 低k个U16 ID，不返回score，其余零 |
| op11 READ_FACTOR | 低32bit U32 factor，高96bit零 |
| op0/1/2/4/8/9正常成功 | 零载荷ACK；不是新输出向量 |

因此“统一接口”表示统一运输与握手，不表示所有载荷都是八个S16。rsp本身不携带op/count/type，外侧N_CTRL须保留已接受命令、有效数、类型与上下文来解释输出。

## 4. 例子与并行边界

同一N执行一行Softmax时，依次BEGIN(mode0)→分块STATS→FINALIZE→回放原分数做EXP→FINISH_EXP→回放EXP做SOFT_REPLAY。EXP与概率均从同一个128bit口返回，但前者是UQ1.15中间量，后者是非负S16 Q1.14最终概率。原分数和EXP由外侧保存/回放，N没有自动读取S或外存的端口。

以后供数服务可以从片上或外存取得数据，再送cmd_data/cmd_aux，无须据此将N拆成多个功能宏。单个N按命令串行执行；若要多行/多任务独立并行，需额外N实例或另设计多上下文架构，并付出真实资源成本。TopK可在原生IDLE时与普通上下文命令交错，但不能推导任意并发；外侧lease仍须保护上下文。

本次仅作边界和源码说明；未新增RTL、外存控制器或运行仿真/推理/EDA。既有源指纹及本轮静态检查见work/Melodydt/151下memory-scope-checks/verification回执，上传commit/读回与CI以PR152最新回执为准。
