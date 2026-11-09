# Issue247：PDF 与新版吞吐证据

关联 [Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247)、[PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)，负责人 Melodydt。

[正式报告](../../../../docs/experiments/issue-247-native-token-throughput.md) · [恢复入口](../../../../docs/handoffs/2026-11-09-issue-247-token-native.md) · [源与命令](../../../../project/experiments/native_token_study/README.md) · [机器索引](index.json)。

每个run保留实际源码commit、Slurm终态、启动命令、工具与输入SHA、全部输出SHA以及筛选原件。超过24KiB的文本保存为可逆`gzip+base64`，索引同时记录原始/存储字节和SHA；未收录的二进制/生成文件按原索引保留在服务器本人目录，不删除原现场。

```bash
python -B work/Melodydt/247/token-throughput/verify.py
```

此验证检查证据完整性及实际冻结功能源；不将条件图模型升级为完整原生RTL、真实权重生成或物理验收。PDF单独保存于正式文档目录，[PDF导出QA](../pdf-export/qa.json)固定原实施文档版本。
