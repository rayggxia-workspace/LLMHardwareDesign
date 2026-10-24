# Issue72 Falcon完整整数R分支候选

本目录由task/72-falcon-chain开发；真实模型/数组数学只在授权服务器Slurm运行。只读复用Issue70原始BF16权重与cal16/eval72真实layer0输入，不新增下载、不重跑整模型。前批head0 FP64更新下的S16/S32各4次饱和原样保留。本批并非简单给旧结果换标签。

## 冻结边界和决策

闭包从真实layer0 input/residual的固定I32Q12编码开始：完整H2560 input RMSNorm → SSM输入MuP → 完整K2560 W8A8 in_proj → 每坐标MuP/RQ → 完整4608通道×conv4及SiLU → dt/alpha LUT → 全32head×D128×N256整数递推 → 完整4096维gate后单group RMSNorm → 完整K4096 W8A8 out_proj → ssm输出MuP → 外部A编码加MuP、residual+A+R三输入join → 完整H2560 pre_ff RMSNorm。

Attention是明确外部I32Q12切口，MLP在闭包外；不能声称整模型整数化、真实INT8内核速度、质量验收或PPA。state模式将原native完整projected向量I32Q12作为外部切口，只诊断conv/系数/R/消费者，full模式才串入真实输入norm和完整矩阵投影。两者不得混称。

影响划分的分叉是：(1)R是否能以因果head unit/epoch/受控提交避免发布饱和，代价是多少；(2)R→4096共享gatednorm是否必须保留全组barrier、跨head数据搬运；(3)同数值任务下独立R还是V/R共享，完整M/V/R/S的W8、宽部分和、状态、LUT、重标和事务是否装得下、端口是否争用。服务比较必须按同mode/bits/policy/实际trajectory进行，不能用S16对S32字节差冒充placement收益。

## 候选精度合同

- 常规数据、conv历史、x/B/C、gate、各线性/归一化输出：I32 Q12，不宣称INT16向量硬件。
- 矩阵：W8逐输出校准离线静态scale，用Q31 mantissa+I16 exponent编译；输入仅当前整数row用最小RNE右移得到[-127,127] A8。全K最坏界/实际INT32核验后，Q31宽乘/RNE输出到Q12；无运行时float max/127。
- gamma、MuP、D、conv weight：I32Q20；bias/输入dt：I32Q12。conv四项宽I64积/和，RNE20一次到Q12，再SiLU。
- SiLU LUT：[-32,32]、step2^-8、16385×I32Q12；输入索引RNE、负域外0、正域外identity，所有域外次数保留。
- 联合dt/alpha LUT：每head同[-32,32]网格；dt I32Q20、alpha U32Q0.31，dt先按原配置limit离线计算。域外clip且计数；这是有界候选，不掩盖失配。总LUT payload约4MiB，必须计入只读ROM/backing及真实访问，不免费放进16KiB V。
- 状态：每head S16/S32码+I16 power2 exponent，仅cal16真实native全部32head状态最大值决定初始unit。两位宽各自按完整signed码域和cal最大值选power2 unit，通常exponent相差16、约相同物理span，但端点并非Issue68刻意同端点合同；评价/native误差不参与在线范围选择。
- 递推：decay=RNE31(S×alpha31)；dtB20=RNE12(dt20×B12)，必须I32；inj=RNE(32+state_exp)(dtB20×x12)；proposal=decay+inj。这是明确的两阶段RNE，不冒称和一次三乘精确舍入相同。输出先完整N256做checked I64 C12×new_state码归约，再按state_exp对齐Q12，加RNE20(D20×x12)。
- 所有乘/加/shift先检查I64候选，norm明确U128 sumsq、variance floor division、isqrt(variance<<40)和signed RNE division到Q12；Python整数/isqrt只是软件定义。硬件候选restoring division固定128迭代、isqrt64迭代。S8 lowering为radix128低digit[0,127]、最高signed8，width<=8用1digit，否则1+ceil((width-8)/7)；每digit积、宽shift/add都计数，未声称RTL已实现。

## 因果范围与事务

每bits比较static_sat、static_guard、guard_rescale。static_sat唯一允许clip后发布的诊断，保留所有饱和；static_guard越界整token拒绝；guard_rescale只将当前越界head的私有trial旧态RNE右移1，unit+1，全token重试，最多8次重试。一个重试波次epoch+1；最终拒绝不发布state/unit/epoch/position/output。guard策略的发布饱和必须为0，不等于误差门通过。当前状态/输入和guard是唯一决策输入，不能查看未来native状态。

