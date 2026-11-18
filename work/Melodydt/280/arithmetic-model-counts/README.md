# 算术调用数与形状

Issue #280 / PR #281；Melodydt。用于 v3 运算级估算，原始大向量保留在服务器。

`collect_model_arithmetic_counts.py` 先核验采样结果清单及 operator-capture-check 的输入 SHA，再导出全部调用签名、实际服务次数、样本形状和 RMS 计数。每个签名必须存在形状样本，同签名样本形状必须一致；RMS N 计数必须守恒。原回放的冻结数值/时间、DDR/SRAM 对账随其 acceptance 回执验收。

每模型 JSON 记录服务器目录、结果清单 SHA、原 operator/arithmetic 输入位置及 SHA。prefill 字段对应短 Prefill，decode 字段同时含 first_token 和 decode 两个窗口，积分时必须按签名前缀区分，不能把两个 decode token 的调用数都加到第 2 步。

这些是观察计数，不是新的 RTL 或 FP32 验收；特殊算子成本规则见上级 ARITHMETIC_ESTIMATION_METHOD.md。原始状态/权重/向量不在这个小型 Git 归档内。
