# Issue32 有限真实输入与离线重放

两模型 grouped capture：每个模型 layer0 三个投影，128-token prefill及一次cached token；只取前2行/4输出列，但保存所有K组的A(INT8)、B(INT8)、INT32部分和、FP32激活/权重scale、bias和输出。每个部分和独立用CPU INT64核对，缩放/累加输出也核对。它验证捕获算术，不是整数M/r或RTL证明。

Qwen3.5 state capture：层0/14/30、head0/31；2048/8192末256-token窗口及紧接单步（2049/8193），共12个payload。Q/K/V边界在内部FP32 QK L2归一化及q/sqrt(d)之前、卷积之后；g为log-decay，beta为sigmoid之后；附初末状态和输出。独立CPU FP64顺序重放，避免保存所有层每步大状态。原始计算FP32，大权重FP16存储，无卸载，采集运行不测性能。

随PR数据在 `../gpu_model_evidence/results/issue-32/selected-repair-inputs/` 的gzip中；先解压指定文件。无需权重/GPU的完整复跑命令（仓库根目录；out须不存在）：

```powershell
& D:/Data/llm-gpu32/.venv/Scripts/python.exe -B project/experiments/gpu_state_capture/run.py --replay D:/Data/llm-gpu32/runs/qwen35-long-state-capture-01/long-state-inputs.pt --out D:/Data/llm-gpu32/receipts/long-state-replay-new.json
```

上面命令已用实际采集文件独立执行：12/12通过。原始/打包文件SHA、捕获源码commit和逐文件SHA见每组manifest、artifact-index和package-index。另机可换Python/数据路径，需PyTorch；不执行模型下载。只载入已核验本项目文件，weights_only=True。

主线据此固定给定模块的M/r、舍入和饱和，以及状态更新合同，再验证拆分与RTL。完整模型语言质量不是此前置条件。本GPU任务未验证整数状态更新、全图非线性或目标芯片流量。
