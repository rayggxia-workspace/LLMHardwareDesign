# Issue 23：Transformers 4.57.6 Qwen3 捕获接口复核

2026-10-22，仅官方源码静态核对；未安装包、未运行模型、未修改 root 工作树。GitHub 认证已核对为 Liangruizhi / 182389313 / 2663955430@qq.com。

建议直接包装显式 eager 后端的 `eager_attention_forward`：它接收到的 Q/K 就是实际 post-RoPE 张量，K/V 还包含刚追加的 cache 前缀；不要把 q_proj/k_proj 输出冒充 attention 输入。root 已选择这个方案。

## 固定版本与字节证据

官方 tag `v4.57.6` → commit `753d61104116eefc8ffc977327b441ee0c8d599f`，提交日期 2026-01-16。已保存原文件并复算 Git blob SHA-1，与 GitHub 返回值一致；SHA-256 如下：

| 源文件 | SHA-256 |
|---|---|
| modeling_qwen3.py | `4b95c371fd26d40c69083dab36ac1eafd8cf82b415a0bb827275097c5ad2305b` |
| cache_utils.py | `f4e11caf14c75bdefa5e3003b93ef0e8b97fb6103375705ad944b0b344d7da8a` |
| configuration_qwen3.py | `27863e9718fdbc899f2d0e567621e4d3d36d8dc500c1d54b49dba4242d08d2bd` |

完整 URL、Git blob、字节数与许可在本目录 `source-manifest.json` 和 `upstream/`。runner 应另行记录实际安装包版本及这两个已加载模块文件的 SHA；版本字符串不能代替实际文件校验。

