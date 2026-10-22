# Issue23 本机推理环境交接

更新时间：2026-10-22T11:45:51.601996+00:00。状态：环境与固定输入已就绪。本安装子任务没有实例化或执行模型；正式推理结果由下游任务单独记录。

- Issue：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/23；root分支 `task/23-qwen3-trace`。
- 独占目录：`D:/Projects/Codex/qwen3-inference-20261022/environment`，创建前已核对不存在。
- 解释器：`D:/Projects/Codex/qwen3-inference-20261022/environment/.venv/Scripts/python.exe`，来自既有 `D:/APP/Python/python.exe` 3.13.14，无全局安装。
- 模型路径：`D:/Projects/Codex/qwen3-inference-20261022/environment/weights`。
- 权重模型：`Qwen/Qwen3-0.6B`；固定 revision `c1899de289a04d12100db370d81485cdf75e47ca`，公开、无门控、Apache-2.0。

## 实际完成的验证

25个runtime wheel先完整下载，逐个核对官方PyPI或PyTorch CPU源的SHA-256，再用离线 `--no-index --only-binary=:all: --require-hashes` 安装。安装退出0；`pip check`为 `No broken requirements found.`。torch 2.10.0+cpu、transformers 4.57.6、safetensors 0.7.0、tokenizers 0.22.2、huggingface-hub 0.36.2、NumPy 2.5.4导入通过；原生 `Qwen3ForCausalLM` 导入通过。CPU FP32 2×2全1矩阵相乘得到全2矩阵。没有GPU探针或模型推理。

环境工具pip 26.1.2来自既有Python的ensurepip捆绑wheel，其SHA已与官方PyPI元数据匹配。25个runtime依赖的hash lock在 `receipts/requirements-lock.txt`，完整26个已安装发行版（含pip）在 `receipts/installed-versions.txt`，pip种子来源另见 `receipts/bootstrap-provenance.json`。wheel文件本体、venv、权重、缓存和日志全部保留，不清理。

## 固定输入

严格只下载以下8个模型文件。每个小文件核对上游Git blob身份或LFS SHA；权重实际SHA匹配授权预期。

| 文件 | 字节 | SHA-256 |
|---|---:|---|
| config.json | 726 | `660db3b73d788119c04535e48cf9be5f55bc3100841a718637ae695b442f27dd` |
| generation_config.json | 239 | `2325da0f15bb848e018c5ae071b7943332e9f871d6b60e2ed22ca97d4cb993d2` |
| tokenizer.json | 11422654 | `aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4` |
| tokenizer_config.json | 9732 | `d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101` |
| merges.txt | 1671853 | `8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5` |
| vocab.json | 2776833 | `ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910` |
| LICENSE | 11343 | `832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e` |
| model.safetensors | 1503300328 | `f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b` |

仅用标准库解析safetensors头，确认311个BF16 tensor、751,632,384元素、payload 1,503,264,768字节，所有范围连续不重叠且文件大小吻合。`lm_head.weight`与`model.embed_tokens.weight`各[151936,1024]，分占不同序列化范围，两个范围的SHA相同；尚未验证实例化后的参数共享。详见 `receipts/safetensors-header-summary.json`。

## 使用方式与记录边界

从已有解释器启动：`& 'D:/Projects/Codex/qwen3-inference-20261022/environment/.venv/Scripts/python.exe' -B <本任务runner.py> ...`。调用方把TEMP/TMP/TMPDIR、PYTHONPYCACHEPREFIX、HF_HOME/HF_HUB_CACHE、TORCH_HOME及其他缓存指向自己的D盘任务目录，设置 `HF_HUB_DISABLE_IMPLICIT_TOKEN=1`；使用本地模型目录和 `local_files_only=True`，不自动GPU或trust_remote_code。不要改写此venv、wheelhouse或weights。默认torch线程16，正式实验必须显式固定并记录自己的线程数。

第一次来源清单脚本将setuptools内嵌vendor的dist-info误计为wheel自身元数据，修正为只认顶层METADATA后继续，失败记录保留。成功安装期间，pip自动预编译曾因完整D缓存前缀超过Windows路径限制而产生FileNotFoundError警告；安装退出0，后续导入、pip check和CPU小矩阵均通过。现行bootstrap helper已加 `--no-compile` 和 `PYTHONDONTWRITEBYTECODE=1` 预防下次同类警告，没有改系统长路径设置。**当前helper包含安装启动后的预防改动，实际执行命令以原始日志及environment-handoff.json为准，不能把现行helper字节冒充原运行源码。**

轻量交接：`receipts/environment-handoff.json`。来源、下载、安装report与实测环境均在receipts；原始日志在logs。`ARTIFACT-SHA256.json`只索引控制脚本/交接/轻量日志，权重和wheel字节校验分别在各自manifest，不对整个venv/cache重复哈希。环境交接可继续使用，但不是可任意搬迁的虚拟环境，也不构成正式模型或PPA结果。
