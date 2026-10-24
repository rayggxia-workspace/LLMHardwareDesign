# Issue74：完整整数MoE与分组量化Block边界验证

2026-10-24 Asia/Shanghai；负责人Liangruizhi；[Issue74](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/74)/[PR75](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/75)，分支task/74-moe-grouped，基于PR73@88e9c4b。结论修订[Block v2第13节](../BLOCK_PARTITION_V2.md)，原FP/整数/失败证据保留。

**补齐了Granite冻结层切口的真实路由、全部所选专家、加权合并、残差和后继归一化整数链；分组投影同函数M/V驻留比较全部通过。** 结果支持固定单位、完整归约、宽合并和有限存储接口，仍不足以固定M/V物理融合或宣称完整模型质量/端到端收益。全部真实模型/张量/服务由本人CPU服务器Slurm并行完成；本机只有源码、小型合成测试、JSON及字节接收，无新增权重、其他机器任务或Phi解封。

## 1. 范围、来源与验收

执行前冻结[协议](../../project/experiments/moe_grouped/PROTOCOL.md)，实际命令、源码commit/SHA、环境、Slurm见[work74](../../work/Liangruizhi/74/README.md)。新服务器根/public/home/yuzelu/RuizhiLiang/issue74-moe-grouped-20261024，前缀lrz-i74-*。权重/旧Issue70和72输入只读，未覆盖成员55/63或服务器89448作业。

| 对象 | 实际状态 | 证据与限制 |
| --- | --- | --- |
| Granite固定官方revision | 已核/复用 | a02780686e08a03fe0d2679a293b5c74a90efa89；config/index/两原BF16 shard SHA匹配官方回执 |
| 两层真实cut捕获 | 已执行且一致 | 90284；层0/13、cal/eval72；post-attention residual、norm、专家和nextnorm，LM/router/MoE/hidden对旧model64逐码0差 |
| 完整整数MoE | 已执行/独立PASS | 8条件，每项43stage/576完整专家路径；合计4608路径非独立样本；24真实NPZ篡改并重写SHA后数学层拒绝 |
| 三g实际宽RQ lowering | 已执行/逐码PASS | 每g184320、共552960产品，显式S8 digit/8或16字节carry对旧hi/lo全量一致 |
| Falcon分组部署 | 已执行/独立PASS | 3函数×2驻留×2标签=12；48实际SHA重写负例；完整R前缀/后继逐事件继承并绑定对应新g整数码 |
| 配对/事后分析 | 已执行 | 90331比较PASS_BOUND_COMPARISON；90308原8产物事后诊断，未新增格式/样本 |
| Granite分组服务、整模型质量 | 未执行/未验收 | Granite只有完整cut数学及容量/算术义务；Falcon服务不能替代Granite端口调度 |
| 目标INT8内核/RTL/布线/时序/PPA | 未执行/未验收 | CPU时间、整数参考和条件服务时隙分列 |

model64参考内部仍有框架norm/RoPE/softmax的FP32 cast，不能称全FP64真值；旧native32/router64失败保留。此次是捕获行的离线cut重放，后8位置按输入标为decode诊断分组，不代表重新执行真实cached-decode调度；原完整/cached/chunk一致性证据见Issue72。

## 2. Granite完整数值合同与成本义务

40专家、top8、H1536、I512。真正外部边界是新hook得到的post-attention residual，不由hidden减MoE倒推。完整链消费当前整数码，Attention、之前/更后层仍在边界外。

| 数据/运算 | 冻结格式与规则 | 实现/成本边界 |
| --- | --- | --- |
| residual/向量 | I32Q12，入口RNE，越界拒绝 | 非全路径A8；单位/布局显式 |
| 完整RMSNorm | gamma I32Q20，epsilon17 Q24，U128平方和/isqrt/div及RNE | 位算法软件参考和独立重算；不把宽算术当已有硬件 |
| expert矩阵 | perexpert/peroutput W8、静态Q31+I16；A8由当前完整行最小RNE shift选单位；fullK INT32 | 对称127码，gate/up K1536界24774144、down K512界8258048，低于INT32；更广码域另核界 |
| router R8/R16 | 相同current norm，peroutput power2 W8/W16及I16指数 | R16全72行/40输出实际9个S8 dot+S64重组，不是免费INT16乘法 |
| top8/Q15 gate | 实际ID，U16 Q15和32768；exp2Q24 LUT、整数除法 | 通用S64 logit差需I65、乘log2e需I97/I128；50积+49次128bit重组是候选，不可套45积费用 |
| SiLU/门乘 | Q12表[-32,32]步1/256，Q24乘积RNE12成Q12，再动态A8 | SiLU表65540B、router表8196B；不能免费塞V8KiB；越域/归零记录 |
| 全8expert合并 | down完整K先RQ共同I32Q12；Q15×data S64全8路prefix，最后一次RNE15 | lateRQ是另一函数，未作placement比较 |
| consumer | 0.22编译Q20/RNE20，加真实残差，再完整nextnorm | 不忽略实际系数；整数运行无FP回退，编译/最终FP诊断分开 |

