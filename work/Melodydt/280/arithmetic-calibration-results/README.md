# 算术真实输入标定归档

Issue #280 / PR #281；Melodydt；2026-11-18 Asia/Shanghai。

当前入口为 `v3-evidence-index.json`：七模型 N/E32/scan 各 66 个样本；66 个完整 RMS apply 向量由 96 个合法分块覆盖，零容量排除；softmax 56、RoPE 54。旧 36 个 apply 回执保留，但不重复加入 v3。`index.json` 是此前 27 份/262 样本的历史快照，不代表当前覆盖。

`*-calibration.json` 是服务器原始小型回执，`*-results.sha256` 是原始服务器清单（其 sample/receipt、build.log 留在服务器）；`archive.sha256` 校验本地归档。新结果 38837942、38838116、38838117 和其余模型后继 38832101/38832112 全部 COMPLETED 0:0，结果 SHA 已核验。

名义 300 MHz，系统 SRAM 512 bit。S128/64-bit 算术接口不是系统 SRAM 位宽；理想 one-outstanding 访存夹具不含 SRAM 功耗。采用 RTL 边界 VCD 传播到 Nangate45 typical 综合网表、等长 active-minus-idle，不加载布线寄生，不是内部门级活动回放。Verilator 5.042；OpenROAD 精确版本 unknown，冻结 RTL 原始 commit 待核实，源文件与 Liberty SHA 已记录。

apply 与 RoPE 包含外接 E32，不能再次相加。大向量保留完整向量因子，仅拆分 apply；分块 staging/实际实例驻留单列敏感性。E32 18 周期/包与 TLM 9 周期的差异保留于 timing ledger，未据此修改冻结 token 时间。

v3 已按真实调用计数积分，并以明确成本代理补特殊算术；PDF 分别报告片上和片上＋DDR。代理范围不是置信区间或保证误差界。方法见上级 ARITHMETIC_ESTIMATION_METHOD.md，完整接续见 docs/handoffs/2026-11-18-issue-280-arithmetic-estimate-v3.md。
