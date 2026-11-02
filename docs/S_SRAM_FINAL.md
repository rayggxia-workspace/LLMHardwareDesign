# 独立 SRAM S：整块最终结果

2026-11-02（Asia/Shanghai），[Issue #155](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/155) / [PR #158](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/158)，执行账号 YUZE-LU。

整个四银行 S 已完成综合、PG、放置、CTS、详细布线、RCX、完整原版 GDS DRC、独立 300MHz 审计、最终网表实际模型功能回归与严格银行边界等价。`qualification-002/acceptance.json` 的 `engineering_acceptance=true`、`review_acceptance=false`。这是下述模型边界内的工程验收；独立审查、合并及银行内部 PEX 尚未完成。

## 固定规格与状态归属

| 项目 | 最终实现 |
| --- | --- |
| 顶层 | `block_feed_s_macro_sram`，独立可选实现；原标准单元 S 及其已验收文件保持不变 |
| 有效工作存储 | 4×256×128bit、单 1RW，合计 16KiB；真实 FreePDK45 银行 |
| 普通口 | 128bit，bank=`addr[1:0]`、row=`addr[9:2]`；写应答返回接受的数据 |
| 宽口 | 512bit 读，拼接顺序 `{bank3,bank2,bank1,bank0}` |
| 仲裁 | 每拍接受普通或宽操作之一；仅实际接受的宽请求优先，不因宽响应背压永久占用普通口 |
| 状态位置 | SRAM 保存 payload；S 内标准单元保存两通道响应队列、在途预留、写应答数据、选择/计数及原 feeder 描述符、A/B 队列 |
| 有限缓冲 | 普通/宽响应各两槽（含在途）；响应数据 160B，原 feeder A 队列 128B、B 槽 64B，加有限元数据；没有额外 16KiB 隐藏副本 |
| 延迟 | K 上升沿接受，随后下降沿 SRAM 操作，K+1 上升沿寄存返回，最早 K+2 消费；相对标准单元 S 增加一级返回寄存，填满后可每拍接受读请求 |
| 复位 | 同步放弃在途/排队响应及命令，复位期间抑制握手；不清 SRAM、不撤销已完成写入 |
| 固定物理边界 | 1030×1030µm，M1–M10，M10 外部接点；银行各 418.655×220.855µm |

接口与时序详见 [实验说明](../project/experiments/s_sram/README.md)。供数器源不改；它按 `mem_valid` 等待实际返回。没有默认为旧响应延迟不变，也没有在宏外隐藏状态或延迟补偿。

## 实际最终验收

| 验收 | 绑定当前整块 033 的结果 |
| --- | --- |
| 全流程 | 95227，fresh synth → floorplan → place → CTS → route → finish/RCX → GDS，COMPLETED/0 |
| 完整 GDS DRC | 原始未删规则 FreePDK45 deck，完整 FEOL/BEOL/OFFGRID/ANTENNA，**0 items** |
| 原生完整布线 DRC | 独立最终 ODB 检查 **0**，检查前后 DEF SHA 相同 |
| 300MHz setup / hold | 最差 **+0.097132ns / +0.007969ns**；原生 setup/hold 违规计数均 0 |
| 电容 | 0 违规；最差 6.610626221fF ≤ 6.691200256fF，裕量 +0.080574006fF |
| slew / fanout | 均 0 违规；最差 slew 裕量 +0.096960604ns，fanout 裕量 +3 |
| 银行时钟 | 4 个周期、4 个高脉宽、4 个低脉宽检查通过，所有银行为传播后的 core 时钟 |
| RC 覆盖 | 所有 native unannotated driver 解析至实际 flat fanout；0 partial、0 connected/unresolved 缺 RC；3366 个未用驱动无连接负载，保留清单 |
| PG / 连通 / pin | 227706 个 PG ITerm、0 错误 PG、VDD/VSS 连通；0 未放置、0 开路信号输入；M10 接点合同及 177 个非时钟输入/788 个输出预算检查通过 |
| 最终实际功能 | 95229，直接由当前 ODB 导出全信号网表，实际生成银行默认 DELAY=3ns/T_HOLD=1ns 不改；三初态各 54370 检查、9448 周期、257 命令，通过 |
| 严格形式 | 95230，对四个银行全部真实 pin 边界作独立符号切分；6726 common inputs、7380 common outputs，正例 UNSAT/identical，地址位反相负例被拒绝 |
| 严格汇合 | 95233，重新核对所有回执/日志/输入源/六文件 SHA 及正负控制，PASS |

所有时序、电气、RC、PG、布局与功能结果均来自 033；不借用旧 024/026/029/030/032 的单项通过。独立审计与实际功能在最终产物依赖满足后并行运行，形式证明亦独立运行。

约束保持：周期 3.3333333333333335ns、不确定性 0.1ns、时钟转换 0.05ns，输入/输出 max0.8ns/min0.2ns，BUF_X2/Z 驱动，50fF 输出负载；不新增 false/multicycle 或数值 slack 容差。native `6_final.sdc` 以四位小数输出 3.3333ns，原件不改；交付同时保留验收使用的精确 `implementation/input.sdc` 及同工具高精度读回/错误约束负例。

## 真实银行与修复依据

选定 WPR2/control25 的 generate-012：95065 完成真实生成、ngspice 原生搜索、setup/hold、泄漏和全部九点表征（3 负载×3 转换；周期 2.916666666666667ns），95078 默认生成模型三初态回归，95077 同源接点 ECO 原版完整 DRC=0、晶体管 LVS match。95147 汇合实际匹配 V/LEF/GDS/SPICE/Lib；不复用另一尺寸/时序版本。完整历史源及绑定见 [continuation-015](../work/YUZE-LU/155/continuation-015/README.md)、[continuation-017](../work/YUZE-LU/155/continuation-017/README.md)。

旧候选完整 DRC/电气/hold 失败均保留，修复包括：

- 从实际银行 GDS 提取 M3/M4 遮挡，保守 pin 窗口、原生 access 读回；每银行 267 个接点在父级实际同网加入补片，4×267，补片进入正常 RCX。复合 routing LEF 只描述必须存在的父级落点，不能作为独立原始银行 LEF 使用。最终 DEF 的全部接点/网络匹配、缺矩形及错误网负例均保留。
- 输出首级使用真实 CLKBUF_X1、小型局部固定连接；控制缓冲允许正常修复。`load_reuse_b` 两级、`din[67]` 三级、`req` 一级真实 BUF_X1 修复观察到的 hold 路径，不增加逻辑时钟周期；没有移除负载或免检超限网。
- 银行 GDS 从 500pm 无损重序列化为 100pm，与标准单元流一致；132 个银行单元的物理掩模、文字和层次逐一相同。最终 113853 个原生组件位置、全部使用的 55 种标准单元及四银行掩模逐一匹配，真实标准单元放大 5 倍负例被拒。
- 原来 6 项 WELL.4 标记来自深层表示下的重叠井边界；此前“井超出银行”及端盖替代的猜测被实测否定。最终保留全部原始子单元、实例、文字、非井几何，在顶层加入相同全局井并集。全局掩模 XOR 为空，实际物理掩模不变，原版 deep 完整 deck 不改，最终 0 项。100pm 井掩模偏移反例被一致性门拒绝。raw stream 仍保存在远程 `6_stream_raw.gds`；不以关闭 deep 或选择规则代替最终检查。

最终生产/审计/形式源是 **bfe44f869c466702c69416c87be4c8ae13eac250**，源 tar SHA **9b1016371b39669845d836682ae8638fdc8b624c33f171ae6fbb90698ab9d4b4**；严格汇合源 **50bcee00980aa134ddafcbb487a91e141c2df0d2**。四份实际 tar 的全部文件与各自 Git blob 原始字节核对。后续本报告提交仅整理交付，不反向改写生产源标签。

## 交付与复核入口

[源绑定索引](../work/YUZE-LU/155/final-033/source-binding-index.json) 列出六文件、匹配银行五视图、输入约束、复合接点抽象、实际落点、全部回执/日志、版图、源 tar、旧银行源历史 bundle 的远程路径、字节数及 SHA。大文件留授权任务存储，不提交 Git。

- 远程任务根：`yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155`。
- 最终六文件：`physical-033/implementation/flow/results/nangate45/s_sram_155/base/6_final.{v,sdc,def,odb,gds,spef}`。
- 完整交付包：`delivery-final-033/S-SRAM-final-033.zip`；[ZIP 回执](../work/YUZE-LU/155/final-033/delivery.json)。本地镜像在本任务工作树 `.local/delivery-sram-s` 及同级 ZIP。
- [最终验收原件](../work/YUZE-LU/155/final-033/evidence/acceptance.json)、[版图](../work/YUZE-LU/155/final-033/layout.png)、[完整 DRC](../work/YUZE-LU/155/final-033/evidence/whole-gds-drc.lyrdb)。
- `six/6_final.v` 是 ORFS 逻辑导出，省略 178 个 ANTENNA_X1；补充 `supplement/full_signal.v` 从同一最终 ODB 导出，包含全部有信号连接的保护单元，并用于最终功能。ODB/SPEF 及电气审计包含这些实际负载。两份网表分别保留 SHA，不冒称前者是含 PG 的全晶体管网表。

在固定镜像的 Slurm 分配资源内，先核对源 tar/SIF/银行视图 SHA，从源解包目录重跑到**全新输出目录**：

```sh
python3 source/project/experiments/s_sram/physical.py --generation /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation --out "$PWD/implementation-new"
python3 source/project/experiments/s_sram/inspect_final.py --physical "$PWD/implementation-new" --out "$PWD/audit-new"
python3 source/project/experiments/s_sram/run_actual.py --physical "$PWD/implementation-new" --generation /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation --verilator /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator --out "$PWD/function-new"
python3 source/project/experiments/s_sram/formal_banks.py --physical "$PWD/implementation-new" --out "$PWD/proof-new"
python3 source/project/experiments/s_sram/qualify.py --physical "$PWD/implementation-new" --audit "$PWD/audit-new" --function "$PWD/function-new" --formal "$PWD/proof-new" --out "$PWD/acceptance-new.json"
```

前三类检查使用生产源 bfe44f86，最后汇合使用 50bcee00；不能拿旧生产源中的汇合程序替代本次已执行的严格版本。SIF SHA 为 `49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a`，完整 deck SHA 为 `4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147`；工具及平台输入见原件回执。上述命令本身不绕过远程使用规则。

资源并行：九点银行表征 6×1、五个接入候选 4×2 动态补位；整块候选实测采用 32CPU 内两项独立 16CPU（disjoint affinity），完成即补独立审计/功能/形式，见 [continuation-021](../work/YUZE-LU/155/continuation-021/README.md)。最终单选布局必须先完成才有同一产物的审计输入，不能为凑满 6 项伪造独立任务。Slurm RealMemory=1MB 配置错误使显式16GiB请求不获准；`--mem=0`配合实际节点可用内存观察，非降低功能并发来掩盖内存不足，不改服务器配置或其他作业。

## 限制与审查状态

本次通过严格限于 **Nangate45/FreePDK45、TT/1.1V/25C、真实晶体管原理图银行表征**。银行内部 wire PEX 尚未实现；OpenRAM `alter_lh_char_data` 将 HL 复制给 LH 的上游限制保留。整个 S 的外部 RCX/SPEF 不补齐银行内部寄生，也不构成 foundry signoff。最终功能模型默认延迟使用慢时钟验证合同，300MHz 通过来自独立提取 RC 的 STA，不宣称以模型仿真在 300MHz 通过。M11/M12 系统接入、层级 Liberty、多角点以及系统吞吐不在本任务通过范围。

原标准单元 S 继续保留。工程交付完成，Issue 保持开放并进入 in_review，PR 待独立审查，不自行合并。管理登记沿用 management-hub PR5 pending；`config/board.json` 未配置，看板条目 unverified、同步 pending；管理员及审查人待指定。协作 Skill：rayggxia-project-collab 1.0.0。