独立接收重编译全部40专家参数/LUT、重算完整所选路径和43stage，并查runtime AST。PASS只表示正确执行冻结整数函数，不代表质量已接受。详见[GRANITE](../../project/experiments/moe_grouped/GRANITE.md)/[AUDIT](../../project/experiments/moe_grouped/AUDIT.md)。

## 3. 路由改善与剩余误差

全部为本层cut局部L2；各层残差/norm会放大或衰减误差，不据此跨层排名模型难度。

| 层 | router | split | 对native集合变化 | 对同current norm FP64 router变化 | MoE L2 | nextnorm L2 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 0 | R8 | cal | 11/72 | 11/72 | 8.9550% | 9.8112% |
| 0 | R8 | eval | 15/72 | 15/72 | 8.4195% | 9.4843% |
| 0 | R16 | cal | 0/72 | 0/72 | 8.1881% | 8.9270% |
| 0 | R16 | eval | 0/72 | 0/72 | 7.7125% | 8.6287% |
| 13 | R8 | cal | 7/72 | 6/72 | 6.9792% | 1.4379% |
| 13 | R8 | eval | 3/72 | 4/72 | 7.7869% | 1.1581% |
| 13 | R16 | cal | 1/72 | 0/72 | 6.8690% | 1.0671% |
| 13 | R16 | eval | 0/72 | 1/72 | 7.7314% | 1.0196% |

R16评价两层最终集合与native相同，但层13对同一current norm FP64 router仍1差；token42的上游扰动与整数router误差抵消。最终0差不等于router自身稳健或一般W16足够。

[事后归因](../../project/experiments/moe_grouped/POSTHOC.md)显示：匹配expert ID的mid在最后Q12 RNE之前已有层0约11%、层13约5.1%–5.2%L2误差。最终同操作数RNE能量/总mid误差仅3.16e-8–3.14e-6；额外mid→A8误差约3.17%–3.25%L2。所有条件mid shift delta最低6/7，无delta0未满量程行。因此不追加只换midQ20实验：增8小数位通常使A8 shift也增8，不能凭格式名获得更多有效位。能量分解有cross，不是对down/nextnorm的因果贡献；上游含norm、W8 gate/up、RQ及SiLU，未逐项隔离。

单层40expert W8为94371840B，静态scale614400B，两个所测层不能同驻EXT128MiB；软件编译数组不代表硬件库存。每expert512维mid需2048B缓冲或重读。全8路S32输出49152B，S64 merge12288B加6144B输出超V16KiB，必须流式tile/合法spill与背压。ID/Q15 gate24B/token、mid delta16B/token、expert输入delta2B/row也须计生命周期。

## 4. 分组函数的同资源部署

本部分是**Falcon相同gatedinput、W8和scale的输出投影**，不是Granite grouped。whole/K512/K256为不同数值函数，各自保持完整partial/对齐和一次最终RQ，才比较M/V驻留。不同g误差收益不能称placement收益。

守恒M256(16×16、B1有效16PE)、共享VR8、单SFU/ROM、M32KiB/V16KiB/R32KiB/S8×32KiB/EXT128MiB、128bit1RW、单BUS和2KiB FIFO；不赠M私有ALU/端口/寄存器。两侧用同bank-select VR服务，差异为驻留/搬运，不是已实现的物理locality。Otile16/Ktile256固定，无prefill batch或优化流水调度。

| 函数 | near M完整链slots | shared V完整链slots | 近M节省 | near M总wire B | shared V总wire B |
| --- | ---: | ---: | ---: | ---: | ---: |
| whole | 16,012,158,659 | 16,012,319,939 | 0.001007% | 18,662,795,456 | 18,663,895,616 |
| K512 | 16,107,447,522 | 16,108,737,762 | 0.008010% | 19,171,150,016 | 19,179,991,616 |
| K256 | 16,120,032,657 | 16,122,613,137 | 0.016005% | 19,218,354,368 | 19,236,043,328 |

