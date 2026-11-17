# 算术真实输入标定归档

用途：Issue #280 / PR #281 的公共算术缺项证据；负责人 Melodydt。2026-11-18，Asia/Shanghai。

`index.json` 汇总 27 份已核验服务器结果、262 组真实输入样本：N 66、E32 66、scan 66、apply 36、softmax 16、RoPE 12。它不是整模型功耗报告。`*-calibration.json` 是原始小型回执，`*-results.sha256` 保留服务器原始结果清单；清单中的 sample/receipt 和 build.log 留在原服务器目录，不能直接在本文件夹执行该原始清单。`archive.sha256` 用于核对本地归档全部文件。

每份回执记录输入、RTL/网表/Liberty、工具和日志的版本或 SHA。脚本 commit 见 index 和服务器 immutable bundle 的 source-commit.txt；冻结 RTL 原始 commit 仍待核实，不能用运行脚本 commit 代替。OpenROAD 回报版本 unknown，准确版本待核实；Verilator 5.042，Nangate45 typical。

能耗为等长 active-minus-idle 的动态增量，使用 RTL 边界活动传播到综合网表，不含布线寄生或内部门级回放。名义 300 MHz，系统 SRAM 512 bit；测试的 S128/64-bit 算术口不是系统 SRAM 位宽。scan/apply/softmax 使用理想单 outstanding 访存夹具，不计其存储功耗，不宣称实际 SRAM 等价。样本极值不是置信区间。

apply 已包含其外接 E32；不得再次叠加独立 RMS E32 标定。36 个 apply 样本可在单 bank 放置 X 和 gamma；30 个大向量明确排除，等待跨 bank 或分块部署。七模型 E32/N/scan 全部有实测。softmax/RoPE 当前只验收 Llama/Granite；后继作业 38832101/38832112 等待其余采样成功。

`rms-e32-timing-ledger.json` 对齐七模型 30 个窗口/site 组合的乘积计数：TLM 9 周期/包，当前 RTL 连续无阻塞 18 周期/包。只表示算术资源周期差，不是校正后的 token 延迟。

恢复方法、全部作业、命令和剩余步骤见 [接续记录](../../../../docs/handoffs/2026-11-18-issue-280-public-arithmetic-calibration.md)。模型原 PDF v2.1 小计保持不变，后续完成调用加权、资源去重和驻留积分后更新片上及片上＋DDR 两套结果与 PDF。
