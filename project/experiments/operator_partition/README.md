# 算子/Block边界首轮研究

Issue21；研究问题与方法见仓库docs/RESEARCH_QUESTION.md和docs/OPERATOR_BLOCK_PARTITION.md。

## 可重跑内容

Python 3.11+、NumPy；本轮使用Python3.13.14/NumPy2.5.0。核心计数器为标准库；数值核需要NumPy。运行前固定源码commit且git status清洁。输出必须新建目录，不覆盖旧尝试。Windows缓存与临时输出放D盘本任务目录，进程级设置，例如：

```powershell
$env:PYTHONPYCACHEPREFIX='D:/Projects/Codex/operator-partition-20261022/pycache'
python scripts/check_project.py
python -m unittest discover -s project/experiments/operator_partition -p 'test_*.py' -v
python project/experiments/operator_partition/run.py --out D:/Projects/Codex/operator-partition-20261022/run-01
```

experiment.json是预声明资源/维度/裕量合同，model-cases.json的派生维度与固定官方原始输入逐字段核验。输入SHA、自洽事件重放、独立闭式MAC/传输公式、配对资源和source起止hash/HEAD/status都检查。输出rows.json、capacity.json、events.jsonl、pareto.json、numerical.json、summary.json、manifest.json和确定性ZIP。正式归档进入results/，失败和辅助审计进入work/Liangruizhi/21/。

## 解释边界

- 本轮是FP32逻辑张量字节/生命周期账本和缩小数学子图；不是cycle/RTL/物理仿真、真实权重模型推理或实测SRAM峰值。
- 同一对固定banks/engines；split/joined仅改变归属，不增加容量、端口、重叠或免费传输。joined的cross_block=0是重分类，局部interengine数据仍在。
- token tile减小需要重读权重；attention online消除完整score常驻，却增加tile O返回vector的传输。物化也允许声明粒度的分包，不从copy调用大小直接推物理峰值/pin。
- 对外KV状态单独计容量；attention核不含QKV投影、RoPE、norm、FFN，Qwen3.5仅全注意力核而非全部混合层；DeepSeek-V3 FFN是单个dense层/单专家，不代表完整MoE。
- Pareto只比较已枚举调度的资源向量，不声称制造前Block最优；容量失败只否定具体调度和容量点。
- 正式数值核378个配置对照和3个错误负例，支持FP64/FP32；无模型权重、数据集、输出质量或硬件速度结论。独立DeepSeek/Qwen/Llama辅助证据和来源限制另列。
