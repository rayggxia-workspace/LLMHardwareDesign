# 官方Qwen3固定版本的局部参数提取合同

本说明保留工具作者的小预检和实现边界；随后实际11tensor/14embedding取数及服务器95247/95248验证已完成，当前结论见[真实数据报告](QWEN_LAYER0_NUMERIC_RTL_REPORT.md)。完整model文件SHA仍未实算。

Issue151 / PR152，Melodydt；本轮研究输入`71c819c2f87e5df8d46c373df0f062fba6cd0600`。数据固定为官方`Qwen/Qwen3-0.6B` revision `c1899de289a04d12100db370d81485cdf75e47ca`。本工具不读取凭据、HF token、其他成员服务器目录或ref-project，不运行模型/RTL，不启动服务器。源码先提交，再由根提供实际源码commit运行提取，数值运算在获授权Slurm任务中另行执行。

## 1. 已实际小预检与预计体积

本机受限沙箱第一次网络请求失败，回执保留`network-preflight-sandbox.json`；当时已发起的单次沙箱外公开小预检随后自然完成。官方API返回200且sha等于固定revision；model.safetensors请求`bytes=0-7`返回206、`Content-Range: bytes 0-7/1503300328`、8字节，little-endian U64头长为35552。此后按根要求停止重复网络探测，没有在本次预检下载11张量或整模型。结果见`network-preflight.json`。[固定官方元数据](https://huggingface.co/api/models/Qwen/Qwen3-0.6B/revision/c1899de289a04d12100db370d81485cdf75e47ca?blobs=true)

官方metadata声明文件1503300328B，LFS预期SHA256为`f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b`。**局部Range下载不能验证整个文件的SHA；工具始终记录full_file_downloaded=false、full_file_sha256_verified=false。** 每个实际取得的tensor/embedding row及其FP32转换文件另计算完整实际SHA。

| 数据 | 预计字节 |
|---|---:|
| layer0全部11张量 BF16 | 31461888（30MiB+4608B） |
| 对应FP32文件 | 62923776 |
| 以上两份合计 | 94385664，约90MiB |
| 每个选定embedding行 BF16/FP32 | 2048 / 4096 |
| config.json | 726 |
| tokenizer_config.json | 9732 |
| vocab.json | 2776833 |

不取整embedding表，不取LM head/其它层。vocab/config三个小文件完整下载并核对官方metadata的Git blob SHA1及长度，再记录实际SHA256；没有下载11.4MB tokenizer.json或merges.txt，因为本轮只解析明确的vocab pieces，不做BPE/聊天模板。

## 2. 11张量与文件ABI

全部名字以`model.layers.0.`为前缀，保持原生PyTorch contiguous row-major，不预先转置/量化：

| 后缀 | BF16 shape |
|---|---|
| input_layernorm.weight | [1024] |
| self_attn.q_proj.weight | [2048,1024] |
| self_attn.k_proj.weight / v_proj.weight | 各[1024,1024] |
| self_attn.o_proj.weight | [1024,2048] |
| self_attn.q_norm.weight / k_norm.weight | 各[128] |
| post_attention_layernorm.weight | [1024] |
| mlp.gate_proj.weight / up_proj.weight | 各[3072,1024] |
| mlp.down_proj.weight | [1024,3072] |

每个张量保留`.bf16le`原始little-endian U16位模式，再产生`.f32le`：将U16左移16位得到IEEE754 FP32位模式，无重新舍入、不经过Python浮点、不改轴顺序；负零保留，非有限BF16参数拒绝。无需numpy、torch、safetensors或tokenizers运行库。

`manifest.json`顶层提供repo/revision/source_commit/extractor_sha256、config_file/vocab_file/tokenizer_config_file/token_sequences_file；`tensors`中每项提供name、shape、source_dtype、source_range、bf16le_file/bf16le_bytes/bf16le_sha256、f32le_file/f32le_bytes/f32le_sha256。`embedding_rows`使用同一字段并增加token_id，shape=[1024]。**文件路径相对manifest，SHA均为实际对应文件内容。** `source_commit`是根提供的实际40hex获取代码commit，脚本另记自己的内容SHA；不把这个字段伪称为自动远端Git认证结果。

header按safetensors标准读取8字节长度与JSON，检查全部dtype/shape/字节范围及无重叠、无间隙、覆盖固定文件payload；11目标张量和embedding必须为指定名称、BF16及精确shape。文件header只确定取数偏移，不自动证明实际tensor已与整文件LFS摘要做过验证。

## 3. 合法token输入与Attention→F边界

`qwen3-token-prefixes.json`列出四个明确的exact vocabulary pieces序列，cal/eval各两组、每组4token。工具使用完整vocab及added_tokens_decoder映射为ID，并检查0≤ID<151936及piece真实存在；找不到就失败，绝不默默换成UNK或改做随机hidden。只对去重后的这些合法ID取embedding行。

输出`token-sequences.json`含`token_sequences:[{id,split,pieces,token_ids}]`。这些是小前缀诊断，不是自动BPE结果、不带chat template，也不是代表性语言校准/质量集。

下一数值工具使用真实trained embedding行、input RMS gamma、QKV/QKnorm/RoPE/因果Attention/Wo和原始hidden残差，产生layer0真实F输入Y；F使用**post_attention_layernorm** gamma、MLP三权重和原Y残差。它不能把preNorm输出、任意randn hidden或input_layernorm gamma错当F输入/gamma。完整FP32 Attention→F与量化评价由数值任务执行，manifest中的FP32_attention_or_F_input_generated=false表示本提取器没有做这一步。

## 4. 可复制命令和失败边界

```powershell
python -B -X utf8 work/Melodydt/151/fetch_qwen3_layer0.py --self-check
python -B -X utf8 work/Melodydt/151/fetch_qwen3_layer0.py --output-dir <新的数据目录> --token-cases work/Melodydt/151/qwen3-token-prefixes.json --source-commit <实际获取代码40hex> --timeout 30 --chunk-bytes 1048576 --retries 2
```

output-dir必须不存在；工具不覆盖既有run，不在失败后删除已取得的证据。`--preflight-only`在新目录仅获取metadata/header，不取张量；不应为同一网络状态不断重复预检。根可在本机取得公开约30MiB，再将数据包传往本人Slurm任务存储；本脚本不执行scp/sbatch或创建服务器进程。

每段Range使用固定revision URL加公开`?download=true&issue151_range=start-end`隔离错误缓存。必须HTTP206、Content-Range起止/total完全相符、Content-Length和实际字节长完全相符、identity encoding；200在读body前拒绝。重定向仅允许HTTPS官方HF域，不打印/保存签名URL，失败只记录安全stage、异常类型和HTTP状态码，不输出urllib异常repr或traceback。

全部成功才写`manifest.json`；失败写`fetch-receipt.json`的FAILED_CLOSED_PARTIAL_NOT_ADMITTED，残留文件不能当完整数据集。成功标记`PASS_QWEN_RANGE_EXTRACT`也仅表示这些tensor/row的数据完整性合同通过，不表示整文件摘要、推理质量或RTL通过。

## 5. 本次实际验证

已运行纯内存`--self-check`：206正例、7项错误Range拒绝、BF16→FP32包括负零的逐字节正例及3项非法/非有限拒绝；没有启动本地HTTP测试服务器。Python AST/JSON解析和UTF8 LF检查通过。小网络预检与这些无网络检查分开保留；正式30MiB取数、实际tensor SHA、Attention→F输入与模型误差由后续真实运行回执补齐，未执行项不预填通过。
