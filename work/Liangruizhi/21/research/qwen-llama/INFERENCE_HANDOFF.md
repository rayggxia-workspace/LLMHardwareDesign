# Qwen3-0.6B 真实权重推理：只读可行性预检

观测时间：2026-10-22 11:20 UTC。本轮只读取系统、Python 包、官方模型与依赖元数据；没有下载权重、安装依赖、运行模型、创建 Issue 或访问服务器。该模型是下一阶段完整 prefill/decode 的资源可行候选，不是最终 benchmark 决定。

## 当前结论

本机具备先做小上下文 CPU FP32 正确性实验的资源条件，但当前环境尚不能执行：唯一核验的解释器 `D:/APP/Python/python.exe` 为 CPython 3.13.14，缺少 torch、transformers、safetensors、tokenizers、huggingface_hub、accelerate；目标项目的 `.venv` 不存在。NumPy 2.5.0 已有，但不建议让新实验继承全局包。

Intel Core Ultra X7 358H 为 16 核/16 逻辑处理器。系统可见内存 31.55 GiB，观测时空闲约 14.75 GiB；D 盘空闲约 349.43 GiB。Intel Arc B390 被 WMI 枚举，驱动 32.0.101.8509；WMI 的 AdapterRAM 字段不能用作可靠的共享显存容量。没有 torch、xpu-smi 或 sycl-ls，因此没有验证 GPU 后端、可用显存或矩阵运算。不要把 GPU 路线写成已经可用。

## 固定输入和许可

