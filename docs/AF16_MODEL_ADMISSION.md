# AF16静态样本准入账本与下一实际尺寸实施项

Issue151 / PR152；输入`cd8dfc9a3770f0be04b3e75fe08fe60fd69e47a6`，原生选定源`707878621b2add4ed218b8c43df2e95c9a56e2ba`。本稿与机器账本、`check_af_model_admission.py`共同交付：保留八样本真实尺寸和十层型，逐一判断当前A16/F16/AF16是否匹配，再明确下一项可以实施的真实尺寸程序。本审阅未运行RTL仿真、推理或服务器操作，没有读取/修改ref-project。

**当前唯一静态ALLOW是人工声明的合成有限配置`synthetic_af16_h8_sq2_i8_v1`。八真实样本对A16/F16/AF16的24项整体结论全部为GAP；各自数值、质量、实际参数/供给仍分别标UNKNOWN。** ALLOW只说明固定ABI匹配，不能替代RTL、模型精度、物理或全模型验收。

## 1. 可执行检查实际做什么

安装后默认读取仓库内`work/Melodydt/151/af16-model-admission.json`。它核对22份现有输入的路径/字节/SHA、六个W0角色分片和172条目录、FamilySpec八模型/十层型、coarse模型维度、graph源索引及当前AF包装源SHA。原图原始快照不重复上传；图ref/路径/SHA保留在锁定索引，本次作者读取并核对选定精简图快照。检查器不会把未随仓库提交的全部raw graph当作已重读。

每个真实模型使用锁定FamilySpec事实计算条件，不采用请求者自报的H8。条件涵盖H/I/head/GQA、Norm/额外Norm、bias/QKnorm/gate/源gain、RoPE、epsilon、整数格式/质量、N group、存储与参数镜像。模型身份若是Qwen3，即使请求写H8/I8，也仍以H1024/I3072评估并额外给出NO_DOWNSIZE。账本缓存的逐条件结论必须和检查器重算一致，不能仅修改结论为ALLOW。

正/反例的预期标签和拒绝rule ID为按冻结ABI手写的常量，检查器不从自身输出生成期望。24个静态例子包括1个合成ALLOW、22个GAP及1个未知模型UNKNOWN：错位宽/Fin/H/I/head、两gamma误别名或交换、参数bank长度/末gamma槽、A尾/F首格式不一致、最终格式、额外RNE3窄化、错误causal前缀、信任host padding、错误last、跳过A DONE、bootload及真实模型冒名缩形。它们验证离线准入逻辑，不是协议状态机、算术质量或RTL测试。

正式目录命令：

```powershell
python -B -X utf8 scripts/check_af_model_admission.py --root .
python -B -X utf8 scripts/check_af_model_admission.py --root . --model qwen3 --target AF16
```

第一条应输出`PASS_STATIC_ADMISSION_CHECKS`并exit0；第二条应输出真实H1024/I3072、GAP并exit2，这个非零码是正确拒绝。`--request`读取完整静态请求JSON；相对路径按`--root`解析，ALLOW退出0，GAP/UNKNOWN退出2，源锁/格式/例子不一致退出1。默认AF包装路径为`project/rtl/block_connection_w4/block_w4_af16_top.sv`；草稿运行使用显式`--ledger`和`--wrapper`绝对路径，正式复制后无需修改脚本。

## 2. 当前固定合同与实际样本的差别

A16是H8/Sq2/D8/一Q头一KV头、无bias/cache、普通RMS、相邻pair RoPE及causal count1/2；F16是H8/I8、每次一行、普通RMS+SiLU门控。二者hidden均S16 Fin10、权重S8 Fin7、gamma S16 Fin10、epsilon_code1。AF16将A两行逐bit保存并依次送同一个F16；没有RNE3/clipS8。

