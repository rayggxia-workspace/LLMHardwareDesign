# Qwen / Llama：影响算子与Block边界的证据

记录日期：2026-10-22。首轮只做推理prefill/decode；训练是未来接口约束。未下载模型权重、数据或tokenizer，未执行训练，未修改项目仓库。

## 证据与版本

Qwen2.5、Qwen3和Qwen3.5均使用Qwen官方HF config，原字节、revision和SHA在model-config-index.json。Transformers实现固定到commit `17c6736cb2d3163be317550474b9d9c5081822ae`；Meta官方实现固定到 `0e0b8c519242d5833d8c11bffc1232b77ad7f301`。精确代码路径、Git blob和行号在source-index.json。config中的transformers_version是发布元数据，不是本轮执行环境。

一手入口：[Qwen2.5报告](https://arxiv.org/abs/2412.15115)、[Qwen3报告§2](https://arxiv.org/html/2505.09388v1#S2)、[Qwen3.5-0.8B官方卡片](https://huggingface.co/Qwen/Qwen3.5-0.8B)、[Qwen3.5-35B-A3B官方卡片](https://huggingface.co/Qwen/Qwen3.5-35B-A3B)、[Llama3作者论文](https://arxiv.org/html/2407.21783v3#S3.SS2)、[Gated DeltaNet作者论文](https://arxiv.org/abs/2412.06464)。

Meta HF config返回401，需要人工授权；没有借用token或绕过。Llama3.1参数改由[Meta官方sku_list.py](https://github.com/meta-llama/llama-models/blob/0e0b8c519242d5833d8c11bffc1232b77ad7f301/models/sku_list.py#L229)核验，运算由[官方model.py](https://github.com/meta-llama/llama-models/blob/0e0b8c519242d5833d8c11bffc1232b77ad7f301/models/llama3/model.py)核验。Llama4已有独立MoE系列，首轮“Llama”明确指3.1，不泛化成所有Llama均dense。

## 会改变边界的实际字段

|模型|D / F或Fe|Hq / Hkv / h|边界差异|
|---|---|---|---|
|Qwen2.5-7B|3584 / 18944|28 / 4 / 128|QKV bias，GQA 7:1，FFN非4D|
|Qwen3-0.6B|1024 / 3072|16 / 8 / 128|Q总宽2048≠D；head级QK RMSNorm，无QKV bias|
|Qwen3-8B|4096 / 12288|32 / 8 / 128|同D下FFN小于Llama3.1|
|Qwen3-30B-A3B|2048 / Fe768|32 / 4 / 128|128专家/top8，无shared expert；Q总宽4096|
|Llama3.1-8B|4096 / 14336|32 / 8 / 128|官方展开取整得到F14336，无QK norm|
|Qwen3.5-0.8B text|1024 / 3584|full:8 / 2 / 256|18线性+6full；GDN Hk=Hv16、dk=dv128、conv4|
|Qwen3.5-35B-A3B text|2048 / Fe512|full:16 / 2 / 256|30线性+10full；GDN Hk16/Hv32；256/top8另有门控shared expert512|

Qwen3的thinking/nonthinking“混合模式”不意味着混合注意力。Qwen3.5才是3层Gated DeltaNet加1层gated full attention。它的full q_proj还输出同宽sigmoid gate，即2Hq*h；不能只预留普通Q端口。已检查的GQA和GDN均不应标成MLA。Qwen3.5初轮只取text backbone，vision与MTP字段保留在原config，但不执行。

## 分块应如何解释

令M=BT，P为含当前token的上下文，h为head_dim。Q/K/V是[M,Hq*h]、[M,Hkv*h]、[M,Hkv*h]。原生KV cache元素数是2BPHkvh；GQA复用是查询头共享KV，不应把cache永久复制Hq份。prefill若把概念分数[B,Hq,T,P]导出跨Block，会付出随T*P增长的接口量；在线softmax则可保留tile和归一化统计。decode的T=1，主压力转为读取长KV前缀和追加少量新K/V。必须分别扫B/T/P。

候选一：Q/K projection的head级norm/RoPE作为邻接epilogue，减少重复导出；但要保留head宽、广播和位置数据接口。
候选二：将QK/在线softmax/AV与KV scratch紧耦合，按GQA head组计带宽与存储。
候选三：SwiGLU的gate/up均为[M,F]，在F方向tile内融合SiLU和点乘，再累加down。整个FFN一宏并非自动最好：还要计3DF权重、X广播、重读和D维partial sum。
候选四：复用专家FFN算子，单列top-k dispatch/scatter与shared分支。朴素实现每方向可能产生MkD元素，但广播与局部聚合可降低，不能称它是必然通信下界。容量要看每专家n_e、热点、队列与权重驻留。
候选五：GDN按value head保存矩阵状态，紧耦合更新与readout；沿dk切分会额外产生归约及delta广播。卷积历史和标量gate流水服务也需显式接口。

Qwen3.5的GDN逻辑是：先将S乘exp(g)，计算beta*(v-S^T*k)，外积更新S，再q^T*S读出。其状态元素数B*Hv*dk*dv，生产config/参考实现采用FP32；另有depthwise因果conv历史。prefill使用chunk算法，decode使用持久递推；两者不是两个独立无状态GEMM。全模型仍有full层增长KV，不能写成O(1)上下文内存。

容量例子（字段推算，非运行内存测量）：0.8B每线性层16*128*128个FP32状态=1MiB，18层18MiB；B1/P8192时，6个full层的BF16 KV合计96MiB，均未计其他激活/conv历史。

## 已实际执行的缩小正确性

tiny-benchmarks.json给出6组配置。通道维缩小32倍、深度缩小；保留原GQA head数、MoE128或256/top8、shared路径、GDN头比/conv4及最小3:1 quartet。使用合成随机权重，不是任何训练好的官方小模型。

correctness.py为可直接执行的原生NumPy程序，--config默认读取同目录tiny-benchmarks.json，--out指定结果路径，无D盘绝对路径依赖，也不使用动态exec。重跑命令为 `python -B correctness.py --config tiny-benchmarks.json --out correctness-native-results.json`。原correctness-recipe.json/correctness-results.json保留首轮来源；native-compatibility-check.json证明原生重跑的136例记录、每例输入SHA、shape、误差、配置SHA完全一致，只有计时和程序来源哈希字段按实际执行更新。

实测最大绝对误差3.9968e-15，全部通过：causal prefill对逐token native-KV decode；显式KV重复reference对分组在线softmax tile；整体SwiGLU对F-tile partial sum；MoE mask reference对dispatch/scatter（随机和集中热点）；GDN直接递推对独立仿射prefix，并核对末态；因果conv跨chunk历史交接。

这些是FP64数学子图与切边/状态交接正确性。attention输入视为位置变换后的Q/K，未验证完整RoPE变体；未执行完整LM logits、真实权重准确率、生产精度容差、软件吞吐或硅PPA。合成路由不证明训练后的expert负载分布。

## 首轮benchmark分层与训练约束

依次采用Llama3.1 dense GQA、Qwen2.5 biased GQA、Qwen3 QK-norm/扩展Q宽、Qwen3 routed MoE、Qwen3.5 dense hybrid，以Qwen3.5 shared-MoE hybrid作压力层。原尺寸config用于shape/容量trace，小维用于正确性；不要把两者合称全模型实测。图边至少记录shape、精度、方向、共享因子、每token/chunk产生率、突发、生命周期与跨token常驻。具体Block收益必须与本地SRAM、队列、端口和线长成本耦合。

训练仅作约束：Y=XW的dX=dYW^T、dW=X^TdY会改变转置和累加归属；norm/attention反向需要激活或重算；GDN不能只保留最终S供反向；MoE需要反向dispatch与归约。Llama3作者报告采用AdamW，两份FP32动量自身即8字节/参数；梯度、权重及可选master副本的精度另列。本轮未执行任何反向或优化器。
