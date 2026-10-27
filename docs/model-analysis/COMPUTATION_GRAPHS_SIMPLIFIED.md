# 八模型精简字符算子计算图

整理日期：2026-10-26。覆盖八个模型、十种 decoder 层类型。

本文用于阅读算子依赖、比较模型差异与讨论候选 Block 边界。所有图均以算子和张量为主体；重复的 RMSNorm、RoPE、SiLU 等小子图适度折叠，其展开定义见文末。这里的折叠方式不代表已经确定物理 Block。

配套材料：[交互图册](./graphs/operator-graphs.html) · [完整实验说明](./COMPUTATION_GRAPHS_FULL.md) · [实际导出与验证索引](./graphs/results/render01/manifest.json)。

## 1. 阅读口径

- 主图表示一个完整 decoder 层，从隐藏状态 `X` 到输出 `O`，包含层内残差。
- `Wq` 等表示权重，权重及标量常量直接写在算子参数中，不再单画常量节点。图中 `MatMul(W)` 表示右乘适当布局的权重；实际 ONNX 可能用转置权重或 Gemm 表示。
- `B` 为 batch，`S` 为当前序列长度，`T` 为可访问的历史加当前长度，`H` 为隐藏维度，`I` 为 FFN 中间维度，`D` 为每个注意力头的维度。
- `Reshape`、`Transpose`、重要的 `Slice`、GQA 的头扩展、门控和残差均保留；省略用于构造 shape 参数的辅助节点与 eval 时无效的 dropout。
- 图中的 `RMS`、`RMS0`、`RoPE`、`L2Norm`、`SiLU`、`GELU_tanh`、`Softmax` 均有展开定义。`RMS0` 使用 `gamma = 1 + weight`，普通 `RMS` 使用 `gamma = weight`。
- 同名中间张量表示同一个来源，可以有多条消费边。`Add(A,B)`、`MatMul(A,B)` 明确列出两路输入，避免只凭线条猜测依赖。
- 各图以语义 prefill 为主；decode 的缓存接入在第 10 节说明。实际 ONNX 验证为 B=1、S=2、FP32、eager、use_cache=False。
- Llama 使用报告记录的配置重建和固定种子随机参数；其余模型的指定层加载真实检查点参数。Qwen3.5 递推核与 Granite 专家分派的导出适配见对应章节。
- 文本图经过语义归一与人工核对，不是从 onnxsim 逐字打印出来的可执行 IR，也没有对文本图本身进行数值执行验证。

### 1.1 为什么三种图看起来不一样

| 图 | 画了什么 | 适合做什么 |
|---|---|---|
| 手工语义图 | 运算关系、主要布局变换、状态与残差 | 理解模型、讨论候选边界 |
| 原始 ONNX | 导出产生的所有算子，包括常量与形状计算 | 审计导出与实现细节 |
| onnxsim 图 | 常量、形状计算折叠及局部融合后的算子 | 阅读实际实现、统计算子 |
| 本文字符图 | 对语义图与实际 ONNX 核对后，按统一规则精简 | 在终端、Markdown、讨论文档中对照 |

例如本次 Qwen3 原始 ONNX 有 253 个节点，其中 Constant 91 个、Unsqueeze 53 个；简化后共 80 个节点，其中 Constant 4 个、Unsqueeze 4 个。两者 MatMul 都是 9 个。因此，图上节点大幅减少不等于矩阵乘计算量同比减少。

### 1.2 模型配置与层类型

| 模型 | 层数 | H | FFN I | Q/KV 头 | D | 本文层类型 |
|---|---:|---:|---:|---:|---:|---|
| Qwen2.5-3B | 36 | 2048 | 11008 | 16/2 | 128 | 全局注意力 |
| Qwen3-0.6B | 28 | 1024 | 3072 | 16/8 | 128 | 全局注意力，Q/K norm |
| Llama-3.2-1B | 16 | 2048 | 8192 | 32/8 | 64 | 全局注意力 |
| Gemma-3-4B | 34 | 2560 | 10240 | 8/4 | 256 | 局部、全局两种 |
| Phi-4-mini | 32 | 3072 | 8192 | 24/8 | 128 | 融合投影、部分 RoPE |
| Qwen3.5-4B | 32 | 2560 | 9216 | 16/4（全局层） | 256（全局层） | 全局注意力、GDN 递推两种 |
| Granite-3.3B | 32 | 1536 | 每专家 512 | 24/8 | 64 | GQA + 40 专家 top8 MoE |
| Falcon-H1-3B | 32 | 2560 | 6144 | 10/2（注意力分支） | 128（注意力分支） | 注意力与 SSM 并行 |

Qwen3 与 Falcon 的 `Q头数 × D` 不等于 H；不能直接用 `H / Q头数` 代替配置中的 D。

