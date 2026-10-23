# Issue61：服务器模型补齐批次与划分证据

负责人 Liangruizhi；[Issue61](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/61) / [PR62](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/62)，task/61-server-models，独立工作目录 D:/Projects/LLMHardwareDesign-servermodels。2026-10-23（UTC+08:00）更新：本轮四模型按冻结协议的 CPU 参考/采集已全部执行，三个主测的整数参考与接收检查也已执行；Phi 按要求封存。执行完成不等于所有精度候选通过、全整数硬件通过或 PR 已合并。

用户最新授权本会话在既有服务器完成原委托批次，覆盖旧“等待通知/仅本机”的调度限制。先核对 Issue32/PR36、Issue55/PR58及成员进度；仅补原包缺少的真实完整 GQA 输入，不重复已有长 GPU 矩阵，不接管别人的物理工程。实际 GitHub 身份 Liangruizhi/182389313。

## 1. 逐模型验收与固定条件

机器为 c96/node13，实际约503.5GiB内存，无 GPU/GRES。全部模型加载和算术通过本人 lrz-i61-* Slurm 作业，位于 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023。24CPU采集与2CPU整数/验证独立目录并行；不在登录节点加载模型。完整逐项状态见 [验收表](../../work/Liangruizhi/61/model-acceptance.json)。

| 模型、固定 revision | 结构覆盖 | 本轮实际执行 | 原证据复用/保留 |
| --- | --- | --- | --- |
| Qwen/Qwen2.5-3B，5defd2796acd3cb2051bb4c787eddc7f8f35e113 | 原始基座，非Instruct；16Q/2KV、完整8Q/1KV，QKV bias | 128/1024+32，layer0，full/cached/chunk；60线性、8注意力格式条件；513严格张量 | PR36的FP16长推理/计时；原部分和独立重放1416值 |
| Qwen/Qwen3.5-4B，851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a | 文本路径，3递推+1全局，完整4Q/1KV | 128/1024+32，global layer3，连续conv/recurrence状态；60线性、8注意力条件；714张量 | 原FP16/BF16失败及FP32辅助修复、8192轨迹；5376 partial、12 FP64状态窗口/6连续边界重放 |
| google/gemma-3-4b-it，093f9f388b31de276ce2de164bdc2081324b9767 | 文本，5局部+1全局，window1024，完整2Q/1KV | 128/1023/1024/1025/4096+32，layers0/5；300线性、40注意力条件；3618张量 | 原BF16来源/配置/实际全分片SHA核对；不是多模态推理 |
| microsoft/Phi-4-mini-instruct，cfbefacb99257ffa30c83adab238a50856ac3083 | 24Q/8KV、完整3Q/1KV，partialRoPE.75、LongRoPE | 128/1024+32，layer0 full/cached/chunk与严格来源检查340张量，独立封存 | 未进行量化筛选，未用其数据调整划分；策略冻结后的独立验证仍未执行 |

新参考都是**原始BF16权重加载为CPU FP32**，seed20261023、B1、eager原生类、chunk128；不是独立FP32权重或FP16 GPU执行。Gemma/Phi transformers4.57.6，Qwen使用隔离5.20.2；torch2.10.0+cpu、NumPy2.2.6、Python3.12.7。Qwen3.5无FLA，使用原生Torch回退，文本config加载记录保留视觉权重的非文本差异。

校准128与评价文本分离，实际token IDs/配置/框架实现SHA、有效长度和初末状态在capture manifest；校准仅捕获16个代表行，不能称128个独立校准行。所选线性为q/o/down、完整K及前16输出；prefill首尾选行、32步cached decode逐步捕获。完整GQA指一个共享KV头的全部Q头，非全模型所有层/头。注意力数值探针只取首4/末4 prefill及32个decode query，保留所有有效key，不保存全模型S×S矩阵。

冻结检查：GQA atol/rtol1e-4；最后33位置logits maxabs0.005、relativeL2 1e-4，全部通过。最大已观测logit绝对差：Gemma0.000389576、Qwen2.5 0.000045300、Qwen3.5 0.001742840、Phi0.000141144。它们是teacher-forced一致性，**不是数学/代码质量评测**。

Qwen3-0.6B/Llama3.2-1B既有证据复用，不重复；Gemma12B、Llama3.1-8B、R1蒸馏按最新范围条件跳过；Qwen3-4B不恢复必跑，原版巨大R1不下载。R1蒸馏不代表MLA/MoE。GPU/VRAM/特定4bit内核无法由本CPU服务器补测，标未执行；最新Issue32明确额外语言质量并非EDA前置，不擅自扩成必跑矩阵。