| 样本 | 真实H/I | Q/KV/D、GQA | Norm/激活及关键额外项 | A16/F16/AF16 |
|---|---|---|---|---|
| Qwen2.5 | 2048/11008 | 16/2/128，×8 | RMS/SiLU；QKV bias | GAP/GAP/GAP |
| Qwen3 | 1024/3072 | 16/8/128，×2 | RMS/SiLU；Q/K逐头RMS；Q宽2048≠H | GAP/GAP/GAP |
| Llama重建 | 2048/8192 | 32/8/64，×4 | RMS/SiLU；Llama3频率；随机/重建来源边界 | GAP/GAP/GAP |
| Gemma local/global | 2560/10240 | 8/4/256，×2 | RMS0/QKnorm/postAttention/postFFN Norm；GELU_tanh；局部window1024 | GAP/GAP/GAP |
| Phi | 3072/8192 | 24/8/128，×3 | RMS/SiLU；融合切分、96/128部分LongRoPE | GAP/GAP/GAP |
| Qwen3.5 | 2560/9216 | global 16/4/256，×4 | RMS0/QKnorm；64/256部分RoPE与输出gate；24D+8A_gate | GAP/GAP/GAP |
| Granite | 1536/每专家512 | 24/8/64，×3 | RMS；源score/gain；40选8 X，不是完整F专家 | GAP/GAP/GAP |
| Falcon | 2560/6144 | 10/2/128，×5 | H共享Norm/Attention+SSM join；SiLU前后MuP | GAP/GAP/GAP |

源导出B1/Sq2/FP32/use_cache=False与当前小prefill长度相符，只给相应条件ALLOW，不表示真实模型运行时长度已被接收。源max_position不是硬件context上限。所有真实hidden整数位宽/Fin、权重/gamma的可接受量化镜像、布局/版本、误差阈值及生成质量仍UNKNOWN。

epsilon必须随输入单位确定：Fin10的code1为2^-20。配置中多数样本1e-6、Phi/Falcon为1e-5，均不与该固定值精确相同；近似是否可接受须另出数值证据。RMS0的gamma=1+weight、Gemma非线性/额外Norm、模型split-half/partial RoPE/系数/位置规则不会由128bit端口自动适配。

## 3. 下一实际尺寸：优先Qwen3完整F行H1024/I3072

优先理由是它具有样本中较小的普通dense H/I、普通RMS+SiLU，没有Gemma GELU/postNorm、Falcon MuP或Granite专家dispatch。**目标保留真实H1024/I3072，不能把量化质量UNKNOWN改写成已准入。** 先取现有来源的真实层输入/参数，选择并接收hidden/weight/gamma Fin、epsilon code和各stage舍入/clip阈值；不能因为当前F16为Fin10/7就认定训练参数也适合该单位。先做独立整数参考及FP32误差/clip统计，再进入实际RTL资格。

在S16 hidden/gamma/mid和S8 weight的候选宽度下，可提出如下**尚未实施/验收**的固定片上分配：

| S字范围 | 内容 | 字节 |
|---|---|---:|
| 0..127 | 原X，H1024 compact | 2048 |
| 128..255 | gamma | 2048 |
| 256..383 | 全H Norm结果 | 2048 |
| 384..767 | 全I3072 compact mid | 6144 |
| 768..895 | 完整H输出 | 2048 |
| 896..911 | K32宽A staging，含loader实际padding | 256 |
| 912..927 | 8输出列×K32的S8 B staging | 256 |
| 928..931 | gate/up/mid/down各8项scratch | 64 |
| **共0..931** | **932字，剩92字不预先借给别的任务** | **14912** |

T输出128字/2048B。这里不要求9MiB权重驻S，也没把紧凑X数组直接冒充loader布局。rows1/K32采用4个K8 tile，每tile宽A仍是完整4×128bit容器组：每个256B A staging只有64B有效S16值，其余实际零/已证明无效容器按合同处理；B staging四tile共256B，8列n-major、k-minor。

N controller须接受count1024，words_hold=128至少8bit、index至少7bit（可统一8bit），并同步修正所有原6bit相关拼接、remaining、lastword、地址offset/扩展加法与准入检查；只改count guard不够。native统计count16bit范围够这个组，但必须先收全H统计再用同一factor回放，不能把H切成独立RMS小组。

