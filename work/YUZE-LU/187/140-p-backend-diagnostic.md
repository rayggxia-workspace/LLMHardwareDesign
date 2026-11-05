# 140 · P 同版 GDS 分组预诊断

- 97693 以 2×12 从容器取原版规则，仅调整 FEOL、BEOL、OFFGRID 和 ANTENNA 四个组开关，分别跑 BEOL+OFFGRID 与 ANTENNA。规则原文、两份派生规则与最终 GDS 都写入 `input.sha256`。
- BEOL+OFFGRID 的 97693.0 退出码 0，`beol.lyrdb` 的 96 个类别共 0 个标记。97693.1 单开 ANTENNA 时缺少 FEOL 定义层，KLayout 在 `connect` 退出。该失败产出的空报告不计证据。139 的独立完整天线诊断正常退出且为零。
- 诊断和 97692 的原版完整规则独立，最终以 97692 的完整结果判定。