官方来源：[Qwen3 实现](https://github.com/huggingface/transformers/blob/753d61104116eefc8ffc977327b441ee0c8d599f/src/transformers/models/qwen3/modeling_qwen3.py)、[Cache 实现](https://github.com/huggingface/transformers/blob/753d61104116eefc8ffc977327b441ee0c8d599f/src/transformers/cache_utils.py)、[Qwen3 配置类](https://github.com/huggingface/transformers/blob/753d61104116eefc8ffc977327b441ee0c8d599f/src/transformers/models/qwen3/configuration_qwen3.py)。

## 最小 API 与实际数据流

`model.model.layers[i].self_attn` 是 Qwen3Attention。其 `forward(hidden_states, position_embeddings, attention_mask, past_key_values=None, cache_position=None, **kwargs)` 返回 `(attn_output, attn_weights)`；前者已通过 o_proj，形状 `[B,T,hidden]`。eager 权重形状 `[B,Hq,T,K]`；其他后端可能不提供权重。

实现 197–230 行的顺序是：

`q_proj → view[B,T,Hq,d] → q_norm → transpose[B,Hq,T,d]`

`k_proj → view[B,T,Hkv,d] → k_norm → transpose[B,Hkv,T,d]`

`v_proj → view/transpose[B,Hkv,T,d]`

随后 205 行对 Q/K 施加 RoPE；210 行调用 cache.update；216 行调用选定 attention backend；最后把 core 输出 `[B,T,Hq,d]` reshape 为 `[B,T,Hq*d]` 后通过 o_proj。q_norm/k_norm 是沿最后 head_dim 轴做 RMSNorm，并含可学习权重，不能遗漏。

此前固定的 [Qwen3-0.6B config revision c1899de289a04d12100db370d81485cdf75e47ca](https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/config.json) 为 hidden=1024、Hq=16、Hkv=8、**head_dim=128**、intermediate=3072、28 层。因而 q_proj/o_proj 输入宽度为 2048，不是 hidden=1024。runner 必须再次绑定本次实际下载 revision/config。

| 捕获位置 | 真实含义与形状 |
|---|---|
| q_proj 输出 | 原始投影 `[B,T,2048]`；没有 q_norm 或 RoPE |
| q_norm 输出 | `[B,T,16,128]`；已经 head norm，尚未 transpose/RoPE |
| eager backend 的 query | 实际 post-RoPE Q `[B,16,T,128]` |
| eager backend 的 key/value | 实际缓存更新后的 K/V `[B,8,K,128]`；尚未 repeat_kv |
| eager core 返回的 attn_output | `[B,T,16,128]`，尚未 flatten/o_proj |
| self_attn 返回的第一个张量 | `[B,T,1024]`，已经 o_proj |
| mlp.down_proj 前置 hook 输入 | 实际 `SiLU(gate_proj(x))*up_proj(x)`，`[B,T,3072]` |

eager 实现内部才将 K/V 扩展至 Hq（132–155 行）；缓存本体只存 Hkv。q/k RoPE 使用 `rotate_half` 的前半/后半布局，不是相邻偶奇两维旋转。

`model.model.rotary_emb` 每次模型 forward 生成 `(cos,sin)`，在所有层间共享。输入 position_ids 通常是 `[Bpos,T]`；默认 cache_position.unsqueeze(0) 时 Bpos=1，可向 batch 广播，故 cos/sin 不应硬断言首维等于 B。返回 dtype 随输入，内部频率计算强制 FP32；dynamic RoPE 类型还可能更新内部频率状态。捕获实际传入的 position_embeddings / cache_position 比重新调用 rotary_emb 更安全。

## DynamicCache

用关键字构造：`cache = DynamicCache(config=model.config)`。**首个位置参数是 ddp_cache_data，不是 config。**

- 本版接口为 `cache.layers[i].keys` / `.values`，兼容读取 `cache[i]` 返回二元组；不要沿用旧版顶层 key_cache/value_cache 假设。
- 传入 config 后可先建层对象，但 keys/values 初始为 None，`is_initialized=False`；`cache.get_seq_length(i)` 未初始化时返回 0。
- 普通 `DynamicLayer.update` 使用 `torch.cat([old,new], dim=-2)`，重绑 keys/values，再返回完整缓存；不是向原张量原地追加。长度轴为 -2，形状 `[B,Hkv,K,d]`。
- Qwen3 调用 update 时，输入 K 已过 k_norm 和 RoPE；V 没有 RoPE。当前层 eager backend 的 K/V 应与 `cache.layers[module.layer_idx].keys/values` 相同。
- 在完整模型 forward 结束前，只应检查当前已更新层；后面的层可能仍为旧长度或未初始化。
- 先断言实际层类型为 full_attention / `not layer.is_sliding`。滑窗缓存会裁剪，`get_seq_length` 可表示累计长度，不能套用普通前缀保存检查。
- `past_key_values` 非 None 时，attention 内部会 update；**不能依靠 use_cache=False 阻止一个传入 cache 被修改**。完整前缀 reference 应用 `past_key_values=None`，基线、观测和负例各自使用独立 cache。

普通 full-attention 下，旧前缀检查可比较更新后 `new_keys[..., :old_len, :]` 与旧快照，同时检查新增长度。严格 bitwise 检查应比较 raw dtype bytes（例如 contiguous 后 view(torch.uint8) 再转 bytes），不能仅把浮点 `torch.equal` 叫作逐位相等；记录 shape/dtype 后再哈希。Q/K snapshot 使用 clone，不能让负例修改生产 cache 的 view。

## 最小捕获模板（静态建议，未执行）

加载/基线均明确 `attn_implementation="eager"`，eval + inference_mode；不要为捕获悄悄从 SDPA 切后端而将差异归为 hook 影响。以下只示意作用域，不承担 runner 的文件写入、版本和验收逻辑：

```python
from contextlib import contextmanager
from transformers.models.qwen3 import modeling_qwen3 as qmod

@contextmanager
def capture_actual_attention(sink, selected_layers):
    original = qmod.eager_attention_forward

    def observed(module, query, key, value, attention_mask, *args, **kwargs):
        if module.layer_idx in selected_layers:
            # Record original shape/stride/dtype/device before cloning.
            sink(module.layer_idx, {
                "q_post_rope": query.detach().cpu().clone(),
                "k_cache_post_rope": key.detach().cpu().clone(),
                "v_cache": value.detach().cpu().clone(),
                "mask": None if attention_mask is None
                        else attention_mask.detach().cpu().clone(),
                "scaling": kwargs.get("scaling"),
            })
        return original(module, query, key, value, attention_mask, *args, **kwargs)

    qmod.eager_attention_forward = observed
    try:
        yield
    finally:
        qmod.eager_attention_forward = original
```

backend 的 mask 是实际 additive causal/padding mask（可能为 None），不是 tokenizer 的二维 attention_mask；trace 应保存收到的 mask，而不是另造下三角。decode query 的绝对位置是已有前缀长度，不应重新从 0 算。

模块 hook 注意 kwargs：DecoderLayer 用 `self.self_attn(hidden_states=..., position_embeddings=..., ...)` 调用，所以 attention 前置 hook 使用 `with_kwargs=True`，从 kwargs 取 hidden_states/position_embeddings/cache_position；args[0] 可能不存在。`mlp.down_proj` 则在官方实现中以位置参数调用，`register_forward_pre_hook` 的 args[0] 就是实际 SwiGLU 中间结果；hook 返回 None，且不原地改 tensor。普通 forward hook 中 self_attn 输出是二元组，不要当单个 tensor。

## 功能影响与验收

包装的是进程级模块全局函数，会影响同进程所有 Qwen3 eager 调用；只在单线程主调用作用域启用，按 layer_idx 筛选，避免嵌套或其他模型并发，始终 finally 恢复。所有 nn.Module hook handle 也在 finally remove。不要用 torch.compile、导出图或 fusion backend 声称同一 hook 路径已覆盖。

复制张量会占内存并改变 CPU 时间、缓存行为；观测流不是无扰动性能测试。只选少量层/步骤，记录原张量 metadata，保存函数原输出对象；sink 只操作 clone。后端原函数参数与返回值完全透传，不用手写 attention forward 替代真实函数。

root 已计划：相同输入、同一 eager backend、独立 cache，比较未观测/观测流每步 logits 和 KV；在捕获点核对 post-RoPE K/V 与当前 DynamicCache 层，并与完整前缀 reference 的选定边界对照。必须把这些实际验证结果写入实验记录；本审查仅确认源码/API，不宣称上述运行已通过。
