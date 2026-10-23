# 给师兄Codex的一次批次请求 v2

2026-10-23，Issue47。供用户转交；未向他人或机器发送任务，未开始GPU/服务器运行。
覆盖先前“暂不新增模型”的最小请求，原因见[决策](../decisions/2026-10-23-causal-gqa-and-cpu-routing.md)。
用户随后只询问96核CPU可行性，当前没有把下列任务自动改派到超算。

以下可复制：

```text
请在本机为LLMHardwareDesign执行一次有界GPU批次并交接。
仓库https://github.com/rayggxia-workspace/LLMHardwareDesign。
先读取最新AGENTS、协作Skill、Issue32/PR36及其他成员进度，用本机操作者自己的GitHub身份。
已有合格数据直接复用，范围扩展另建关联Issue，不重复PR或接管他人任务。

主测：已有Qwen2.5代表、Qwen3.5-4B、google/gemma-3-4b-it。
有限扩展：google/gemma-3-12b-it、Qwen/Qwen3-4B、meta-llama/Llama-3.1-8B-Instruct、
deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B。
独立保留：microsoft/Phi-4-mini-instruct，现在可采集封存，划分冻结前不用保留组调参。
若已经调参则取消其独立保留身份。Qwen3-0.6B由另一电脑处理。

先核权限、显存/磁盘和后端兼容性，固定revision与协议，逐模型运行/释放显存并支持恢复。
Gemma/Llama缺访问权限时留阻塞、继续其他项，不借凭据或代同意许可。
不下载原版R1或其他超大权重，不启动其他机器，不恢复已取消的额外语言质量矩阵。

输入固定自然语言/数学/代码三类，校准与评价分离并保存token。
基础B1、prefill128/1024、decode32；主测再4096，更长优先复用现有结果。
扩展先短跑通、代表层采集和cached一致性，不做所有精度/长度笛卡尔积。
Gemma按实际配置W检查W-1/W/W+1的mask和KV淘汰；采local/global各一层。
Qwen3.5核连续、cached和chunk、保存跨窗状态，优先已有12-window，不能每窗清零冒充连续。

全图记录算子/shape/布局/dtype/状态/依赖；数值只采首中末代表层及校准组选定的异常层。
保存投影输入/必要权重切片/bias位置/输出；一个完整GQA共享组的Q/K/V/mask/位置/输出；
norm/RoPE/激活/门控必要边界；KV布局、有效长度和scale；Qwen3.5状态更新输入、初态和末态。
保留完整归约维度和头共享关系，避免保存全层完整S×S注意力矩阵。
观察者尽量不改变语义，说明插桩和影响。GPU性能运行不进行张量转存。

高精度优先BF16/FP16并验证数值，必要FP32明确记录。
Gemma12B和Llama8B可4bit权重加载，但记录格式/group/scale/zero point/计算dtype/后端；
没有原高精度对照时标明，仅代表该加载条件，不将反量化4bit称原始FP16参考。
主硬件候选仍W8A8/INT32，KV、递推状态、非线性及scale各自定格式。
区分浮点参考、假量化、整数参考、真实整数内核；列出浮点回退。
切片验证溢出、舍入/饱和、重定标和误差；转换/宽乘/除法缺硬件证据就待验证。

记录算术/真实shape、INT32部分和、状态/metadata、复用与同步依赖，供Block划分比较。
GPU时间与显存只是当前后端观测，不证明目标Block周期/PPA；不统一把FP32流量除四。
R1-Distill为dense蒸馏，不代表MLA/MoE；原版仅做配置/算子需求分析及明确合成的缩小参考，
不得声称跑通原版R1，也不下载其完整权重。

每项最终标复用/已执行/失败/阻塞/条件跳过并附证据。
保存commit、命令、版本、revision、输入/配置、位置/大小/SHA-256；统一索引、格式和校验工具。
大文件用已授权共享存储，仓库留小样本和索引，不提交权重/密钥。
OOM先减少观察者/捕获量，仍失败则记录并继续；CPU offload和纯GPU性能分列。
一项失败不阻塞其他独立项，数值失败合同停止性能收益比较，不无限扫参数找有利结果。
更新本人进度、Issue/PR、交接，不自行合并或done，不把本地完成写成远端完成。
最终说明覆盖哪些划分决策、缺口、成果SHA和另一电脑恢复第一步。
用户通知另一电脑后，它再读取最新成果并整合。
```
