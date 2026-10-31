# 七宏六类连接方案与协调机制研究

任务：[Issue #151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151)，负责人 Melodydt。第一阶段研究交付，待独立审查；下文保留“已有实现 / 结构核验 / 候选方案 / 待验证”的区别。

当前七宏不能用一套已经存在的通用bridge串起来。已有协调资源分为三类：S内部的专用供数器、旧互联实验中单独硬化的辅助宏、实验顶层/软件模型中的外部控制。六类样本还需要显式的格式、布局、存储生命周期与阶段调度；GDN/SSM系数和MoE宽归并另有数值能力决策，不能隐藏在普通协议bridge里。

## 已有实现的归属总表

| 机制 | 放置位置与实际工作 | 接入七宏时的处理 |
| --- | --- | --- |
| S→M loader | `block_feed_s_macro`内部与四存储bank共同硬化；512bit读出、A128/B512分发、有限队列、bank/row/tile/half及装载完成 | 可复用接口组织，重核M v2命令、结果与行级提交；loader不负责启动完整计算图 |
| `block_feed_pair`的M→T mux | 组合测试顶层中的route_to_t与写索引；有源test glue，不是独立硬宏 | 不能计作已实现的产品协调器；若采用，须作为预制逻辑正式实现和计价 |
| PR133 `bridge` | 独立硬化的`linkclose_bridge_fixed`；2×131bit弹性包、capture过滤、T顺序写索引及输出驱动 | 可参考有限排队方法；单capture、无任务版本、错误仅观测等合同不能直接扩充成通用多任务桥 |
| PR133 `bank` | 独立`linkclose_buffer140`，140路BUF_X16及一位canary；139路用于T数据/索引/valid | 不是存储，不生成地址；任意基址/重排/存储仲裁需新增有源实现 |
| `booster` / `return` | `linkclose_buffer1`同一master的两个物理实例 | 仅电气中继；不存payload、不生成事件、不切断协议循环 |
| M/T/S驱动修复 | 旧版独立副本内部132/140/1个选定BUF_X4→BUF_X16 | 是新物理版本，原生产视图未替换；不能向当前M v2或其他方向转移资格 |
| E op13 | 当前E内部四S32→四S16、RNE与饱和 | 可复用数值转换；外部仍需尺度、有效数、半包及128↔32组织 |
| SystemC上层线程 | 软件事务层显式发命令、搬运、等待及T提交 | 不代表RTL协调器；E模型还缺RTL op13 |

旧桥的准确接线、源代码行及原执行版本见[实现归属审计](SIX_CONNECTION_BRIDGE_AUDIT.md)。候选公共控制与事件合同见[协调机制候选](SIX_CONNECTION_COORDINATION_CANDIDATE.md)。机器清单见[连接与改动索引](../work/Melodydt/151/connection-index.json)。

## 本轮方案取舍

第一版候选优先保持M/N/E/G/R/S/T的已有叶宏RTL，增加明确的外部预制协议wrapper、有限缓冲/分支汇合及协调器；这不是已经批准的物理边界。新wrapper可以作为独立bridge宏硬化，也可以与一组接口共同硬化，须通过面积、负载、引脚和时序比较后决定，不能仅凭RTL module名字宣布硬宏已存在。

缺少通用指数、宽系数或宽归并时，另比较独立数值服务、叶宏新操作、或明确外部系数输入；三者不能靠纯M11/M12连线替代。改变叶宏RTL、driver或接点必须建立新版本并重新验证。

六项的最小控制与验证顺序列在后文。它们是样本覆盖清单，不是数学最小物理拓扑，也不是完整整模型定点质量或吞吐结论。

## 0. 固定来源与适用口径

- 样本算法：main `a103da352b7e431cedc69f54b9f71c05371be1b3` 的八模型精简图，覆盖十种代表层。图以 FP32、B=1/S=2、无历史缓存的导出为主要验证条件；Llama 是配置重建/随机参数；文字图不是可执行 IR。不能从图推定整模型定点质量、decode 历史状态或系统吞吐。
- 七宏：PR #144 `5e787714362d957b79c2997141cf05eeebb85afc`。M/N/E/G/S/T 有当前合同下逐宏资格，R 尚未取得当前最终物理资格；这些资格不是本稿所列整链资格。
- SystemC：PR #146 `4ad1ad4643d08cabf2fcc35e9465424556b1f325`。无时钟事务模型，尚未实现 RTL 协同仿真/形式等价；其 E 仍只有 0–12 运算，枚举值 13 是顺序 Reset，未覆盖 RTL 的 op13。
- 旧专用消费者只作为控制和整数算法参考：同一七宏快照中还可读到 `attention106.sv`、`m106.sv`、`mfront106.sv`、`norm106.sv`、`r106.sv`、`gdn109.sv` 等。它们使用不同库存、格式及外存合同，不能被描述为本次七宏拼接实现。

以下箭头表示任务间数据依赖，不默认是零成本直连。需要注明来源端口、目标端口、格式、分块、握手及物理路径后才能成为硬件连接。

## 1. 统一的改动归属原则

| 归属 | 合适的内容 | 本研究中不能省略的成本/边界 |
|---|---|---|
| 现有宏内部 | M 点积/部分和/缩放提交；N 统计/Softmax/Norm；G 激活及紧邻门乘；R 状态/历史及提交 | 如改数值合同、操作码、状态或端口，成为新版本，重做受影响功能/模型/物理验证；不把这些运算重复搬到 bridge 再隐藏成本 |
| 外部预制 wrapper/bridge | 命令翻译、4×S32 容器和 S16 紧凑流的组织、128↔32 分拍、有限缓冲、地址和布局生成、标签/错误保持、分支汇合 | 这些均为有源逻辑，须在共同底座冻结前实现；寄存、队列、仲裁、RAM 端口及长线驱动全部计价 |
| 显式数值服务候选 | 通用负指数、宽系数运算、S32/S64 加权归并等现有宏未覆盖的能力 | 不能泛称“协议桥”而假定它已经存在；可比较新增 SFU/计算宏、扩展既有宏、或明确外部服务三种边界 |
| 协调器/任务表 | 模式、地址、形状、有效长度、量化单位、上下文/版本、依赖、bank 所有权、存储生命周期、提交/回收 | 任务表能调用已有运算和线路，不能创造缺失的数据通路、端口或精度；任务/事件存储与控制器硬件仍需预制和计价 |
| 纯后定制金属 | 在已存在的合法 M10 端点及获批准的有源适配端口之间连接 M11/M12 | 不能新增 FIFO、MUX、转换器、地址生成器、时钟/电源资源或计算单元；静态布线也必须通过实际负载/RC/时序检查 |

第一轮建议优先复用已有宏的运算，补外部有限适配与协调规格；确实缺少数值能力时单列新服务或宏修订决策，不能预设所有改动都能放在 bridge。

## 2. 常规注意力

### 已有方案内容

- M 支持投影、QK/PV 所需 S8/S16 乘法、分块和完整结果缩放；N 有完整 Softmax 流程及非负 S16 Q1.14 最终概率。
- E 有偏置、缩放、选择/mask 所需基本运算及相邻配对 RoPE，op13 可把四个 S32 读出容器转为四个 S16。
- S 有四 bank 16KiB 和实际 A128/B512 供数器；T 有 6KiB 的单批次结果交接。
- 旧 `attention106.sv` 实现了专用 Q8/KV16 注意力控制，含实际多遍 Softmax、外存 K/V/LUT 访问、P15 及共享算术服务。可参考其访问顺序和独立观测，但它不是 N 的 Q1.14 协议，也不是七宏 M/N/E 的既有连接。

### 候选控制步骤

1. 为输入、Q/K/V、分数/EXP、概率、PV 输出和残差分配有限地址及生命周期，选择一个 query/head/tile 的执行范围。
2. N 完成输入 Norm；S/访问器按 M 的 A/B 格式和行、tile、bank 元信息装载，再由 M 进行 Q/K/V 投影。
3. 对 Q/K 施加所需的额外 Norm、RoPE、偏置和缩放；生成/取得 cos/sin 及 mask。保持 V 与对应头/位置的身份。
4. M 分块算 QK；按明确的累加完成边界才缩放、mask、转为 N 所需 Q5.10 分数；不得对每个 K 片独立 Softmax。
5. N `BEGIN→STATS*→FINALIZE→EXP*→FINISH_EXP→SOFT_REPLAY*`。S 或外部存储实际保存/重放原分数与 EXP；N 没有整向量缓存。
6. 将 Q1.14 概率作为 M 的 S16 操作数，以合法布局与 V 供数做 PV，再复用 M 完成输出投影，最后 E 加残差。

### 数值/布局及缺口

- M 的 op5 即使选 S16，响应仍是四个 S32 容器；E op13 只给出低64位四个 S16，高64清零。需要适配器合并两个半包或按明确 count 消费，不能当八个有效 S16。
- RoPE 只支持局部相邻配对。模型的前后半区配对、Transpose、GQA 共享头、Phi 的融合 QKV 和部分 RoPE 需要地址/布局/旁路方案；单纯 Reshape 仅在实际布局允许时可不搬数据。
- scale、mask 有有限数值编码；FP32 的负无穷不能自动落到当前有限 S16 合同。需要独立整数参考确认裁剪和误差。
- Qwen3、Falcon 的 `Q_heads × D` 不一定等于 H；Granite attention_multiplier=0.015625 不能换成默认 1/sqrt(D)。
- N 最大计数65535不表示整行能驻留S。仅65535个S16就需131070B；外存供给及分块回放必须实际存在。
- 历史 KV decode 读写、窗口访问和缓存发布需另加版本/顺序合同；图册未验证非零历史 decode ONNX。

### 改动归属与候选验证

- 先保留 M/N/E 运算内部；wrapper 负责 readout→紧凑流、S/A/B布局、有限 fork/hold/join、QK与PV阶段切换；协调器维护完整行统计屏障和缓存身份。
- 选择 Llama/Qwen2.5 的小头作为最小路径，再覆盖257键长度、尾块、GQA复用、mask全负/有限极值、随机背压、跨 query/context 错配拒绝和 reset。
- 对同一固定资源报告数据字节数、S端口占用、回放次数和存储峰值；不能把七宏单测或旧 attention106 的结果作为整链通过。

## 3. 额外 Norm 与布局变体

### 已有方案内容

- Qwen3/Gemma/Qwen3.5 的 Q/K Norm 可复用同一个 N；Gemma 的注意力后和 FFN 后 RMS0 也在 N 的功能域内。
- N 支持 RMS/L2、外部 gamma 回放和一次一个统计上下文；E 可做 gamma=1+weight 的准备及必要转换，但其 S16 饱和边界必须计入。
- 旧 `norm106.sv` 提供 H1536/H2560 的专用流式 gamma 控制及分母观测，可参考“全行统计完成后分块读 gamma”的生命周期；其 S32/共享算术与本 N S16/U64 合同不同。

### 候选控制步骤

1. 主路径输入 Norm 后发投影；Q/K 投影结果单独分配 head 向量范围，锁定 N 的当前上下文。
2. `BEGIN(RMS/L2,epsilon)→STATS*→FINALIZE→REPLAY(x,gamma)*`；全部统计完成后才回放。每头Norm和跨整个H/4096通道Norm不得混淆。
3. Q/K Norm 输出重排到 E 的 RoPE 配对布局；Gemma后置Norm输出与保存的残差在E汇合。
4. 同一N切换下一头/下一归一化位置前确认回放完成；错误不将未完成统计当作可复用空闲上下文。

### 改动归属与候选验证

- Norm平方/分母/根/缩放仍在N；gamma生成、地址、Norm范围和旁路放wrapper/任务表；没有证据要求为每一处Norm复制N。
- 第一版先以外部固定 gamma 准备和带用途标识的地址表供给；若把gamma=1+weight放E，应验证单位和饱和，不能任意替换FP32加法。
- 覆盖128/256头、H2560、RMS0和L2不同语义、gamma尾块、零向量/epsilon、两个上下文交错请求拒绝；验证内存预算和S宽读优先期间的窄口等待。

## 4. 门控 FFN 与动态专家内部路径

### 已有方案内容

- M 做gate/up/down投影，G两路激活并可在同一流水执行紧邻门乘，E提供转换/基础算术，S/T保存中间值与残差。
- G的`in_x`应是gate投影，`in_gate`应是up投影，SiLU/GELU作用的输入不能对调；两路激活不等于E的八路吞吐。
- 旧 `vprep97.sv` 与 `m106.sv/mfront106.sv` 提供受限 Granite K512、八专家、H1536 的真实“SiLU→S32 MID→整K动态A8/scale→驻留M→merge/residual→流式Norm”方案；可参考动态量化屏障、owner/version/epoch和排空，不是本G/M完整FFN连接。

### 候选控制步骤

1. 一个M时分计算gate和up，或Phi融合gate_up投影后按布局拆分；保留前一个分支，不能被下一次M结果覆盖。
2. 明确每个分支的数值单位，M读出后用E op13或已证明适配转为G的Q5.10，按2元素包汇合相同token/tile的gate与up。
3. G选择SiLU或GELU_tanh、使能门乘；保持激活函数、gate数据、尾部有效数和错误随同一包传递；输出受背压时整个流水冻结。
4. 采用固定S16直接给下投影，或采用显式整K动态量化方案。后者必须先完成完整范围扫描和scale发布，不能按小包各自决定delta后拼成一个M输入。
5. S实际组织A输入，M算down，必要后置N，再E与残差汇合；T按完整批提交/释放。

### 改动归属与候选验证

- 激活及紧邻门乘留G，投影/归约留M。2lane↔8lane打包、分支保留和S布局在预制wrapper，token/tile配对与bank版本在协调器。
- 固定S16是可研究的基线，不表示整模型误差已经接受；动态A8/scale若需要，是额外真实统计/控制/缓存能力，不能只在任务表写“量化”就视为实现。
- 覆盖串行两投影与融合投影、G两输入故意错序、长K、饱和、不同激活及随机背压。对动态量化单列整K扫描、scale生命周期和下游错误接收用例。

## 5. Qwen3.5 GDN

### 已有方案内容

- R有四抽头卷积、GDN更新、S32活动/影子状态、Q/K Q1.14、beta/decay UQ1.31和显式commit/revoke；N可做Q/K的L2及读出的RMS；G可做SiLU、Sigmoid、Softplus及输出门乘。
- E op13是现有R S32读出到S16的明确转换资源，但需要调用方声明尺度，且可能饱和。
- 旧 `gdn109.sv` 是不同的完整双head S32专用控制参考，含宽服务调用、重标和原子根发布；它通过外部协议读取decay/beta等系数，并不证明七宏已经生成这些系数。

### 必需路径与候选控制步骤

1. 输入Norm后，M产生QKV、Z、beta原量和dt原量；供给卷积历史、卷积权重及R活动状态。
2. R先做卷积，读出候选结果并保存，E转S16，G执行SiLU；按Q/K/V切分、重排和head映射。Q/K进入N做L2，按R的Q1.14合同准备后装入R；V按R当前S32单位准备。
3. beta侧调用G Sigmoid；dt侧调用G Softplus，并计算A*dt及负指数decay。此系数管线当前未在七宏内闭合，见下节。
4. 完成所有Q/K/V/beta/decay的就绪事件后发R GDN；检查错误及候选输出。候选状态尚未commit时读到的active state仍是旧状态。
5. 读取R候选输出到持久缓冲，再经E转换和N做每value-head RMS。
6. N结果接G的`in_gate`；G的`in_x`来自独立Z投影，执行SiLU(Z)*Norm(R)。之后M输出投影、E残差。
7. 卷积history与递推状态按明确的token提交边界共同commit；失败处理必须覆盖早先卷积留下的pending_history。commit清output_valid，不能先commit再读op12。T输出发布与R状态提交的跨宏原子性尚未定义，不能只说“两者commit”就认为全局原子。

### 系数与数值缺口

- G的Sigmoid输出Q1.14；R beta要UQ1.31。将已量化的非负码左移17位可以改变编码容器，但不能恢复丢失的精度；是否满足算法参考要独立验证。
- G的Softplus输出Q5.10；现有E普通运算输出S16，不能默认产生R需要的任意S32注入或UQ1.31 decay。
- N的EXP必须处于统计final后的Softmax上下文，减保存的maximum、限制计数，且输出UQ1.15；G没有通用EXP。不能默认把N当独立UQ1.31指数SFU。
- 候选选择应显式比较：新增已预制系数服务；扩展G/N/E相关操作并重新验收；或规定外部已版本化系数输入。最后一种只能声称“系数输入切片”，不能声称端到端GDN系数由芯片生成。
- Q/K L2的输出尺度、1/sqrt(128)缩放、head重复和S32状态单位均要绑定整数参考。单纯将S16数值接到Q1.14端口可能相差二进制尺度。

### 改动归属与候选验证

- 状态更新、范围检查和bank提交保留R；布局、读出保持、opcode翻译、Q格式容器准备放wrapper。真正缺失的指数/宽算术须归入显式数值服务或宏修订，不能藏在纯金属或无成本bridge中。
- 验证卷积→SiLU→L2→递推的往返路径以及R→N→G输出路径；检查Z/Norm的G输入角色、迟到响应、错误beta/decay、pending_history撤销、重复commit、epoch耗尽。
- 分开验证“已给系数的R切片”和“由投影原量生成系数的完整控制链”，后者不得拿前者的测试数量抵充。

## 6. Falcon SSM 与并行混合层

### 已有方案内容

- 同一R有SSM逐元素衰减、注入、readout/skip及卷积模式；N/G/M/E可承担外围投影、激活、门控和Norm。
- 旧 `r106.sv` 从外部系数记录读取dt/alpha/skip，执行专用完整head状态计算与提交；其中“输入系数已准备”这个边界必须保留。旧 `m106.sv` 等可参考共享存储/算术的owner和排空规则，但不是七宏协议。

### 候选控制步骤及真实R顺序约束

1. 输入Norm分别进入注意力支路和SSM支路；单实例时可时分执行，必须保存中间结果，不能要求并行图就必定复制所有宏。
2. SSM支路经M投影与MuP缩放分成Z、XBC、dt，明确Slice、广播和各段单位。dt需Softplus、Clip、A*dt负指数；B*dt/X等注入准备及skip系数供给不能省略。
3. 若同一个R完成卷积和后续SSM、且希望history与state共同提交，候选调度须先在无pending时装完active state、卷积history/taps及本轮逐元素decay，再运行卷积。理由：R的op1/state和op15/decay在pending_history时均拒绝，而卷积完成会置pending_history；这条顺序需实际组合验证。
4. 读卷积候选输出→E格式转换→G SiLU→切分X/B/C，装R的key/query、x/inject/参数；发SSM时检查本轮decay有效位齐全。R执行状态计算会消耗decay有效性，每轮需要重新装载，不可因bank翻转复用旧因子。
5. 成功后先读出并保存R候选输出。G的激活输入来自Z，门乘另一输入来自R读出；G输出之后才进入N，且是跨4096通道Norm，不能改为先Norm或每head各自Norm。
6. M输出投影及缩放后，与注意力支路在E汇合，再加原残差；两个分支必须具有匹配token/位置/版本。
7. 明确SSM/history的commit/revoke和整层输出的发布边界；后续状态运算失败可能留下早先成功卷积history，必须显式处理。

### 改动归属与候选验证

- 复用R状态核心、G激活、N全组Norm；新建有限布局/广播/半行打包/标签保持，系数生成同GDN列为显式数值能力决策。
- SSM的逐元素UQ1.31 decay、S32 inject/skip、整head范围检查不能靠将一条S16线接到S32口完成。E只有op13宽输入缩窄模式，不是通用S32向量算术。
- 验证完整“先装decay→卷积→SiLU→SSM→读出→共同commit”序列；另做错误顺序拒绝、history残留撤销、G输出全4096元素统计屏障和两个并行语义分支的乱序完成join。

## 7. Granite MoE

### 已有方案内容

- M可做router和专家投影；N有40选8及Softmax；G可做专家内部SiLU/门乘；M或另行定义的宽归并能力承担加权求和。
- N TopK输入是最多40组S16 score/U16 ID，最终响应仅含8个U16 ID。RTL的TOP_SAVE将best_id写入chosen/rsp_data，不返回selected logits或原位置；不能把TopK响应直接当8个分数送Softmax。
- 旧 `m106.sv/mfront106.sv/vprep97.sv` 提供固定Granite专家计算、动态A8及归并控制参考，但router/TopK/gather等边界与七宏实现不同。

### 候选控制步骤

1. M算40个router logits，按明确的S16量化单位保存原score表并向N装入(score,ID)。首版将expert ID约束为唯一0..39，并验证该约束。
2. N TopK返回ID；wrapper/访问器按ID从保留score表取出selected logits，再建立独立N Softmax上下文，产生8个路由权重。若允许任意或重复ID，仅凭ID无法总是恢复所选原记录，需要返回位置/score或定义更强规则。
3. ID进入专家地址计算及权重访问器；token数据按assignment复用/复制，专家逐个或分块用M/G执行。动态ID改变访问和任务，不要求运行时重接物理线路。
4. 保存token/rank/expert/scale/version的映射，专家输出乘路由权重并累加回正确token。完成所有top8返回后才能发布该token的合并结果。
5. 施加Granite的0.22缩放及残差，释放专家临时缓冲。重复调用同一M时保留未合并结果，不能假设8专家并行实例。

### 数值/存储与归并决策

- 唯一0..39 ID下，40个S16 score共80B，可放显式S地址区；不必修改N返回格式。若支持任意唯一U16 ID，另需显式ID映射；40组(score,ID)为160B，不能隐去。
- 仅保存选中ID不等于已实现Gather、专家地址、权重调度、加权ReduceSum或ScatterAdd。
- 专家输出可能为S32/S64；现有E普通乘法的最终输出仍S16，不能当作任意宽的加权归并器。
- 可研究把每专家权重并入M的合法缩放/完整结果追加，或新增明确的宽归并服务。前者必须证明量化单位、系数组合范围、一次RNE位置、行/token分配及溢出合同，不能默认浮点分配律等同当前整数合同。
- 独立宽归并服务是新计算/状态资源，不是“只是一个MUX的bridge”。若只研究S16饱和归并基线，必须明确数值质量限制。

### 改动归属与候选验证

- 第一版建议N保持TopK ID接口，score保存/gather及专家地址放外部预制访问/协议服务，调度程序控制专家顺序；若将TopK返回扩为(score,index,ID)，应作为N新版本重新接收并同步SystemC。
- 验证40选8的tie、ID合法/唯一性、同一token多专家、专家乱序完成、有限返回槽满、不同token不能互相累加、路由权重与expert rank配对、未完成top8禁止发布及宽累加溢出。

## 8. 六项共用接口与验证前置

1. 定义有限、带版本的张量/任务描述：token、head/channel范围、tile、元素格式/共同尺度、长度、源/目的地址、实际线路、bank及错误/饱和语义。不能假设这些标签已经是现有宏端口；wrapper持有或随外部队列传递。
2. 区分命令接受、计算完成、数据写入并可见、R/T提交、消费者完成及资源释放。S的done只表示装载数据已交给M，不是M计算完成。
3. S宽读优先于窄访问，连续供数没有窄口无饥饿保证；任务表需安排N/G/R/T与补料的访问窗口。控制器不会凭软件创造第二个端口。
4. 对N多遍回放预留完整统计屏障、有限持有缓冲和输出空间；对fork/join记录剩余消费者/引用生命周期。只连valid/ready不自动解决有界队列环路死锁。
5. T单批最多384×128bit，完整Sealed/Commit/Take/Release，不能用6KiB替代任意长结果存储或假设双缓冲并发。
6. 补SystemC E宽输入转换操作及独立原始32位运输字段/RTL opcode映射；不能将现有Reset=13直接当RTL op13，也不能用a[8]的S16字段假装保留四个S32输入。
7. 本轮先制定oracle、最小分块组合与拒绝用例；真实仿真需固定版本、按项目服务器/Slurm规则另行执行并提供启动追踪回执。当前没有新增仿真结果。

## 9. 固定版本证据入口

- [样本图与证据范围](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a103da352b7e431cedc69f54b9f71c05371be1b3/docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md)
- [七宏数值/接口/容量合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/docs/BLOCK_V2.md)
- [S供数和旧M组合合同（历史M合同不能覆盖M v2）](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4dd994bf256c1a3a16163756a3a486139984ecff/docs/BLOCK_FEED_V1.md)
- [N RTL：EXP上下文与TopK仅ID响应](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_v2/block_v2_n.sv#L222)
- [R RTL：pending、载入/执行、读出与commit](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_library_v1/block_v1_r.sv#L111)
- [E RTL：S32输入解释与op13](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_v2/block_v2_e.sv)
- [G RTL：两输入角色、四级流水及背压](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_v2/block_v2_g.sv)
- [SystemC E尚未覆盖op13](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4ad1ad4643d08cabf2fcc35e9465424556b1f325/project/systemc/include/blocks/e.hpp)
- [专用注意力控制参考attention106](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/shared_services/attention106.sv)
- [专用V/M/Norm接续参考m106](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/shared_services/m106.sv)
- [专用流式gamma参考norm106](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/shared_services/norm106.sv)
- [专用Falcon状态参考r106：系数来自外部记录](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/shared_services/r106.sv)
- [专用GDN参考gdn109：不同宽算术和元数据合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/shared_gdn/gdn109.sv)