单M调度按I方向每8项依次完成：gate的完整H1024归约→保存gate8；up完整H归约→保存up8；G门乘→compact mid；384个tile全完成后才启动down。down每8个H输出连续消费全部I3072，再统一RNE/clip及原X残差。K32时，gate/up各384个输出tile、各32个归约chunk；down128个输出tile、各96个chunk，未优化基线共36864次EXEC/行。这个数不是ROM长度或工期估计；固定程序可使用有界循环。**不能在保留down partial时复用同M计算下一gate/up，也不能逐K chunk窄化再求和。**

候选S8三矩阵参数总计9437184B=9MiB；需要真实可达版本、固定有序的provider/host chunk流、槽位预约及实际ACK/错误/晚响应规则。当前13字参数bank不具备这种供给能力，不能只加大数据文件。以上地址与程序是下一实现对象，不构成现有硬件mapping或质量通过。若数值接收要求改成更宽数据，这份容量候选必须重算。

## 4. 后续优先级与冻结门

第二项优先Qwen3真实Attention：复用H1024长RMS与供参能力，增加Q/K headNorm128、Q宽2048、GQA2、D128归约与模型RoPE pair/位置映射。头内128项在原N算术/现有有界controller范围内，但多头整体程序和存储不因此自动具备。

第三项可比较Llama普通A/F的算子路径与Qwen2.5 bias路径：Llama无QKnorm且算子较近，但H2048/I8192和Llama3频率要另映射，且其来源只有重建随机参数；Qwen2.5有真实参数来源但bias、GQA8和I11008增加工作。再逐项接收Phi、Gemma、A_gate以及H/X/D的源特有路径，不能用“同样是A/F”消除额外Norm、部分RoPE、gain或mixer边界。

每次扩展须新增有限profile版本、真实尺寸与全部永久程序、参数镜像/供给和容量证书，再改变准入表；未知模型仍不自动可用。role/Fin/layout主要为编译期契约，不增加通用每包role/大handle，也不允许各产品另综合有源控制器来补缺功能。

## 5. AF包装源码独立审阅

已读`block_w4_af16_top.sv`，SHA `96a36f39843d6195169591676371642420c096d37dbe190c94c516495677889c`。未见当前有限合同的阻断：

- 父running由父start建立，覆盖A_START/F_FEED中子尚未start的取消；RUN abort产生父error，不等待不存在的prestart子DONE。
- frame_seen只在实际子输入握手后置位，区分初始空闲与异常丢帧；40拍接受且A真实stored建立后才parent stored/start。
- 参数bank[0..11]为F权重、[12]为F gamma；A gamma仍在原A帧word24。两行A结果独立hold，整RUN期间禁止新frame覆盖。
- A捕获两输出并消费正常A DONE后才喂F；每行17拍及真实stored→start→输出→正常F DONE后才下一行。父首尾格式保持S16 Fin10，没有RNE3桥。
- sat按当前started及对应输出/DONE阶段观察，避免上一帧/上一行stale flag；已有父DONE遇abort保持flags，ready同拍一次消费。
- 非法子metadata不发布；已消费row0在row1错误时不可回滚。父不新增T，也没有提供一般L5 stored ACK网络。

显式holding为13×128bit参数+2×128bit行数据=1920bit/240B，控制状态另计。实际实例M2/N2/E2/G1/R0/S2/T2；两S各16KiB、两T各6KiB，不能按任务预约缩小物理宏。正常预算为A103+2F39=181普通S（131W/50R）、M72/N28/E10/G2、loader12/512bit读26、子T take4/release3，外部输出2；aggregate相等不替代逐阶段握手与错误测试。

## 6. 本次实际验证与限制

已实际运行离线checker：exit0，`PASS_STATIC_ADMISSION_CHECKS`；22份既有源+AF包装SHA、24个手写标签正反例、八模型×三target逐条件表一致。只有1个synthetic ALLOW，22反例GAP、1未知模型UNKNOWN；真实24个结果均GAP。独立CLI调用`--model qwen3 --target AF16`正确exit2并报告H1024/I3072。管理结构检查实际PASS，仅管理结构。

这些检查没有执行RTL、原模型量化推理或协议状态机仿真。既有A16/F16功能结果沿原报告保留；本轮AF执行结果由根按真实作业与回执另补。完整LLM的embedding、finalNorm、LMhead、sampling、MTP/多模态仍不在当前A/F准入内。
