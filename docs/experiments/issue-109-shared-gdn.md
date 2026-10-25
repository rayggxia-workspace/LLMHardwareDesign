# Issue109：M/A/Falcon/GDN 四profile真实共享服务

负责人 Liangruizhi；2026-10-25。[Issue109](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/109)；task/109-shared-gdn。基于PR108@7a9fece与PR107@03ab900，合并d5e7cd1。实际RTL/正常driver冻结4b69d43，44cmd恢复driver fe14c02；最终接收phase6，端口成本phase7，门级延时工具phase8。本地科学证据与跨机接收已完成；root统一发布PR，尚未上传/审查合并，不能据此认为物理完成。

## 已形成的边界

M/V、A、Falcon R、Qwen3.5 GDN R控制器现在实际共用同一个16KiB/128bit/1RW、8S8组合乘法、一个S32服务（两个64bit响应槽）、一个128bit SFU和一个memory_link。不是四份同预算核相加。GDN三块宽乘lowerer只有控制/暂存，三次使用同一个S32服务，exact product之后单次RNE；常量49地址cell另外计价。四个控制器及所有寄存、格式/比较/移位/RNE、metadata、D选择器和debug均在实际logic mapping中。

GDN每个STEP完整计算两头128×128状态，所有head range收齐后，按104原保守guard重标；不能按tile自行改变scale。两个state bank、trial、I64 proposal、两个I64 Y bank、两套64B metadata与16B原子root位于独立0x06200000..0x06300000外部窗口。active mutable659600B + 32slots50176B = 709776B。实际从104原image只改metadata word3三个地址指针，数据数组与coefficients逐字节不变；源状态和版本不是host新造中间值。

完整2048B候选Y经共享外部桥读128×16B，通过同一个result_valid/take出口。新增导出路径有32bit基址、10bit索引和1bit pending；桥本身保持单有限response，不新增2048B片内buffer。候选identity含owner32/context64/position64/version64/units16/numeric_epoch32/bank1，共273bit，不含result索引/有效握手。D使用独立transport generation。全部候选ACK后才能accept/reject；accept后root提交不可撤销，只有ACK后更新published mirror并最终释放lease。

环境sink最高6KiB（M结果；GDN2048B），写入前缀为provisional，失败必须丢弃。sink、外部双response FIFO最低320bit加控制和请求/回复32bit epoch线路，不在core logic area内；没有实现下一Block的事务buffer或GDN后续gated norm。DONE ACK表示原bank读引用已释放，禁止busy期间外部并发读写；两bank不是任意历史快照。

## 对Block电路边界的直接含义

本次可确定的是服务所有权与数值原子性：GDN的完整head range/重标和双head发布仍由R控制；tile只限制搬运和暂存，不能独立选scale。S是共享scratch，跨算子持久状态必须在有版本的外部state/root；D承担独占lease、统一transport、候选真实导出与commit-drain；不能将R数值epoch或两head单位藏进D传输tag。M/A的8S8是真实operand/result mux共享，GDN/Falcon使用同一S32服务，所有独立控制器面积仍在。

| profile | 本切片真实精度与计算范围 | 仍在边界外 |
|---|---|---|
| M/V | 原INT32Q12 gate/up→整数SiLU/LUT→整K512量化A8、8S8矩阵与INT32累加、merge/residual/流式norm | 通用V ISA、任意GEMM、模型所有层 |
| A | Q8、K/V16、P15，实际8S8 limb分解和宽归约/SFU | online/append、投影/RoPE、output projection |
| Falcon R | 完整D128×N256单head原S32状态、宽整数guard/RNE及原子root | 其余31heads、卷积及完整4096消费者 |
| GDN R | 两头128×128非对称S32状态、每头I8 unit、Q/K/V对称S16、decay U32Q31、beta U16Q15；I64中间量/Y，实际3段S32 lowering后单次RNE | 输入投影/L2norm/非线性gate、输出gated norm |

这支持保留“计算/状态语义控制器 + 有限共享服务”的电路候选，不支持立即冻结最终物理边界。当前一次一个owner串行，吞吐、可重叠调度、真实宏与电气路径仍缺；不同profile顺序完成不是同一LLM端到端性能提升。

## 实际服务器验证

全部张量/数学/RTL/综合/门级在本人服务器 `/public/home/yuzelu/RuizhiLiang/issue109-shared-gdn-20261025`，仅lrz-i109作业。PC仅管理、源码/AST和字节接收，无模型下载、无Phi解封。

| 条件 | quiet | 有界等待 | 验收 |
|---|---:|---:|---|
| 同instance完整混合命令 | 13 | 13 | 独立97/102/99/104 oracle全部通过 |
| D总周期 | 27900245 | 32753641 | 原配置下测量，非整模型端到端速度 |
| 外部事务 | 1418349 | 1418349 | 每事务5×128bit；sideband另计 |
| S读/写 | 1536736 / 189484 | 同左 | 唯一真实1RW端口 |
| S32端口0/1 grants | 1204752 / 14336 | 同左 | 包括实际GDN宽lowering |
| 恢复/协议命令 | 44 | 44 | 独立完整状态/输出接收通过 |
| 恢复D总周期 | 39287602 | 46227762 | 12次实际abort/4次stale，跨两次reset前采样 |