## 2. 整数合同与独立验证

正式配置 [quant-protocol.json](../../project/experiments/server_models/quant-protocol.json)。源FP32先检查并RNE编码S32Q20；A/W对称S8[-127,127]，scale为I8二进制指数，A按静态tensor/动态行/K128，W按输出或输出×K128。每组i32部分和；组间按单位对齐到检查过范围的i64软件参考，再一次RNE/Sat8。Y逐输出scale固定为两倍校准最大值；Qwen2.5 bias离线编码S32Q20，在最终RQ前整数对齐相加，不能将bias遗漏或浮点后加。

W/static/Y编译期scale仍用FP64；动态A在S32Q20之后用整数范围/位操作选scale。Norm、RoPE、非线性、Qwen3.5状态等原捕获仍浮点；注意力exp/div显式FP64回退，没有全整数softmax/状态实现。软件整数参考和真实INT8内核速度分开，不能从NumPy执行称目标硬件已有该能力。

三个主测共420线性、56注意力格式条件已执行。独立接收重算3852288个INT64 partial、161280个Fraction最终RQ、50503680个A编码、240768个scale指数及1680项包核对。严格导出再次逐值对照原捕获，累计5185张量（含Phi），不能只相信生产方自己重写的SHA。

### down_proj：scale粒度是跨模型的真实分叉

下表为相应模型/层所有本轮prefill/decode切片的最坏最终输出relativeRMSE，完整K/16输出、相同Y合同；5%仅是预先冻结的局部探索门。

| 模型/层 | 静态全K A/Wout | 动态行A/Wout | 动态K128 A/Wout | 动态K128 A/W128 |
| --- | ---: | ---: | ---: | ---: |
| Gemma layer0 | 28.40% | 14.03% | 4.08% | 3.81% |
| Gemma layer5 | 21.22% | 18.23% | 4.21% | 4.00% |
| Qwen2.5 layer0 | 27.45% | 18.27% | 3.48% | 3.37% |
| Qwen3.5 layer3 | 8.58% | 5.32% | 4.93% | 4.83% |

动态K组A比单纯动态整行更关键；Wout在这些切片已接近W128，不应把W128强行固化到所有算子。既有Llama最优5.39%仍是失败，不能用新模型过门覆盖。Gemma layer0 q_proj/o_proj即使RMSE<5%也分别出现输出饱和（dynamic_K128_W128合计21/5个），所以**并非全部线性合同通过**。Qwen3.5 down在RQ前最坏0.84%、RQ后4.83%，再次提示输出scale/格式可能比输入继续细分更值得检查。所有失败/饱和保留，未做事后阈值调整。

### 注意力：不能统一KV8/P8

P8/P16分别为非负P7/P15有效码、存储I8/I16，步长2^-7/2^-15；KV在校准后冻结逐头二进制scale。下表为完整共享组所选query的最坏注意力输出RMSE，有FP64 softmax回退，非完整模型质量。

| 组 | KV8/P8 | KV8/P16 | KV16/P16 |
| --- | ---: | ---: | ---: |
| Gemma local layer0 | 34.47% | 3.52% | 0.50% |
| Gemma global layer5 | 6.89% | 4.49% | 1.74% |
| Qwen2.5 layer0 | 13.98% | 12.50% | 0.58% |
| Qwen3.5 global layer3 | 23.37% | 2.88% | 0.95% |

KV8对Qwen2.5仍是瓶颈，Gemma/Qwen3.5的所选组更受概率低位精度影响。所有KV剪裁为0也不保证误差小。P零比例包含因果/窗口mask的零，不能把96%–99%零值全解释成量化损失。16位不是免费能力：只允许S8单元时，3个radix128 limb实现16×8需3次、16×16需9次S8乘积，加移位/归约/流量；尚无此新算术RTL/PPA资格。

## 3. 范围证明修正：保留不变量，比盲目加宽更重要

作业90045/90046读取相同真实输入，原始数值指标不变。[conditional-bounds02.json](../../project/experiments/server_models/results/issue-61/conditional-bounds02.json)明确区分：粗格式界、固定权重界、归一化概率语义界。

线性采用 B=Σg127·Σk|W8|·2^(unit_g-e0)+|aligned_bias|。420个所见scale矩阵的固定16输出范围界均可进INT32，Gemma/Qwen2.5/Qwen3.5最宽分别30/31/30位；粗33/34位并不等于实际溢出。范围证明仅绑定当前W和所见单位，未证明未来所有动态scale或整层安全。逐组逐输出U32 L1系数对down的16输出分别需要5120/5504/4608B，还需在线检查、移位、相加及不通过时的回退，不能当零成本。

