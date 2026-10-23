# Issue32 实际INT8分组部分和

捕获格式、边界和离线状态重放见[共同说明](../gpu_state_capture/README.md)。

GPU采集完整命令（干净源码、新输出目录）：

```powershell
& D:/Data/llm-gpu32/.venv/Scripts/python.exe -B project/experiments/gpu_grouped_capture/run.py --model-dir D:/Data/llm-gpu32/models/qwen25 --out D:/Data/llm-gpu32/runs/qwen25-group128-capture-reproduce --group-k 128
```

Qwen3.5使用其model-dir和group-k32；未做额外语言质量测试。源码/模型SHA先核验，失败不覆盖。
