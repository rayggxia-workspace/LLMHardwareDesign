# Issue32 GPU 模型证据工具

本任务分支基于 main 1a98e9d；独立正式代码，不改 Issue23 严格绑定 Qwen3-0.6B 的 runner。
已阅读 Issue23/PR24、Issue25/PR26@2cd9ca15、相关交接。统一完整精度合同尚未发布；本目录配置只是**本地候选筛查**。
尚未运行的条件不能由工具存在推定通过。最终结果以 results 索引和实验报告为准。

## 顺序与复跑

隔离环境：D:/Data/llm-gpu32/.venv。权重、wheel、下载分段、原始检查点、临时数据均留 D 盘，不进入 Git。
Python3.12、torch2.10.0+cu128、transformers5.17.0；实际全依赖由 probe.py 和 pip freeze 记录。
不升级全局驱动、不卸载他人模型、不静默 CPU offload。WDDM 共享 GPU 存在显示负载，结果不能当作独占 GPU 基准。

在干净已提交源码下，从仓库根目录运行（PowerShell 单行完整命令）：

```powershell
& D:/Data/llm-gpu32/.venv/Scripts/python.exe -B project/experiments/gpu_model_evidence/run.py --model-dir D:/Data/llm-gpu32/models/qwen35 --out D:/Data/llm-gpu32/runs/qwen35-reference-replay --phase reference --lengths 512 2048 4096 8192
```

输出目录必须不存在。先用 `--short-only` 完成 128+16、校准、验证和短状态敏感性；之后 integer 阶段以
`--phase integer --reference-dir <reference run> --short-only` 对照；最后执行上面全长度 reference。
统一合同未冻结时，整数阶段仅候选矩阵敏感性，不宣称项目整数验收。
短参考若失败，工具拒绝继续扩长，保留 JSON/traceback；真实 OOM/数值失败不得删除。
每个模型独立进程，当前模型所有条件完成后再下载/加载下一个。

Qwen3.5 官方 HF revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`；prepare.py 固定元数据、所有 LFS SHA256 和非 LFS Git blob ID。
ModelScope 仅作为**同字节权重**传输替代；非权重文件也须匹配固定 HF blob，不能静默采用不同配置。
Qwen2.5 使用 Qwen 官方 ModelScope 固定 commit `5defd2796acd3cb2051bb4c787eddc7f8f35e113`；prepare_ms.py 固定官方文件清单和逐文件 SHA256，来源与 HF 分开标明。
Qwen2.5-3B 使用 qwen-research 许可，不宣称 Apache2。
CUDA wheel SHA256 `fbde8f6a9ec8c76979a0d14df21c10b9e5cab6f0d106a73ca73e2179bc597cae` 来自 PyTorch 官方 cu128 索引，国内镜像仅传输，安装前核验。

## 数据字段与证据边界

- run-manifest.json：源码 commit/文件 SHA、官方模型 revision/本地文件 SHA、完整冻结配置、命令、GPU/显存起点、offload=false。
- loaded-model.json / loading-info.json：实际语言模型类、源码 SHA、参数/配置、加载缺项和内存。语言权重缺失即失败；不执行视觉或 MTP 路径。
- inputs.json：固定 teacher-forced token IDs，calibration/validation 分开；不使用模型生成反馈。动态 absmax 无拟合参数；校准只检查有限值，不调整阈值。
- results.json：correctness、quality、state_sensitivity、performance、failures；失败包含 traceback。`completed` 表示程序完成，数值验收必须看各字段，不能等同全项目 done。
- quality：mean_kl 是 reference 概率到 candidate 的 KL；nll 是固定下一 token 的平均交叉熵（自然对数）；nll_delta/candidate-reference、top1_agreement。自编中英/代码诊断文本仅 4×128 token，不能外推通用语言质量。
- events.json：有序真实模块接口形状/dtype/逻辑字节/存储大小/stride。包含投影、attention/递推模块、norm、MLP 和 decoder 残差接口；不声称从 hook 恢复完整跨模块 DAG、融合 SDPA 内部概率/归约或实测流量。
- cache：逐层真实 KV/conv/recurrent 张量，logical_bytes 与去重 storage_bytes 分开。measured_traffic_bytes=null 表示未测，不是0。storage 不能与逻辑张量简单相加当峰值。
- quantized-matrices.json：实际 INT8 权重和 FP32 通道 scale 字节、权重量化误差、INT32 最坏累加界。integer-kernel-stats.json 给真实调用数/最大观察累加/饱和。实际调用 torch._int_mm；输出 scale 相乘/偏置仍浮点，无整数 M/r 重定标、无整数非线性/状态。
- state_sensitivity：INT8/INT16候选的 native→quantize→dequantize 状态扰动；**假量化**，状态更新仍原生浮点。短条件每次 decode call 后舍入；长条件每256-token prefill边界和逐 decode 舍入，不能说逐 token prefill 全整数状态更新。保留每层误差汇总，不保存每步全状态。
- delta 函数 PT：Qwen3.5 layer0 第一次 chunk/第一次 recurrent 调用的真实 Q/K/V、log-decay g、sigmoid beta、初态/末态/输出；边界在内部 FP32 QK L2Norm 和 Q/√d **之前**。delta-parameters.pt 保存 A_log/dt_bias/卷积权重；preconv-qkv.pt 保存 layer0 两次卷积前投影；selected-cache.pt 保存该层128及129词元时卷积/递推缓存。没有捕获所有层/步。
- timings.csv：一次预热与3次测量，全部保留；同步 CUDA 的 prefill/decode/总墙钟时间、peak allocated/reserved bytes，tokenization/loading不计。观察器运行分开，整数带统计的运行不进入性能表。不是 CUDA 单核时间，也不是目标芯片吞吐/通信流量。
- long PT：每档 one/chunk 的末 logits 与 layer0/3 原始缓存。所有层状态比较流式汇总；完整状态只临时放 CPU 比较，不长期保存。
- artifact-index.json：每个运行产物的字节/SHA，可由 verify.py 独立读回。选定递推用不同 einsum 顺序重放；错误初态负例只要求 cached 单步拒绝，prefill可能遗忘扰动。

结构检查：`python scripts/check_project.py`。
业务检查：`python -m unittest discover -s project/experiments/gpu_model_evidence -p test_protocol.py -v`。
读回：`python project/experiments/gpu_model_evidence/verify.py <run目录> --out <新审计JSON>`。
这些测试不是主线小模型整数参考、端口/RTL或硬件收益实验。

## 尚待对齐

PR26 的 INT8 矩阵/INT32累加建议可以对齐本矩阵 kernel，但整数 M/r、scale编码、KV/递推、卷积/非线性和语言质量合同仍缺失。
FP32 递推/宽整数替代是否可行必须由真实更新输入继续验证；不得将 FP32 状态字节整体除4或把INT8矩阵速度当目标芯片收益。
原始大数据共享存储尚未由项目认可；本地本人目录保留并留 SHA 索引，不能说团队已能访问。用户通知主研究线查看PR并整合；不主动发消息、不自合并、不标done。
