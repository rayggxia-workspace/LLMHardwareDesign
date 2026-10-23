# 候选整数参考与量化边界（Issue33）

负责人Liangruizhi；[Issue33](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/33)，
独立task/33-int8-contract，D:/Projects/LLMHardwareDesign-integer；临时目录
D:/Projects/Codex/int8-contract-20261023。本机CPU与适用RTL仿真，不使用服务器/GPU或下载大模型。

[候选精度合同](../../../docs/INTEGER_PRECISION_CONTRACT.md)与
[采集需求](../../../docs/GPU_CAPTURE_CONTRACT.md)已先行发布到[PR34](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/34)。
工具包括fixed/reference/vectors、capture严格接收器、层0捕获、数值比较、
quantized graph记账和独立串行RQ RTL。每次运行的source_dirty与commit/SHA独立记录。
原FP32/BF16结果保留原条件；本候选独立RNE/LUT不是缺失llaccel规范的逐位复现。

## 本机复现

先运行`python -B work/Liangruizhi/33/verify_evidence.py --extract`。原始科学payload按原字节压缩在
`evidence/issue-33-local.zip`，索引在work/Liangruizhi/33/manifest.json；raw目录被gitignore，
只通过归档交付，避免大段JSON差异。验证器拒绝覆盖已修改的本地副本。

从项目根目录执行；全局Python需要NumPy/jsonschema，已有Qwen虚拟环境需torch2.10.0+cpu、
transformers4.57.6。无安装/下载/其他机器步骤。TEMP/TMP及缓存指向任务D盘目录。

```powershell
$env:TEMP='D:/Projects/Codex/int8-contract-20261023/process-temp'
$env:TMP=$env:TEMP
D:/APP/Python/python.exe -B project/experiments/integer_precision/run_checks.py --output D:/Projects/Codex/int8-contract-20261023/recheck
D:/Projects/Codex/qwen3-inference-20261022/environment/.venv/Scripts/python.exe -B project/experiments/integer_precision/capture_qwen3.py --weights D:/Projects/Codex/qwen3-inference-20261022/environment/weights --output D:/Projects/Codex/int8-contract-20261023/recapture
D:/APP/Python/python.exe -B project/experiments/integer_precision/run_numeric.py --inputs project/experiments/integer_precision/inputs --output D:/Projects/Codex/int8-contract-20261023/renumeric
D:/APP/Python/python.exe -B project/experiments/integer_precision/capture.py project/experiments/integer_precision/results-v2/capture-example --replay-linear
D:/APP/Python/python.exe -B project/experiments/integer_precision/placement.py --output D:/Projects/Codex/int8-contract-20261023/replacement.json
D:/APP/Python/python.exe -B project/experiments/integer_precision/run_rtl.py --work D:/Projects/Codex/int8-contract-20261023/rtl-replay --output D:/Projects/Codex/int8-contract-20261023/rtl-replay-results
```

placement是受控混合算子fixture：32行、N16/K1024，四K片；INT32驻留/跨Block、RQ近端/共享、
两64KiB bank、一个RQ、一个矩阵、一个向量、一个64B/cycle半双工链路、2KiB边界buffer。
另有两方案相同的32KiB私有状态工作区，1R1W、每端口64B/cycle为假设；整状态暂存不能免费。
每token宽状态更新不随tile行数免费减少；INT16和INT32状态分开比较。bank非抢占burst，
2RW单burst同时用两端口，与1R1W的方向并行区别明示。矩阵/向量服务是假设，
RQ26延迟/28启动间隔由本机RTL验证；无芯片性能、时序/PPA或模型质量外推。
CPU实际运行秒数也不是INT8硬件加速证据。

重捕获是可选步骤；数值重放可直接读取已提交inputs。正式图使用results-v2/placement-v4.json；
初版results/placement.json漏计私有状态工作区，仅保留为被取代的探索，不能用于完整有限缓冲结论。
细化命令：`python -B project/experiments/integer_precision/refine_numeric.py --inputs project/experiments/integer_precision/inputs --output D:/Projects/Codex/int8-contract-20261023/refinement-replay.json`。
最终审计：`python -B project/experiments/integer_precision/audit_results.py --output D:/Projects/Codex/int8-contract-20261023/audit-replay.json`。
详细结果和每轮源码绑定见docs/experiments/issue-33-integer-precision.md，原始证据及SHA见work/Liangruizhi/33/manifest.json。
