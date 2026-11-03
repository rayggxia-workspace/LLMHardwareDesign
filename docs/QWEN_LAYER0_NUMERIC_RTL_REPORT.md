# L4真实Qwen3 layer0 F：数值诊断与有限RTL验证

Issue151/PR152，Melodydt；输入71c819c2。取数源码92989582，数值源码d0c40f57，实际RTL源码f7fc7614。本轮新增一个静态参数顶层和一个文件驱动TB，旧44份RTL/TB/include逐字节不变。当前仍L4，L5、真实完整A、产品程序永久金属绑定及PPA未完成。

## 本轮结果与边界

官方公开Qwen/Qwen3-0.6B固定revision c1899de289a04d12100db370d81485cdf75e47ca的layer0 11个BF16张量和14个embedding行已真实提取、转FP32并移交本人服务器。数值作业95247/node1/c64/8CPU自然COMPLETED0:0/1:02；RTL95248同配置自然COMPLETED0:0/1:49，四条完整H1024/I3072整数行分别7项检查通过，4条9437184B actual accepted权重流SHA与独立canonical一致。它们证明有限真实数据的整数执行，不接受整模型精度或物理实现。

数值输入是4个明确vocab-piece前缀，每个4token，cal/eval各2前缀。真实embedding及layer0权重经过独立FP32完整Attention（Q16/KV8/D128、Q/K RMS、split-half RoPE、GQA2、causal、Wo及原残差）得到F切口Y；再评估F(Y)。每split8token×1024=8192个输出元素。不是自动BPE/chat模板、代表性语料、28层推理或与官方Torch/BF16逐bit等价；这些门仍待完成。

## 来源和数据链

model.safetensors文件总1503300328B，官方expected LFS SHA f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b。仅按206 Range读取所需tensor和embedding行，完整文件没有下载/实算SHA；不能把expected写成verified。每个所需BF16和F32文件都有实际SHA，全部BF16→F32 scalarbit展开在服务器再次验证。官方config/vocab/tokenizer_config完整小文件按Git blob核验。它是本轮明确选择的官方revision，不声称与历史未锁revision的导出checkpoint完全同字节。

服务器HF直连超时，本机公开Range可用，故先本机提取再安全传本人目录。58个数据文件、97362511B未压缩数据的转移SHA均核对；原始参数、F切口/矩阵/流和构建只保留在本人服务器任务data01/runs下，不上传Git。脚本、sourcecommit、工具版本、精确命令、实际输出路径和SHA见[实验索引](../work/Melodydt/151/qnum/evidence-index.json)。无需借用其他成员目录或凭据。

## 数值比较：不据cal平均指标接受产品尺度

| 配置 | X/Norm Fin | 三矩阵Fin | epsilon码/M READ右移 | eval RMSE | eval relative L2 | eval max绝对误差 | 权重clip |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| 当前基线 | 10/10 | 7/7/7 | 1；7/7/7 | 0.01477456 | 5.8247% | 0.09690666 | 0/0/0 |
| 安全W8候选 | 10/10 | 8/8/8 | 1；8/8/8 | 0.00746166 | 2.9417% | 0.03862415 | 0/0/0 |
| cal-only选中W9候选 | 12/12 | 9/9/9 | 17；11/11/7 | 0.00672735 | 2.6522% | 0.36110115 | 53/5/24 |

G的gate/up/mid保持Fin10，down与原残差同XFin。epsilon码按源1e-6×2^(2XFin)舍入，Fin12码17的有效epsilon约1.013279e-6，基线Fin10码1为2^-20。完整K归约后才RNE/clip，不能每chunk窄化。8个预声明候选仅用cal输出relative L2排序，冻结选择后才统计eval。Fin14导致可表示输出范围约±2及clip，说明增加小数位不是免费提升精度。

选中W9平均误差较小，但最大误差较基线和W8更大，且三矩阵共82个权重被截断。没有预先约定质量阈值，也没有代表性评估；W9不是产品定稿。W8无clip折中只有本次数值证据，未列入四条RTL行。应继续多目标阈值、长/多样前缀、独立评估与官方框架对照，决定是否需要进一步逐通道/NUM硬件。