PV若把每个概率码当任意独立最大值，粗界可达44位；归一化P则满足 ΣPcode≤2^f+ceil(activeK/2)+1，且V全key共用同一head scale。本轮最长4128key、P15预算34833，实测最大32793。V16的3个平衡radix128 limb，其加权绝对界为41024；P预算×41024可覆盖每个limb前缀，仍进INT32。

**90046实际用S8值limb、NumPy I32部分积和累加，以独立I64 sidecar检查移位项及每次相加溢出，56条件的1474560个PV输出全部匹配原I64参考**。14/28/14条件分别用1/3/9个基础乘积；完整输出核而非只验一个标量。边界测试遍历16位limb域，40000key条件不能无条件认证；P8均匀1/256被RNE成零说明范围安全与误差是不同问题。

条件成本：每活动query/head一个U32计数器4B、概率预算检查、固定Vscale/状态epoch和单位证明。**未实现的整数exp/div必须自身证明或强制满足相同Psum条件**。该界不覆盖未归一化online attention O反馈、跨页Vscale变化或更长上下文；不能直接取消全部宽旁路。

划分启发：优先把“概率归一化/重标定→受检概率→PV完整归约”作为保持不变量的局部闭包候选。若拆开，接口应带单位、有效长度/掩码、Psum预算/证明和版本，而非只传裸INT32。线性同理固定完整归约语义，RQ位置继续可选。见[决策记录](../decisions/2026-10-23-invariant-preserving-block-boundaries.md)。

## 4. 容量、端口和实际打包

所有位宽、A/W/Y scale、bias、单位、包头64B、对齐64B、payload1984B、链路128bit分别记账；不把FP32统一除四。初始静态元数据传输与驻留分列，展开单位/紧凑重构单位两种实现分列。16KiB源暂存放不下一行down的S32输入时，需重读或分组调度；未实现其调度不能宣称免费streaming。

[causal-cost01.json](../../project/experiments/server_models/results/issue-61/causal-cost01.json)，90047，补齐420条件的逐调用重打包。原linear.json中的cost聚合所有选行，只是字节下界；decode必须逐token发包，不能合并32未来步骤。例：Gemma layer0/down K128W128，32步、N16、K10240：

- 最终I8每步128B，合计4096B；旧聚合640B不代表真实因果decode链路。
- 共享V紧凑部分和包合计174080B，展开单位为256000B；另有两侧共同的最终输出。静态W/Y元数据驻留1296B，初始化包1408B。
- 所有K组部分和同时物化每行5120B、32步合计部分和读写327680B；流式归约另为每行I32 64B/I64 128B，但需要调度/端口证明，不能同时假定物化成本与流式收益。
- 源S32行40960B大于16KiB；L1 guard表5120B、每选行1280个范围项。

这些是**同数值合同下通信/容量/端口服务下界与明确假设**，未新建公平端到端调度器，不是10880拍就等于芯片多10880周期。既有E2a收益约0.57%仍保留原条件，新模型不继承该百分比；E2b完整attention、E3公平状态和E4物理仍未完成。

Gemma原生FP32在4096+32：KV逻辑412114944B（393.02MiB），full prefill底层storage1149763584B（1096.5MiB），cached decode最后412352512B（393.25MiB）。窗口逻辑正确，但view保留大base可使prefill分配约为逻辑2.79倍；chunk时也单列。应分别核数学活跃窗口、物理对象生存期、prefill工作区、硬件ring buffer实现，不能把原生框架分配量当目标SRAM必需量或直接按位宽缩放。

## 5. 实际作业、失败与版本

| Slurm job | 内容 | 实际结果 |
| --- | --- | --- |
| 89992/89993 | 原Qwen partial/连续状态两轮独立重放 | COMPLETED0:0，23秒/4秒 |
| 89995 | 服务器直接HF下载 | FAILED1:0，DNS失败；公开镜像中继替代传输 |
| 90002/90016/90028 | 后端/缩小模型检查 | 完成；90017字典状态适配失败保留，修复后90028通过 |
| 90026 | Phi实际参考/封存 | COMPLETED0:0，42秒，24CPU |
| 90030 | Gemma实际参考/窗口/GQA | COMPLETED0:0，1分59秒，24CPU |
| 90033/90036 | Qwen2.5/Qwen3.5实际参考/GQA | COMPLETED0:0，45秒/48秒，24CPU |
| 90031/90034/90037 | 三主测整数探针 | COMPLETED0:0，70秒/24秒/23秒，2CPU |
| 90032/90035/90038 | 独立整数接收及旧格式 | 完成，旧strict01因cached norm混入full scope而废止，不能当正式导出 |
| 90039/90040/90041/90042 | 修正strict02及逐值来源绑定 | 全部COMPLETED0:0，67秒/13秒/16秒/11秒 |
| 90043/90044 | 汇总、真实负例、封装和精选重放 | COMPLETED0:0，1秒/47秒 |
| 90045/90046/90047 | 条件范围界、全PV32核、因果包成本 | COMPLETED0:0，12秒/28秒/1秒 |