## 2. Qwen2.5-3B

特点：Q/K/V 投影有偏置；Q/K 不做头内归一化；普通 RMS + SwiGLU。K/V 从 2 个头扩展到 16 个查询头。

```text
X [B,S,2048]
 |
 RMS -> N
        |
        +-> MatMul(Wq) -> Add(bq) -> Reshape -> Transpose -> RoPE -> Q
        |
        +-> MatMul(Wk) -> Add(bk) -> Reshape -> Transpose -> RoPE -> K
        |
        +-> MatMul(Wv) -> Add(bv) -> Reshape -> Transpose --------> V

K -> Unsqueeze -> Expand(head x8) -> Reshape -> K_rep -> Transpose(last2) -> Kt
V -> Unsqueeze -> Expand(head x8) -> Reshape -> V_rep

Q, Kt -> MatMul -> Mul(1/sqrt(128)) -> Add(mask) -> Softmax -> P
P, V_rep -> MatMul -> Transpose -> Reshape[B,S,2048] -> MatMul(Wo) -> A

X, A -> Add -> Y
               |
               RMS -> F
                      |
                      +-> MatMul(Wgate) -> G -----------+
                      |                   |            |
                      |                   +-> Sigmoid -+-> Mul -> SG
                      |                                            |
                      +-> MatMul(Wup) -> U ------------------------> Mul
                                                                     |
                                                                MatMul(Wdown)
                                                                     |
                                                                     Z
Y, Z -> Add -> O [B,S,2048]
```

上图 `Mul(G, Sigmoid(G))` 就是 SiLU。实际 onnxsim 将三个带偏置的 Q/K/V 线性投影表示为 Gemm；这里保留 MatMul + Add，方便看清偏置。

## 3. Qwen3-0.6B

特点：Q/K 增加头内普通 RMS；Q/K/V 投影无偏置；16 个查询头、8 个 KV 头、D=128。Q 投影宽度为 2048，虽然 H 只有 1024。

```text
X [B,S,1024]
 |
 RMS -> N
        |
        +-> MatMul(Wq) -> Reshape -> RMS(head,D=128) -> Transpose -> RoPE -> Q
        |
        +-> MatMul(Wk) -> Reshape -> RMS(head,D=128) -> Transpose -> RoPE -> K
        |
        +-> MatMul(Wv) -> Reshape --------------------> Transpose --------> V

K -> Unsqueeze -> Expand(head x2) -> Reshape -> K_rep -> Transpose(last2) -> Kt
V -> Unsqueeze -> Expand(head x2) -> Reshape -> V_rep

Q, Kt -> MatMul -> Mul(1/sqrt(128)) -> Add(mask) -> Softmax -> P
P, V_rep -> MatMul -> Transpose -> Reshape[B,S,2048] -> MatMul(Wo) -> A

X, A -> Add -> Y
               |
               RMS -> F
                      |
                      +-> MatMul(Wgate) -> SiLU --+
                      |                          |
                      +-> MatMul(Wup) ----------> Mul -> MatMul(Wdown) -> Z

Y, Z -> Add -> O [B,S,1024]
```

SiLU 在图中折叠一次，具体仍是 `G -> Sigmoid(G)`，然后 `Mul(G,Sigmoid(G))`。与 Qwen2.5 对比时，重点是新增的 Q/K norm、取消 QKV 偏置与投影宽度差异。

## 4. Llama-3.2-1B

特点：Q/K/V 无偏置，无 Q/K 头内 RMS；普通 RMS + SwiGLU；K/V 头扩展倍数为 4。Llama3 的位置频率规则影响层外 cos/sin 生成，不能从层内 RoPE 乘加拓扑单独看出来。

```text
X [B,S,2048]
 |
 RMS -> N
        |
        +-> MatMul(Wq) -> Reshape -> Transpose -> RoPE -> Q
        |
        +-> MatMul(Wk) -> Reshape -> Transpose -> RoPE -> K
        |
        +-> MatMul(Wv) -> Reshape -> Transpose --------> V

K -> Unsqueeze -> Expand(head x4) -> Reshape -> K_rep -> Transpose(last2) -> Kt
V -> Unsqueeze -> Expand(head x4) -> Reshape -> V_rep

Q, Kt -> MatMul -> Mul(1/sqrt(64)) -> Add(mask) -> Softmax -> P
P, V_rep -> MatMul -> Transpose -> Reshape[B,S,2048] -> MatMul(Wo) -> A

X, A -> Add -> Y
               |
               RMS -> F
                      |
                      +-> MatMul(Wgate) -> SiLU --+
                      |                          |
                      +-> MatMul(Wup) ----------> Mul -> MatMul(Wdown) -> Z

Y, Z -> Add -> O [B,S,2048]
```