主序列包括两原Granite完整V/M/norm、真实Qwen2.5 full首query（有效KV=1）和cached query（有效KV=129）、Falcon完整head INIT/两连续步，以及GDN native连续三步跨其他lease和真实legacy重标checkpoint一步。每路GDN4commit/1range-wave，84352个完整stage pair、13个完整状态快照425984codes及3328输出codes独立比较。不是同一模型的完整层图；没有把native32/portable12全轨迹再次执行。原104的全轨迹证据保持其原条件。

恢复每路44cmd，25类明确检查，包括cfg写/读ACK冲突、M/A/Falcon原在途/registry边界、GDN S ACK/宽S32/外部读写/候选导出在途取消、完整候选拒绝、延迟root ACK、错误owner/position/version、旧tag、最后合法GDN命令和协调reset后RESTORE。G root写已实际生效而ACK保持24拍时，镜像仍旧、abort不接受、lease不释放；ACK后只提交一次。保存每条完整published状态/Y/root/meta；失败和拒绝不得改变原checkpoint。终止epoch直接Q注入仅RTL，不计门级资格。

八个实际文件重SHA语义负例经完整receiver新进程拒绝：G输出/state/version/stage、M输出、A概率、Falcon末状态、typed protocol；不是仅hash失败。三项真实网表重SHA负例拒绝额外S容量、额外动态乘法和缺失映射cell。源码静态审计另确认104数学/FSM尾部经明示地址与generation抽离后逐字节一致；不是形式等价证明。

## 资源与限制

实际Nangate45 logic-only面积163901.220µm²，109574cells、12767DFF；generic寄存14291bit，唯一memory131072bit。相对106 125966.694µm²增加约30.11%，增加完整第四profile控制器及宽算术/导出/mux；不是相同函数的面积优化结论。实际顶层输入1102bit/输出3287bit含所有debug，不能当产品已收敛物理端口；层级/port逐项账本在cost02.json。

每个G完整候选另付128外部读、2048B payload、10240B线传输、1024B generation sideband；没有免费读back。M/A/Falcon原数学和容量不改；raw controller cycles包含OFFER等待，不能与D export_cycles重复相加。

| 实际quiet GDN步骤 | D周期 | 外部事务 | S32 grants | S读/写 |
|---|---:|---:|---:|---:|
| native连续每步 | 2296327 | 90471 | 197376 | 82048 / 16482 |
| legacy真实重标checkpoint一步 | 3907725 | 131431 | 361984 | 147712 / 32866 |

该表保留完整head重标、proposal、shadow与输出的真实费用；两个来源输入不同，不把差值当相同输入的优化收益。每个完整G候选quiet导出1280周期，等待模式1660或1663周期；这是D导出阶段观测，与controller等待有重叠。后续优化须保持全head guard和一次RNE，同时验证所有影子状态读写与lease排空成本，不能只优化单个乘法后宣称完整R加速。

SRAM仍行为wrapper，LUT仍外部128KiB；没有真实SRAM宏、STA/CTS/RC/PVT、物理功耗或布局布线/制造后金属定制资格。A仅materialized三遍score/PV，KV caller committed前缀，无append/online；M仍8S8/K512/8专家/H1536专用消费者，非通用16×16。GDN输入投影/L2norm/gates与输出gated norm未在本切片实现。完整Block库尚未验收完成。

## 最终选定门级结果与原失败

两路原始mapped gate首轮2400s到限，均完成7/8命令，最后GDN真实重标未结束；quiet已27794/33664阶段对、held3604/33664。FAILED/timeout原档保留。原网表/二进制/driver/输入唯一一次6000s有界重放gate002/gate102已分别用41:43、50:46完成，两个独立receiver各1:01通过。每路8完整命令、2次完整两head GDN提交/1次真实重标、50560stage pairs、262144state codes/2048Y codes及4096B真实导出全部接收；actual行/状态快照/阶段/协议与对应RTL逐字节相同。selected A仅有效KV1但完整8head，主RTL另覆盖cached129；门级不含44cmd恢复或RTL-only Q注入。

## 交付与恢复

43本人作业全部终态：39COMPLETED、2首轮门级FAILED、2依赖reader CANCELLED。完整104917869B/673members留授权服务器delivery01，SHA `9de3fc27bf2fd89fbcb8d3d1a753b26910b4a73214ee8d0f42ad0f1334a19994`；精选356685B/229members入仓，SHA `24080128111fac643d7e10186545eb849d103829e76c35e8a065399ad972fd13`。服务器双包、本机精选及8phase233原Git源字节全部通过；104原41项/106原52项源与工件Git blob不变。见[正式索引](../../project/experiments/shared_gdn/results/issue-109/index.json)、[门级回执](../../project/experiments/shared_gdn/results/issue-109/gate-receipt.json)及[电路候选v2](../BLOCK_CIRCUIT_CANDIDATE_V2.md)。

项目结构实际PASS仅管理结构。root统一上传PR/读回；当前未push，Issue仍in_progress、非done；登记management-hub PR5 pending，Projects缺配置/read:project，unverified/同步pending，审查人/管理员待指定。

恢复先核最新Issue/PR及本地clean HEAD，已有43作业全部结束，无需重启；root发布后读回report/index/cost/gate四份关键文件。后续按电路候选v2的真实消费者buffer、宏/drive/PG/PVT和新top物理门槛继续。109物理资格不继承98或旧86/88。
