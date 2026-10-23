# Block候选v1的解析记账

Issue41。正式设计见docs/BLOCK_CANDIDATE_V1.md与docs/BLOCK_MINIMAL_EXPERIMENTS_V1.md。
candidate.json是一份声明库存/合同，analyze.py只计算容量、打包和服务下界，**不启动模型/GPU/RTL/远程任务**。
它不产生物理面积、实际周期或最终划分收益。

```powershell
python -B scripts/check_project.py
python -B project/experiments/block_candidate/analyze.py --output D:/Projects/Codex/block-candidate-20261023/analysis-new.json
```

拒绝覆盖已有输出。报告逐文件SHA、源码commit及字节绑定；source_bound=false的准备运行不能当冻结源码证据。
最终解析结果/检查与交付SHA存work/Liangruizhi/41。原模型config复用Issue37固定快照，未读取ref-project。
候选packet64B header与Issue39的8B header不同；不将两个协议的通信数字混用。
E1–E5均是后续计划，本工具通过不代表它们已执行/通过。