证据边界：本轮没有原始检查点，导出与数值验证采用配置重建和随机参数，只验证该配置下的层计算与导出流程。

## 5. Gemma-3-4B

两种层均有 Q/K 头内 RMS0、注意力后 RMS0、FFN 后 RMS0，FFN 门激活为 GELU_tanh。每层共六组归一化：输入、Q、K、注意力后、FFN前、FFN后。

### 5.1 局部注意力层

```text
X [B,S,2560]
 |
 RMS0 -> N
         |
         +-> MatMul(Wq) -> Reshape -> Transpose -> RMS0(head) -> RoPE(local) -> Q
         |
         +-> MatMul(Wk) -> Reshape -> Transpose -> RMS0(head) -> RoPE(local) -> K
         |
         +-> MatMul(Wv) -> Reshape -> Transpose ---------------------------> V

K -> Unsqueeze -> Expand(head x2) -> Reshape -> K_rep -> Transpose(last2) -> Kt
V -> Unsqueeze -> Expand(head x2) -> Reshape -> V_rep

Q, Kt -> MatMul -> Mul(1/sqrt(256)) -> Add(causal + local_mask_1024) -> Softmax -> P
P, V_rep -> MatMul -> Transpose -> Reshape[B,S,2048] -> MatMul(Wo) -> A
                                                                              |
                                                                            RMS0
                                                                              |
                                                                             A_n
X, A_n -> Add -> Y
                 |
                 RMS0 -> F
                          |
                          +-> MatMul(Wgate) -> GELU_tanh --+
                          |                               |
                          +-> MatMul(Wup) ----------------> Mul -> MatMul(Wdown)
                                                                         |
                                                                       RMS0
                                                                         |
                                                                         Z
Y, Z -> Add -> O [B,S,2560]
```

局部层窗口为 1024；局部 RoPE 的 theta 为 10000。图中 mask 表示实际可访问位置约束。具体实现可以通过掩码、缓存裁剪或专用局部注意力内核执行；本图不把某一种缓存物理组织方式当成模型强制要求。

### 5.2 全局注意力层

```text
X [B,S,2560]
 |
 RMS0 -> N
         |
         +-> MatMul(Wq) -> Reshape -> Transpose -> RMS0(head) -> RoPE(global) -> Q
         |
         +-> MatMul(Wk) -> Reshape -> Transpose -> RMS0(head) -> RoPE(global) -> K
         |
         +-> MatMul(Wv) -> Reshape -> Transpose ----------------------------> V

K -> Unsqueeze -> Expand(head x2) -> Reshape -> K_rep -> Transpose(last2) -> Kt
V -> Unsqueeze -> Expand(head x2) -> Reshape -> V_rep

Q, Kt -> MatMul -> Mul(1/sqrt(256)) -> Add(causal_mask) -> Softmax -> P
P, V_rep -> MatMul -> Transpose -> Reshape[B,S,2048] -> MatMul(Wo) -> RMS0 -> A_n

X, A_n -> Add -> Y
                 |
                 RMS0 -> F
                          |
                          +-> MatMul(Wgate) -> GELU_tanh --+
                          |                               |
                          +-> MatMul(Wup) ----------------> Mul -> MatMul(Wdown)
                                                                         |
                                                                       RMS0
                                                                         |
                                                                         Z
Y, Z -> Add -> O [B,S,2560]
```

全局 RoPE 配置 theta=1000000、linear factor=8。本次实际导出用外部 cos/sin 且 S=2，两种层均简化为 110 个节点；这个结果没有检验真实长序列下局部与全局的存储/带宽差异。

## 6. Phi-4-mini

特点：QKV 使用一次融合投影，然后 Slice 成三路；FFN gate/up 也融合投影。无 Q/K 头内 norm。每头 D=128，其中 96 个通道参与 RoPE，32 个通道直接保留。

```text
X [B,S,3072]
 |
 RMS -> N -> MatMul(Wqkv) -> QKV [B,S,5120]
                              |
             +----------------+----------------+
             |                |                |
         Slice(Q)         Slice(K)         Slice(V)
             |                |                |
          Reshape          Reshape          Reshape
             |                |                |
         Transpose        Transpose        Transpose
             |                |                |
      PartialRoPE(96/128) PartialRoPE(96/128)    |
             |                |                |
             Q                K                V

K -> Unsqueeze -> Expand(head x3) -> Reshape -> K_rep -> Transpose(last2) -> Kt
V -> Unsqueeze -> Expand(head x3) -> Reshape -> V_rep

Q, Kt -> MatMul -> Mul(1/sqrt(128)) -> Add(mask) -> Softmax -> P
P, V_rep -> MatMul -> Transpose -> Reshape[B,S,3072] -> MatMul(Wo) -> A

X, A -> Add -> Y
               |
               RMS -> F -> MatMul(Wgate_up) -> GU [B,S,16384]
                                              |
                            +-----------------+-----------------+
                            |                                   |
                        Slice(gate)                         Slice(up)
                            |                                   |
                           SiLU ------------------------------> Mul
                                                                 |
                                                            MatMul(Wdown)
                                                                 |
                                                                 Z
Y, Z -> Add -> O [B,S,3072]
```