这些是带采集/加载/验证的作业耗时，**不是可比较的模型吞吐**。实际脚本RSS/时间完整保存，不用于推算目标Block/PPA。详细sacct见work61/execution-ledger.tsv及final-execution-ledger.log。

服务器外网DNS/HTTPS不可用；用户授权后由本机内存中继公开ModelScope原BF16资源，固定revision并核官方Git/LFS与实际完整文件SHA，未将完整权重落本机。Gemma一个完整分片SHA失败隔离为.failed-39a56b55，原失败保留，重传后期望SHA通过；短写处理已修正，但根因未确认，不写成已证明的网络/管道bug。Qwen3.5 LICENSE与原包仅LF/CRLF差异可精确重构，权重无差异。没有借凭据、代点许可或删除失败。

关键正式源码：Gemma/Phi捕获8a1fe4bfed52dd0baa552c6043f507bafe902c03；Qwen捕获a96eef6175d15173496d674caee7b0078971f2f5；整数3f17910ec3d9591a10e9b98ff09916154385751d；最终导出0ff14d76d51beb0a0c607d7e0d024a41b49fd661；收集7fdd2c243e8c1e8a1b9abfcae262ebc9f27bd1b5；全PV32核4ca7214923dd5d87934fb2e10211517bbca35c19；因果成本8211803c9a6f7bab42f66ef320410693b9522be2。每阶段独立binding，不以文档最终commit冒充运行源码。

## 6. 数据交付和验收边界

正式 [index.json](../../project/experiments/server_models/results/issue-61/index.json)保存大小、完整SHA、源码和范围。所有大包在本人授权服务器根目录；不是公共下载链接，接收人需其已有服务器权限，不新增授权。

| 成果 | 大小B | SHA-256 |
| --- | ---: | --- |
| primary-model-data01.zip，服务器：三个主测完整原捕获/编码/strict02 | 569140969 | 2f03daf778c6667aae49d2edd40f3397227514e59c6342d367a552cac6ff7730 |
| phi-reserved02-sealed.zip，服务器：保留验证封存 | 30232659 | 373a030cc3f4087664d69d20bb13a9ed504e9753972c8a52cf1d5edaa4c668ed |
| batch-metadata01.zip，仓库：日志、指标、冻结源码、精选样本 | 7269991 | b2e94f70861d92debf71d5f0055a7006c6c1731db688e46c0473d0786b9530fa |
| conditional-bounds02.json，仓库：全PV32核与条件界 | 296152 | 9897fc12300206c9c0b6e357beb6d7f1d6bbe63dbfdcef882f07396bdcf7938a |
| causal-cost01.json，仓库：逐token实际粒度账本 | 627318 | 5e34b9543fb1d88e3da0f426f93557647329de95e9ccbed9e4ed1b714e27fa2c |

本机已核元数据包117个索引成员+自身索引，27个源文件逐字节比对5个原始Git commit。精选样本在包内review-samples01.zip，独立离线重放4个完整GQA组491520个FP64输出、6个down case182784 partial/2304 Fraction RQ。它不包含全420个case或全部浮点校准输入；全量重算须读服务器主包。Phi不在调优/精选样本中。

真实负例：改动Qwen2.5一个存储INT8输出并重写生产SHA，被独立Fraction重放拒绝；改动导出FP32的低位并重写SHA/schema通过后，被原捕获逐值绑定拒绝。篡改样本与错误日志单独保留，不污染正式包。PR36另核69文件：57原字节、12Git换行精确还原；不能写成69原字节相等。

已执行管理结构、项目五套业务测试和server_models17项边界/接收测试；实际命令、日志和后续接收入口见[README](../../project/experiments/server_models/README.md)、work61及[交接](../handoffs/2026-10-23-issue-61-server-models.md)。未执行本批新算术RTL/目标时序/PPA、全整数非线性/状态、整图收益；这些是研究下一阶段，不能用本轮CPU通过替代。

当前交付分支/PR62待审查，基于未合并PR60；不自行合并或done。登记management-hub PR5 pending；无board.json/Projects能力，看板状态unverified、同步pending待管理员，审查人待指定。
