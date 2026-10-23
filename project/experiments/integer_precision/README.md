# 候选整数参考与量化边界（Issue33）

负责人Liangruizhi；[Issue33](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/33)，
独立task/33-int8-contract，D:/Projects/LLMHardwareDesign-integer；临时目录
D:/Projects/Codex/int8-contract-20261023。本机CPU与适用RTL仿真，不使用服务器/GPU或下载大模型。

先交付[候选精度合同](../../../docs/INTEGER_PRECISION_CONTRACT.md)与
[采集需求](../../../docs/GPU_CAPTURE_CONTRACT.md)，随后补充可执行参考、数据验证器、
小算子/实际捕获、同资源记账与RTL证据。此初稿尚未宣称工具实现或检查通过。
原FP32/BF16结果保留原条件；本候选独立RNE/LUT不是缺失llaccel规范的逐位复现。
