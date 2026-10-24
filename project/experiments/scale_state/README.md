# Issue66：消费者scale与连续整数状态

负责人Liangruizhi，基于PR65@ec3008c。当前执行阶段：独立并行实现/冻结/服务器Slurm，不把计划写为完成。输入只读复用；完整hidden的残差/next norm缺失时，使用现有Qwen3.5权重有界采集，不下载模型。Phi封存，Issue55/63保持独立。

export_legacy_state.py只按原SHA无损导出PR36真实state窗口，不能拼不连续窗口冒充长序列，也不提供conv历史。新capture补完整hidden消费者与连续32步conv/history/gates。整数内核、FP桥、独立reference和条件资源账本分别验收；每阶段binding/commit、输入/成果SHA与Slurm日志保留。具体运行和实际结果待执行后回填。