LongRoPE 的频率选择位于 cos/sin 生成中；本文没有把它展开成额外的层内乘法分支。融合投影不是把三路结果相加，而是一次产生拼接张量后拆分。

## 7. Qwen3.5-4B

32 层中，每四层为三层 GDN 递推加一层全局注意力。层输入 norm 与 FFN 前 norm 使用 RMS0。

### 7.1 全局注意力层

特点：Q 投影同时产生 Q 与输出门，两者按每个头拆分；Q/K 有头内 RMS0；每头只旋转 64/256 通道；PV 后的门激活为 Sigmoid。

```text
X [B,S,2560]
 |
 RMS0 -> N
         |
         +-> MatMul(Wq_gate) -> Reshape[B,S,16,512] -> Split(last axis)
         |                                                |
         |                         +----------------------+-----------------+
         |                         |                                        |
         |                   Q_raw [..,256]                           Gate [..,256]
         |                         |                                        |
         |                     RMS0(head)                                Reshape
         |                         |                                        |
         |                     Transpose                                 Sigmoid
         |                         |                                        |
         |                PartialRoPE(64/256)                                G
         |                         |
         |                         Q
         |
         +-> MatMul(Wk) -> Reshape -> RMS0(head) -> Transpose -> PartialRoPE(64/256) -> K
         |
         +-> MatMul(Wv) -> Reshape --------------> Transpose --------------------> V

K -> Unsqueeze -> Expand(head x4) -> Reshape -> K_rep -> Transpose(last2) -> Kt
V -> Unsqueeze -> Expand(head x4) -> Reshape -> V_rep

Q, Kt -> MatMul -> Mul(1/sqrt(256)) -> Add(mask) -> Softmax -> P
P, V_rep -> MatMul -> Transpose -> Reshape[B,S,4096] -> C
C, G -> Mul -> MatMul(Wo) -> A

X, A -> Add -> Y
               |
               RMS0 -> F
                       |
                       +-> MatMul(Wgate) -> SiLU --+
                       |                          |
                       +-> MatMul(Wup) ----------> Mul -> MatMul(Wdown) -> Z

Y, Z -> Add -> O [B,S,2560]
```

Gate 在 softmax/PV 之后乘到上下文上，不是 QK 打分前的门。这里的 Gate 使用 Sigmoid，与 FFN 中的 SiLU 不同。

### 7.2 GDN 线性递推层：投影、卷积和门

配置：16 个 key 头、32 个 value 头，key/value 每头均为 128；卷积核宽度为 4。线性层没有 QK softmax 注意力和 RoPE。

```text
X [B,S,2560]
 |
 RMS0 -> N
         |
         +-> MatMul(Wqkv) -> Transpose -> CausalDepthwiseConv1D(k=4) -> SiLU
         |                                                               |
         |                                                           Transpose
         |                                                               |
         |                                                             Split
         |                                                               |
         |                         +-------------------------------------+--------------+
         |                         |                                     |              |
         |                      Q_raw                                 K_raw          V_raw
         |                         |                                     |
         |                    Reshape+L2Norm                        Reshape+L2Norm    Reshape
         |                         |                                     |
         |                  RepeatHeads(16->32)                  RepeatHeads(16->32)   V
         |                         |                                     |
         |                   Mul(1/sqrt(128))                             K
         |                         |
         |                         Q
         |
         +-> MatMul(Wz) -> Reshape ----------------------------------------------> Z_gate
         |
         +-> MatMul(Wb) -> Sigmoid ----------------------------------------------> beta
         |
         +-> MatMul(Wa) -> Add(dt_bias) -> Softplus -> dt

A_log -> Exp -> Neg -> A
A, dt -> Mul -> g -> Exp -> decay

Q, K, V, beta, decay, S_prev -> [逐token算子子图，见下] -> R, S_new

R -> RMS(per value head, gamma=weight) -> R_n
Z_gate -> SiLU -> G
R_n, G -> Mul -> Reshape[B,S,4096] -> MatMul(Wout) -> A_out

X, A_out -> Add -> Y
                   |
                   RMS0 -> F
                           |
                           +-> MatMul(Wgate) -> SiLU --+
                           |                          |
                           +-> MatMul(Wup) ----------> Mul -> MatMul(Wdown) -> Z_out

Y, Z_out -> Add -> O [B,S,2560]
```

