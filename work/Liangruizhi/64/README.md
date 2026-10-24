# Issue64辅助证据

负责人Liangruizhi；[Issue64](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/64)/[PR65](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/65)。正式方案/代码/结果分别在docs/BLOCK_PARTITION_V2.md、project/experiments/block_decisions/、该目录results/issue-64/index.json；不把全部成果塞个人目录。

- *binding*.json：每阶段运行源码commit/逐文件SHA；*submit*.json为实际命令/jobID，failed与retry分列；execution-ledger.log是最终Slurm读回。
- output-independent-original/portable.json及audit_output.py：不导入producer，A最终码/Fraction/动态delta/指标/原Llama匹配及重写SHA负例。便携版本已独立实际执行。receipt-normalization.json保留原Windows文本SHA，Git为LF。
- attention-independent.json：服务器完整56 NPZ重放一轮+另一轮字节一致；34990 score Fraction见证与producer27850概率见证分开。
- attention-selected-independent.json与replay_selected_attention.py：精选两实际NPZ/两LUT本机接收，不冒充全56再次重放。
- service-independent.json与audit_service.py：两轮576/96、3轨迹/端口/credit及4种轨迹变异、3手写负例；不调用producer/scheduler。轨迹无policy字段，按独立统计保留匹配，不认证策略算法。
- archive-intake.json、verify_delivery.py：外SHA/安全成员/56成员SHA/6原Git源；数值接受由上面独立工具完成，不能只看包SHA。
- delivery.json：服务器full/selected大小/成员/SHA；final-receipt-copy.json说明文本LF转换，二进制ZIP完全不改。
- staging-receipt.json：Llama原capture02/numeric04逐原manifest核验后上传；output-repeat.json为A科学文件重复性。
- failures.json：启动器引用127失败、接收器误读policy及服务运行前草稿修正，不删除失败或改生产数据迎合检查。
- validation.json/validation-*.log：本任务实际管理结构、业务/边界、独立精选接收。未跑模型质量/目标RTL/PPA，不把测试数当硬件资格。

临时原文/脚本/接收数据：D:/Projects/Codex/issue64-block-v2-20261024；服务器本人新目录/public/home/yuzelu/RuizhiLiang/issue64-block-v2-20261024。下一步/协作阻塞见docs/handoffs/2026-10-24-issue-64-block-v2.md。登记PR5 pending，看板unverified/同步pending，审查人/管理员待指定。