## RTL具体改动与工作原理

[block_w4_qnum_top](../project/rtl/block_connection_w4/block_w4_qnum_top.sv)沿已测F1024控制程序，新增编译期N_EPSILON与M_GATE_SHIFT/M_UP_SHIFT/M_DOWN_SHIFT四常量；N请求使用绑定epsilon，M最后READ以matrix选择shift。逆替换模块名、四参数与相应两表达式并去注释后，token序列与旧F1024相同。没有改叶宏、S/T布局、job/version协议或服务顺序；也没有通过TB force修改命令。

这表明叶M/N有源算术能力可承载两组有限命令常量，控制路径和数据格式必须一起绑定。当前是两次独立编译的静态profile验证，不是运行时装新程序，更不是M11/M12 ROM/线路永久绑定已经实现。旧F1024的weights_version只是参数身份，不能据此更换数值尺度。

S仍预约14912B、T2048B；完整1024 RMS、384组gate/up/G形成全部3072mid，再128组down/原残差，单M每组全K累加。每行36864次EXEC、589824权重拍、9MiB实参数、888076普通S请求/真实ACK、40448M命令、258N命令，T128字后真实RELEASE才DONE。新TB逐S写比较所有Norm/gate/up/mid/down/output，检查输入最后ACK、请求保持、输出背压、完整计数、heldDONE与abort+ready一次消费，并导出实际accepted流SHA。

RTL只运行baseline与cal-selected各一条cal_text_0_pos3、一条eval_text_0_pos3，共4完整行×7检查=28标记，不是28层模型。四条stream SHA：baseline两条49345f8375ff31be9efeba69a4a19251ae042656e261f6d67f994ed346f39ab1；selected两条9bc10d560783337d69ba3d18990a93b4f445585101cffc6259e72d314ff00148。

先行Python独立检查全部8个导出fixture：全18874368个F32→S8参数量化与两profile流重排SHA、gamma/input、全8192 N/24576 G/8192 E输出，以及192个不分块full-K M点积。G数学重建与原生表比对；M只采样，不据此宣称全部raw accumulator或完整饱和flag已独立证明。实际RTL则逐最终stage写值核对。独立FP32切口本身尚无官方框架对照。

## 证据、复现与未完成项

[数值原始回执](../work/Melodydt/151/qnum/evidence/runs/n01/results/numeric-run-receipt.json)、[RTL原始回执](../work/Melodydt/151/qnum/evidence/runs/q02/results/run-receipt.json)、[全部文本SHA](../work/Melodydt/151/qnum/evidence/evidence-manifest.json)、[绑定](../work/Melodydt/151/qnum/qnum-rtl-bindings.json)、[数值工具ABI](QWEN_NUMERIC_TOOL_ABI.md)。39份文本、两作业6+24份源输入（含重复项）、数值全部输出与四个actual stream在导出时重核。编译警告原样保留，不是lint clean；新故障矩阵、旧44RTL回归未重跑，控制模板资格不扩大成任意profile/故障通过。

q01只本地打包未提交、无job；11191a71推源后仅修合同两条辅助目录路径，实际RTL首次作业是q02/95248，无编造失败作业。完整Slurm/容器/命令见证据文件。

真实A同时形成[Sq2单S/T候选](QWEN3_SQ2_ATTENTION_PLAN.md)：S峰16384B、T4096B、原残差T spool/全context/逐KV头、Wo完整2048K；静态11个负例拒绝，尚无该A控制器/适配RTL。下一步是代表性质量门、框架对照/W8复核、实际A的Tspool与布局/参数/系数控制，再进入L5。原八模型×三target24GAP账本保留；外存存在并保留灵活性，真实MEM未接。

## 交付状态

复用Issue151/PR152和task/151-six-connection-study→task/143-seven-block-v2，Refs #151；待外部审查，未自合并/非done。登记PR5仍pending；config缺board.json/无Projects条目工具，状态unverified、同步pending、处理人待指定。个人进度/交接已更新；本地交流PDF单独交付，不上传Git。