`RepeatHeads` 表示沿头轴重复，每个 key 头对应两个 value 头；实际 ONNX 可用 Tile/Reshape 等实现。`RMS` 必须先于输出门乘，与 Falcon 的门乘顺序相反。

### 7.3 GDN 每个 token 的状态更新：展开到算子

`S_prev` / `S_new` 的形状为 `[B,32,128_key,128_value]`。

```text
S_prev, decay_t -> Mul -> S_decay

K_t -> Unsqueeze(value axis) -> K_col
S_decay, K_col -> Mul -> ReduceSum(key axis) -> V_pred

V_t, V_pred -> Sub -> Error
Error, beta_t -> Mul -> Delta

Delta -> Unsqueeze(key axis) -> Delta_row
K_col, Delta_row -> Mul -> Update                  # key x value outer product
S_decay, Update -> Add -> S_new

Q_t -> Unsqueeze(value axis) -> Q_col
S_new, Q_col -> Mul -> ReduceSum(key axis) -> R_t

S_new ------------------------------------------------> StateWrite
R_0, R_1, ... -> Stack(time axis) --------------------> R
```

无历史的 prefill 从全零状态开始，依次处理 token；decode 从历史状态开始处理当前 token。官方分块 prefill 使用另一套分块算法。本轮原生分块导出遇到不支持的 `linalg_solve_triangular`，成功 ONNX 仅将核替换为官方逐 token 递推实现；其输出仍与原生分块前向核对。

## 8. Granite-3.3B MoE

特点：注意力使用 GQA；FFN 替换为 40 个专家中动态 top8。每个专家 I=512，不能把 512 当作全部专家总宽度。两处残差分支均有 0.22 缩放。

### 8.1 注意力与残差

```text
X [B,S,1536]
 |
 RMS -> N
        |
        +-> MatMul(Wq) -> Reshape -> Transpose -> RoPE -> Q
        |
        +-> MatMul(Wk) -> Reshape -> Transpose -> RoPE -> K
        |
        +-> MatMul(Wv) -> Reshape -> Transpose --------> V

K -> Unsqueeze -> Expand(head x3) -> Reshape -> K_rep -> Transpose(last2) -> Kt
V -> Unsqueeze -> Expand(head x3) -> Reshape -> V_rep

Q, Kt -> MatMul -> Mul(attention_multiplier=0.015625) -> Add(mask) -> Softmax -> P
P, V_rep -> MatMul -> Transpose -> Reshape[B,S,1536] -> MatMul(Wo) -> Mul(0.22) -> A

X, A -> Add -> Y
               |
               RMS -> F -> Reshape[B*S,1536] -> Tokens
```

注意：这里注意力打分缩放来自配置 `attention_multiplier`，不能替换为默认 `1/sqrt(64)`。

### 8.2 动态 top8 专家：与本轮导出对应的精简图

```text
Tokens -> MatMul(Wrouter) -> Logits [B*S,40]
                                  |
                                TopK(k=8)
                                  |
                  +---------------+----------------+
                  |                                |
                IDs                           SelectedLogits
                  |                                |
                  |                             Softmax -> RoutingWeights
                  |
                  +-> Gather(ExpertGateUpWeights) -> W_gu_selected
                  |
                  +-> Gather(ExpertDownWeights) ----> W_down_selected

Tokens -> Unsqueeze(assignment axis) -> Tokens8
Tokens8, W_gu_selected -> BatchedMatMul -> GU [B*S,8,1024]
                                          |
                            +-------------+-------------+
                            |                           |
                         Slice(gate)                 Slice(up)
                            |                           |
                           SiLU ----------------------> Mul -> Mid [B*S,8,512]

Mid, W_down_selected -> BatchedMatMul -> ExpertReturns [B*S,8,1536]
ExpertReturns, RoutingWeights -> Mul -> ReduceSum(top8 axis) -> M
M -> Reshape[B,S,1536] -> Mul(0.22) -> Z

Y, Z -> Add -> O [B,S,1536]
```

原生专家实现按专家聚集 token，再将输出累加回 token。另一种等价的字符表达是：

```text
TopK IDs -> Group/Argsort -> Gather(token rows)
                         -> expert MatMul / SiLU / Mul / MatMul
                         -> Mul(routing weight) -> ScatterAdd(token rows)
```

本轮为了避免导出时把 Python 分支与所选专家固定下来，采用前一张动态 Gather + 批量 MatMul 图。TopK IDs 保持为运行时张量。两种分派方式的权重访问、临时存储和通信组织可以不同，不能只按数学等价就假设硬件成本相同。