候选为公开、无门控、Apache-2.0 的 [Qwen/Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B/tree/c1899de289a04d12100db370d81485cdf75e47ca)，固定 revision `c1899de289a04d12100db370d81485cdf75e47ca`，无需 Meta 门控账户。已读取该固定 revision 的 [LICENSE](https://huggingface.co/Qwen/Qwen3-0.6B/raw/c1899de289a04d12100db370d81485cdf75e47ca/LICENSE)，标题确认为 Apache License Version 2.0，版权行为 Alibaba Cloud。Hugging Face 官方 API 的该 revision 元数据列出 **1 个 safetensors 文件，共 1,503,300,328 字节（约 1.400 GiB）**：

- `model.safetensors`
- 预期 LFS SHA-256：`f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b`

以上是远端元数据，不是本地权重校验结果。下载后必须对本地字节重新计算 SHA-256。API 同时报告 BF16 tensor elements=751,632,384，不应把名称“0.6B”乘 2 当作下载大小，也不应直接将此数称为 tied model 的独立参数个数。

固定 config：D=1024、F=3072、L=28、Hq=16、Hkv=8、head_dim=128、vocab=151936、tie_word_embeddings=true、max_position_embeddings=40960、torch_dtype=bfloat16。依 config 结构推算 tied 独立参数数为 596,049,920；这只是结构推算，尚未读取 tensor header 或实例化模型验证。模型卡中的上下文描述与固定 config 字段应分别记录。本次方案不测试长上下文。

## 依赖方案：仅元数据核验，未安装

[Qwen 官方推理说明](https://qwen.readthedocs.io/en/stable/inference/transformers.html)要求 transformers>=4.51.0，建议 torch>=2.6，原生 Qwen3 不需 trust_remote_code。已核验下列发行版存在且 wheel 标签兼容本机 CPython 3.13/Windows AMD64；核心版本约束相容，但尚未完整求解和导入：

| 包 | 候选版本 | 作用 |
|---|---|---|
| torch | 2.10.0+cpu | 官方 CPU wheel；先验证 CPU 路线 |
| transformers | 4.57.6 | 原生 Qwen3 |
| safetensors | 0.7.0 | 权重载入 |
| tokenizers | 0.22.2 | 兼容 transformers 的 >=0.22.0, <=0.23.0 |
| huggingface-hub | 0.36.2 | 兼容 >=0.34.0, <1.0 |

直接指定 `device='cpu'` 并普通加载不需要 accelerate；仅使用需要它的加载/分配 API 时另行安装已核验的 1.12.0。无需 torchvision/torchaudio。官方 CPU wheel URL、SHA 和 PyPI Requires-Dist 保存在 `dependency-candidate-metadata.json`。没有下载 wheel 包体，仅获取元数据。

下一阶段经独立任务跟踪后，可在 D 盘新建隔离 venv；下面是**未执行**的 PowerShell 示例，路径由下一阶段负责人与 worktree 一同登记：

```powershell
$stage = 'D:/Projects/Codex/qwen3-inference-stage'
New-Item -ItemType Directory -Force -Path "$stage/tmp", "$stage/cache", "$stage/weights", "$stage/results" | Out-Null
$env:TEMP = "$stage/tmp"
$env:TMP = "$stage/tmp"
$env:TMPDIR = "$stage/tmp"
$env:HF_HOME = "$stage/cache/huggingface"
$env:HF_HUB_CACHE = "$stage/cache/huggingface/hub"
$env:TORCH_HOME = "$stage/cache/torch"
$env:PIP_CACHE_DIR = "$stage/cache/pip"
$env:PYTHONPYCACHEPREFIX = "$stage/cache/pycache"
& 'D:/APP/Python/python.exe' -B -m venv "$stage/venv"
& "$stage/venv/Scripts/python.exe" -B -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.10.0+cpu'
& "$stage/venv/Scripts/python.exe" -B -m pip install 'transformers==4.57.6' 'safetensors==0.7.0' 'tokenizers==0.22.2' 'huggingface-hub==0.36.2'
& "$stage/venv/Scripts/python.exe" -B -m pip check
& "$stage/venv/Scripts/python.exe" -B -c 'import torch, transformers, safetensors; print(torch.__version__, transformers.__version__, safetensors.__version__); print(torch.ones(2,2) @ torch.ones(2,2))'
```

这些命令不是完整可复现实验记录：安装后还需保存实际完整 lock/pip freeze、wheel 来源/版本及校验、CPU 后端/线程、输入和结果。若安装器回退到源码编译，先停止并排查兼容性。不要自动更换其他账户、门控模型或全局 Python 环境。

## 分阶段运行与验收

1. 环境门槛：成功导入核心包、`pip check`、CPU FP32 小矩阵、`AutoConfig` 固定 revision 原生识别；记录真实包版本。该步骤尚未执行。
2. 下载门槛：仅固定 revision 的 `config.json`、`generation_config.json`、`tokenizer.json`、`tokenizer_config.json`、`merges.txt`、`vocab.json`、`LICENSE`、`model.safetensors`。权重/缓存放 D 盘且不入 Git；不要使用 `revision='main'`。记录实际字节及 SHA-256，权重必须匹配上述值。保留 LICENSE；本次核验官方许可标签及固定 LICENSE 原文，未进行法律意见分析。
3. 单模型正确性：原生 `AutoModelForCausalLM.from_pretrained(local_path, torch_dtype=torch.float32, attn_implementation='eager', trust_remote_code=False)`，CPU、`.eval()`、`torch.inference_mode()`，batch=1，先 T=16，再 64/128。先做显式固定 token 的 forward/cache 实验，再选 tokenizer prompt；不启用编译、量化或自动设备分配。
4. 对同一固定 token 序列，比较完整 prefix 重算与 prefill 后逐 token cache decode 的每一步最后 token logits；位置、attention mask、cache_position 和 dtype 必须相同。记录 max-abs/relative error、完整 shape、cache 实际字节、峰值内存和耗时，不预先承诺某个误差阈值。解码先限 8 个 token；若用 chat template，显式 `enable_thinking=False`，避免把思维链长度混入算子实验。
5. 正确后再比较模块分割/融合的等价性与数据移动；一次先测 4 线程，再决定是否测 8 线程。不以 CPU wall-clock 代替目标硬件 PPA 或宣称吞吐提升。GPU/XPU 是另一个需验证后端、驱动和数值的扩展任务。

资源估算（不是实测）：序列化 tensor 的 FP32 容量上界估算约 2.800 GiB，可能另有 BF16 staging、Python/加载器开销和激活。建议首轮为进程预留约 8 GiB 可用内存和至少 10 GiB D 盘空间，并实际监测峰值；模型加载失败不能靠此估算宣称内存充足。FP32 KV cache 为 `2*B*T*28*8*128*4 = 229376*B*T` 字节，B=1、T=128 为 28 MiB；完整 logits `[1,128,151936]` 约 74.19 MiB。不要首轮运行 config 最大上下文。

## 待解除的风险与证据边界

- 当前缺依赖，模型加载、prefill、decode、tokenizer 和数值误差都**未执行**。轮子存在与版本约束相容不证明 Windows DLL/ABI 运行成功；独立 venv 避免全局 NumPy 2.5 的潜在影响。
- CPU 时延与峰值内存未知；不要给未测 tokens/s。加载时复制和缓存/目标目录复本会增加磁盘及内存占用。
- Hugging Face CDN/Xet 网络、限流、断点缓存和本机杀毒可能影响下载。公开模型无需令牌，不读取账户凭据；失败时记录网络阻塞。必要的 Xet 回退参数应在下一阶段显式记录，不能暗改全局设置。
- [PyTorch 的 Intel GPU 文档](https://docs.pytorch.org/docs/2.14/notes/get_start_xpu.html)列出相关新平台支持，但该文档不能证明本机 B390 与候选 torch 2.10、现有驱动组合已经可用。尚未运行 `torch.xpu.is_available()`；CPU wheel 不提供 XPU 实验依据。
- 这里证明的是有条件资源可行性，尚不构成真实模型 benchmark 结果、Block 最优边界、DAC 论文贡献或物理 PPA。

机器数据见 `inference-preflight.json`；输入元数据见 `weights-candidate-metadata.json`。三者与原有缩小算子正确性结果分别归档，避免将 synthetic FP64 检查混称为真实权重模型验证。