12独立接收PASS，6组纯label witness/splice逐字节一致。同g库存/容量/分配/数值绑定/算术和engine operand计数相同；V多72×34B descriptor本地copy与实际partial跨bank流。当前34B含g<=16描述符padding，不是每g数学最小元数据。

宽算术与端口成本全账：

- g0 32×32→64 core为25 S8积+24次8字节carry/控制；grouped 64×32→128为45积+44次16字节carry/控制。552960实际产品均逐码一致。
- 再计digit提取18/26 byteops、每term常数shift构造14/22、S32→64符号扩展11、动态对齐18、RNE64/128共106/182 byteops，含舍入/符号/I32 guard。不是只算MAC或套CPU大整数速度。
- 所有operand/digit/partial/product及回写付1RW bank拍、BUS包头/16B打包和有限FIFO。K256 engine wire810823680B已包含于总19218354368B，禁止再加一次。
- 动态delta I16每token useful2G B，另common delta2B；实际owner descriptor34B/token，near M传80B/token，shared V本地copy。
- W scale每输出Q31+I16只一份共15360B，72token读取1105920B，不按G复制。两个端点各预留1344B新scratch，V另64B delta；高水M22720/V9600/R32768、EXT85293632/ROM4260100B，最大VR operand576B借原2KiB FIFO。
- shared V每64B S32 tile partial成96B包；whole/K512/K256 partial wire1105920/8847360/17694720B，减near M descriptor5760B，精确等于三对wire差。旧whole-O协议的8/16倍保留原条件，不混用新tile包头。

见[微程序和接口合同](../../project/experiments/moe_grouped/GROUPED_SERVICE.md)。它们是候选微实现/上界，未RTL校准；完整链有继承R/consumer及外部A/residual cut，分母不是整模型。90305旧费用pilot保留不排名；正式90306起。新g0也计更完整steering/RNE/IO，不与旧base绝对时隙排序。

## 5. 算子与Block划分收敛

| 边界 | 可确定的义务 | 保留的物理选择 |
| --- | --- | --- |
| M完整K→重标 | 同单位INT32 partial，混合单位显式I64对齐/guard，完整和后一次RQ；typed partial/complete | 近M或共享V驻留、共享宽引擎映射；0.001%–0.016%不足以固定融合 |
| router→dispatch→expert→merge | 动态ID/gate、实际输入单位、完整所选专家、共同down单位、宽prefix/final-RNE | router精度/回退、topk/SFU归属、expert分页/merge tile；不固定所见expert连接 |
| V完整consumer | 全hidden norm、epsilon/gamma/scale版本、残差系数、布局/表端口/缓冲 | 分块/两遍读/共享ROM；W8A8不能掩盖I32/I64/I128 |
| R/S/D既有闭包 | 连续history、两代状态、range guard、因果重标、unit/epoch/version、原子发布 | 独立R或V/R合宏仍待实现/物理；Granite无R不改变原Falcon/Qwen证据 |

继续M/V/A/R/S/D六逻辑模板。固定局部MAC反馈、存储仲裁、范围检查、版本提交的候选义务；保留M↔V宽旁路、动态dispatch和S/backing端点的产品映射。完整归约/状态闭包不等于必须同制造宏。

后续只补影响边界的分叉：S8宽微程序/SFU/ROM/bank-select实际校准；Granite有限容量expert/merge tile调度。质量收敛先隔离gate/up权重/激活误差再决定分组，不盲改F20或增加品牌。Granite grouped/整模型质量预算与冻结后Phi独立验证未执行。

## 6. 成果与交付

统一[索引](../../project/experiments/moe_grouped/results/issue-74/index.json)记录全部实际源、命令、Slurm、大小/SHA及完整/精选包位置；原权重和Issue70/72输入明确外置。完整档保留调试pilot及所有实际篡改负例。精选metadata只作字节接收，不代替服务器数学/端口验收。

实际检查及准确数量见索引/work74回执：新模块小型合成边界/比较测试、closure原90项、architecture_extensions原80项、check_project和diffcheck。未在本机重跑真实模型或服务。

通过同一PR75交付，最终远端commit/CI/ready以读回回执为准；未经要求的审查合并为in_review而非done。登记PR5 pending；无board.json/Projects能力，看板unverified/同步pending，管理员/审查人待指定，不把文件上传描述成看板/物理验收完成。