## 9. Falcon-H1-3B

特点：从同一个归一化输入并行产生注意力与 SSM 输出，先合并两条分支，再加输入残差，随后执行 FFN。各分支包含 MuP 缩放；SSM 是先门乘、后共享通道归一化。

### 9.1 层内连接与 FFN

```text
X [B,S,2560]
 |
 RMS -> N
        |
        +-> Mul(attn_in=1.0) -> [9.2 注意力算子子图] -> Mul(attn_out=0.15) -> A
        |
        +--------------------> [9.3 SSM算子子图] ----> Mul(ssm_out=0.088388...) -> M

A, M -> Add -> Mixed
X, Mixed -> Add -> Y
                   |
                   RMS -> F
                          |
                          +-> MatMul(Wgate) -> Mul(0.353553...) -> SiLU --+
                          |                                             |
                          +-> MatMul(Wup) -----------------------------> Mul
                                                                         |
                                                                    MatMul(Wdown)
                                                                         |
                                                                    Mul(0.078125)
                                                                         |
                                                                         Z
Y, Z -> Add -> O [B,S,2560]
```

9.2 和 9.3 是紧接着展开的算子子图，不表示物理 Block。

### 9.2 注意力分支

```text
N_a [B,S,2560]
 |
 +-> MatMul(Wq) -> Reshape -> Transpose ---------------------------------> RoPE -> Q
 |
 +-> MatMul(Wk) -> Reshape -> Transpose -> Mul(key_multiplier=0.044194...) -> RoPE -> K
 |
 +-> MatMul(Wv) -> Reshape -> Transpose ------------------------------------------> V

K -> Unsqueeze -> Expand(head x5) -> Reshape -> K_rep -> Transpose(last2) -> Kt
V -> Unsqueeze -> Expand(head x5) -> Reshape -> V_rep

Q, Kt -> MatMul -> Mul(1/sqrt(128)) -> Add(mask) -> Softmax -> P
P, V_rep -> MatMul -> Transpose -> Reshape[B,S,1280] -> MatMul(Wo) -> AttentionOut
```

本次实际导出使用完整 128 通道 RoPE。K 投影后的额外 key_multiplier 与 QK 打分后的 scale 是两处独立的乘法。

### 9.3 SSM 分支：投影、卷积、时间步与读出

```text
N [B,S,2560]
 |
 Mul(ssm_in=0.5)
 |
 MatMul(Win)
 |
 Mul(per-channel MuP vector)
 |
 Split -----------------------------------------------------+
   |                         |                              |
 Z_gate [..,4096]          XBC [..,4608]                  dt_raw [..,32]
   |                         |                              |
  SiLU                    Transpose                      Add(dt_bias)
   |                         |                              |
   G                CausalDepthwiseConv1D(k=4,bias=True)   Softplus
                             |                              |
                            SiLU                        Clip(dt_limits)
                             |                              |
                          Transpose                         dt
                             |
                           Split
                             |
                    +--------+--------+
                    |        |        |
                X_ssm     B_coef   C_coef
                    |        |        |
                    |     Broadcast from 1 group to 32 heads
                    |        |        |
                    +--------+--------+----> [9.4 单token状态算子子图] -> R

A_log -> Exp -> Neg -> A_rate
A_rate, dt ------------------------------------------------------> 9.4
D, X_ssm --------------------------------------------------------> 9.4

R, G -> Mul -> Reshape[B,S,4096] -> RMS(across 4096 channels)
                                         |
                                    MatMul(Wout)
                                         |
                                       SSMOut
```

每头 x 宽度 128，状态维度 256，共 32 个 SSM 头。输出门乘之后，才跨 4096 个通道归一化；不能改画成“先 norm 再门乘”，也不能改成每头各做 128 维 norm。

MuP 向量按 z、x、B、C、dt 五段设置不同缩放，来源为本次配置的 `ssm_multipliers`，顺序为 `[0.353553..., 0.25, 0.176776..., 0.5, 0.353553...]`。

### 9.4 SSM 每个 token 的状态更新

`S_prev` / `S_new` 的形状为 `[B,32,128_channel,256_state]`。

```text
dt_t, A_rate -> Mul -> Exp -> Decay
S_prev, Decay -> Mul -> S_decay

dt_t, B_t -> Mul -> dB
dB -> Unsqueeze(channel axis) -> dB_row
X_t -> Unsqueeze(state axis) -> X_col
dB_row, X_col -> Mul -> Injection                 # channel x state outer product

S_decay, Injection -> Add -> S_new

C_t -> Unsqueeze(channel axis) -> C_row
S_new, C_row -> Mul -> ReduceSum(state axis) -> Readout
X_t, D -> Mul -> Skip
Readout, Skip -> Add -> R_t

S_new ---------------------------------------------> StateWrite
R_0, R_1, ... -> Stack(time axis) -----------------> R
```