transactions逐token记录before/attempts/after、每attempt old/proposal/injection/decay hash、units、epoch、guard、commit/abort；initial/final完整state和每步SHA用于独立重算。chunk8/16在边界实际复制/重载整数state和metadata，核state/unit/epoch/version/position/合同checksum；checksum是软件见证，不假设硬件SHA引擎。SHA扫描作为观察者隔离；候选旧态/首trial复制、proposal宽存储、guard、重编码、发布及元数据IO另记，不能免费shadow。

## 阶段与验收

先运行capture补参，compile只在cal/静态权重上生成scale/LUT；state六条件和full六条件可分作业并行。固定原16/72token，逐阶段误差全报，不设置事后挑样或应用质量PASS；整数正确性由独立receiver逐stage/逐状态码/SHA、真实篡改负例验收。原Issue70参考门失败不改写。

~~~text
python -B project/experiments/closure/falcon_capture.py --weights MODEL --capture ISSUE70_FALCON --binding BIND --out NEW
python -B project/experiments/closure/falcon_chain.py compile --capture CAPTURE --binding BIND --out NEW_COMPILED
python -B project/experiments/closure/falcon_chain.py run --compiled COMPILED --mode state --bits 16 --policy guard_rescale --chunk 8 --binding BIND --out NEW
python -B project/experiments/closure/falcon_chain.py run --compiled COMPILED --mode full --bits 32 --policy guard_rescale --chunk 16 --binding BIND --out NEW
python -B -m unittest discover -s project/experiments/closure -p test_falcon_int.py -v
~~~

binding需commit、falcon_chain_sha256、falcon_int_sha256；capture单独falcon_capture_sha256。每out不得存在；manifest冻结全部artifact大小/SHA。reference.npz仅在完整整数执行结束后才读取用于误差报告。编译器原始float reference不可用于运行时分支或scale；这是软件分离合同，独立接收还需重算和源码核验。


## 完整连续历史接续资格（后续phase）

初版phase把conv全序列因果预计算，再恢复R状态；它只证明算子整数链和R checkpoint，**不证明完整conv+R的恢复事务**。初版产物不改写。falcon_resume.py另阶段按token重算完整输入norm/投影、以已提交conv历史生成私有新历史，运行R私有trial和全部消费者，最后才共同发布conv/state/units/epoch/version/position/输出。R本地COMMIT在外层branch_published之前只是私有试算，不是硬件已发布。任一R/consumer拒绝，外层提交描述符不变。

新阶段消费同一compiled及已完成full基准，仅比较整数数组和全部状态SHA，不加载FP reference。分别full、chunk8、chunk16、prefill64+8次单token decode；chunk边界实际保存并重载完整conv和state，以及单位/epoch/version/position/owner/合同。8种真实篡改（state/conv/unit/owner/epoch/position/version/contract）必须拒绝。

conv history=4608×4×I32=73728B；old+private trial=147456B，不能免费送R32KiB。状态完整旧态/私有trial、宽proposal、有限S/backing都另计。checkpoint文件SHA与复制属于资格观察者，单列成本，不混入产品必须每8token执行的流程；持久历史库存及更新IO是必需义务。

~~~text
python -B project/experiments/closure/falcon_resume.py --compiled COMPILED --baseline FULL_GUARD_RESULT --schedule prefill64decode1 --binding BIND --out NEW
~~~

binding还需falcon_resume_sha256；falcon_chain_sha256、falcon_int_sha256按本phase新源重新绑定。fi.scan兼容resume=None默认旧语义；旧已冻结结果仍保留，不能用新source覆盖原run绑定。接续功能的真实资格以服务器逐stage逐码比较和独立接收为准。


## 不能遗漏的宽度与原phase历史限定

完整S32状态码×C32经N256归约的通用最坏绝对界为2^70，保证全码域需72signed bits；当前候选只是实际max-product×N满足I64时执行，超界拒绝，不能宣传I64对任意合法S32/C32永不溢出。alpha UQ31×S32积界2^62可I64；dtB20有独立I32 guard，再乘x32。S16只是状态存储较窄，本候选计算先widenS32，不能自动将其宽乘服务减半。

原phase的conv_history_final_q12属于全72预处理历史；static_guard拒绝后它不是已提交前缀cache，不允许恢复。原phase只核算子整数链和R发布，不核完整历史事务；完整guard-rescale72基准的最终历史可与新phase逐码对照。原失败/字段/manifest不覆盖，新phase的atomic branch接续才有完整历史资格。

同资源服务若统一每token串行加载完整权重，只能称同一保守服务协议。prefill64可做权重tile多row复用而decode不同；72×W8字节不是不可避免下界，不得将未搜索batch/复用的服务称端到端最优。