这张图表达递推语义。实际原生 prefill 使用分块扫描，ONNX 中还出现 Pad、CumSum、Where、Einsum 等算子。本轮 Falcon 原始导出为 998 个节点，onnxsim 后为 173 个；不能将此字符图当作分块扫描实现的逐节点转录。

## 10. Decode 时如何接入历史状态

本节描述语义上的状态依赖。本轮没有导出带历史状态的 decode ONNX，也没有验证非零历史状态。

### 10.1 各注意力层的 KV 缓存

当前 K 已完成 RoPE；V 直接来自投影与布局变换。GQA 共享头的扩展位于缓存读出之后，避免在语义图上强制缓存重复的 K/V。

```text
Past_K, K_current -> Concat(sequence axis) -> K_all -> StateWrite(new K cache)
Past_V, V_current -> Concat(sequence axis) -> V_all -> StateWrite(new V cache)

K_all -> [可访问位置选择] -> Unsqueeze/Expand/Reshape -> Transpose -> Kt
V_all -> [可访问位置选择] -> Unsqueeze/Expand/Reshape ------------> V_rep

Q_current, Kt -> MatMul -> Mul(scale) -> Add(mask) -> Softmax -> P
P, V_rep -> MatMul -> ... -> current hidden output
```

全局层访问历史前缀；Gemma 局部层只允许窗口内位置。是否真的移动/裁剪缓存张量，取决于 cache 实现，不能由抽象窗口直接推断。

### 10.2 Qwen3.5 GDN / Falcon SSM 的卷积历史

```text
ConvHistory, CurrentProjectedInput -> Concat(time axis) -> Combined
                                                          |
                             +----------------------------+-----------------+
                             |                                              |
                      DepthwiseConv1D                             Slice(last cache width)
                             |                                              |
                    Slice(current outputs)                         StateWrite(new history)
                             |
                            SiLU
                             |
                       subsequent split
```

history 更新必须取“旧历史 + 当前输入”的尾部；只切当前 token 无法保留完整卷积历史。实际缓存保存 kernel 宽度还是最少的 kernel-1 历史，按具体 cache 接口确认。

### 10.3 递推状态

```text
StateRead(S_prev) -> 本文对应的单token更新子图 -> S_new -> StateWrite
                                             |
                                       current readout
```

GDN 与 SSM 的状态更新式不同，不应仅因两者都有 StateRead/StateWrite 就当成同一个算子核。Falcon 同一层同时涉及注意力 KV、卷积历史与 SSM 状态。

## 11. 折叠算子的展开定义

本节给出精简图的“展开开关”。讨论数值功能时可以折叠，讨论归约资源、特殊函数单元与跨边界张量时应展开。

### 11.1 普通 RMS 与 RMS0

```text
X -> Pow(2) -> ReduceMean(last axis) -> Add(eps) -> Rsqrt -> Inv
X, Inv -> Mul -> X_normalized

RMS :  X_normalized, weight          -> Mul -> Y
RMS0:  weight -> Add(1) -> gamma
       X_normalized, gamma          -> Mul -> Y
```

ONNX 常将 `Rsqrt(A)` 表示为 `Sqrt(A) -> Div(1, sqrt)`。若使用混合精度，还需要保留实际实现中的类型转换。本轮 FP32 字符图省略这些 Cast。

### 11.2 L2Norm

```text
X -> Mul(X,X) -> ReduceSum(last axis) -> Add(eps) -> Rsqrt -> Inv
X, Inv -> Mul -> Y
```

它使用 ReduceSum，无可学习 gamma；不能直接替换成带 gamma 的 RMSNorm。

### 11.3 RoPE 与部分 RoPE

```text
X -> Slice(first half) -> X1 -----------------------+
X -> Slice(second half) -> X2 -> Neg -> NegX2       |
                                          |        |
                                          +-> Concat(NegX2,X1) -> Rotated

X, cos -> Mul -> C
Rotated, sin -> Mul -> S
C, S -> Add -> RotatedOutput
```

部分 RoPE：

```text
X -> Slice(rotary channels) -> RoPE ------------+
X -> Slice(passthrough channels) ---------------+-> Concat -> Y
```

cos/sin 的频率生成、位置索引，以及多模态位置编码的上游处理不在本文层图中。具有同样 RoPE 层内算子，不代表上游位置编码规则相同。

### 11.4 SiLU

```text
X ----------------+
|                 |
+-> Sigmoid ------+-> Mul -> Y
```

若需要继续下降到特殊函数能力，数学上 `Sigmoid(x)=1/(1+exp(-x))`，可进一步表示为 Neg、Exp、Add、Reciprocal。但实际近似、多项式或查表实现需要另行选择。

### 11.5 GELU_tanh

```text
X -> Pow(3) -> Mul(0.044715) -> C
X, C -> Add -> Mul(sqrt(2/pi)) -> Tanh -> Add(1) -> T
X -> Mul(0.5) -> HalfX
HalfX, T -> Mul -> Y
```

Gemma 门分支使用这个版本。Tanh 也可以进一步降低到特殊函数实现，但本轮没有选定其硬件近似方案。

### 11.6 Softmax

沿 key 轴（注意力）或 top-k 轴（MoE 门权重）执行：

```text
X -> ReduceMax(axis) -> Max
X, Max -> Sub -> Exp -> E
E -> ReduceSum(axis) -> Denominator
E, Denominator -> Div -> Y
```

ReduceMax/Sub 是常见的数值稳定处理。此处为数学展开，不表示实际注意力一定先物化完整分数矩阵或完整 softmax 张量。

### 11.7 因果深度卷积

```text
ProjectedSequence -> Transpose(channel first) -> causal left Pad
                                                    |
                                             Conv1D(groups=channels)
                                                    |
                                           Slice(valid positions)
                                                    |
                                                   SiLU
                                                    |
                                        Transpose(sequence first)
```

实现可用 Conv 的 padding 属性加输出裁剪，或显式 padding、缓存更新加无 padding 卷积。核宽度为 4 不等于必须单独部署四个卷积 Block。

## 12. 将代表层放回模型层序列

以下是层类型序列索引，层内算子仍以各章节为准。此处不是整个网络端到端 ONNX 图。

```text
Qwen2.5 : 36 x 第2节层
Qwen3   : 28 x 第3节层
Llama3.2: 16 x 第4节层
Phi4mini: 32 x 第6节层
Granite : 32 x 第8节层
FalconH1: 32 x 第9节混合层（每层内部两分支并行）

Gemma3（0-based layer index）:
  global layers = 5, 11, 17, 23, 29
  remaining 29 layers = local
  total = 34

Qwen3.5:
  [GDN, GDN, GDN, GlobalAttention] x 8
  total = 32
```

词嵌入、位置与掩码生成、模型末尾归一化、LM head 和采样不在本次导出边界。要构成整个推理过程，还需要这些上游/下游计算；不能把“代表层图重复 L 次”称为本轮已经完成的整网导出。

## 13. 实际 ONNX 节点数对照

| 模型/层 | 原始 ONNX | onnxsim | 本文特别保留的差异 |
|---|---:|---:|---|
| Qwen2.5 | 232 | 67 | QKV 偏置 |
| Qwen3 | 253 | 80 | Q/K 头内 norm，非 H/Q 的 head_dim |
| Llama3.2 | 230 | 64 | 普通 GQA；本轮随机参数 |
| Gemma 局部 | 300 | 110 | 局部 mask、六组 norm、GELU |
| Gemma 全局 | 300 | 110 | 全局 mask 与位置频率规则 |
| Phi4-mini | 305 | 74 | 融合 QKV、融合 gate/up、部分 RoPE |
| Qwen3.5 全局 | 335 | 95 | Q/output-gate 分割、PV 后 Sigmoid 门乘 |
| Qwen3.5 GDN | 374 | 132 | 卷积、L2 norm、delta 状态更新、norm 后门乘 |
| Granite | 285 | 84 | 动态 top8、专家权重 Gather、加权归并 |
| Falcon-H1 | 998 | 173 | 并行分支、MuP/K 缩放、SSM、门乘后共享 norm |

不要按这些节点数推算相同比例的面积、功耗或时延变化。形状、张量精度、权重与状态访问、分块、融合以及硬件调度都还会改变实际成本。

## 14. 来源及与前版的核对说明

本文依据同目录实际导出的 config、raw/simplified.graph.json、receipt，以及对应 Transformers 实现整理。完整 SVG 与 JSON 都可以从图册查到；实际权重 ONNX 位置由实验索引给出。

核对时纠正了上一版手工语义图的两处 Falcon 表达：本次配置使用完整 128 通道 RoPE；K 在 RoPE 前另乘 key_multiplier。本文已明确画出，不沿用旧手工图的部分 RoPE 标记和遗漏的 K 缩放。旧导出及旧手工图文件未在本次文档整理中覆盖。

Granite 的 attention_multiplier=0.015625 也在本文显式标出，避免把旧图中的通用“attention scale”误读成 1/sqrt(D)。

本文件由独立实验目录的字符图文档归档而来，原始文件保留。此次目录整理未重新运行模型或导出 ONNX；任务为 Issue #116。
