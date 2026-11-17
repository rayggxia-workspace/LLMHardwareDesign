# Falcon 扩展采样与系数范围

Issue #280 / PR #281，Melodydt，2026-11-18 Asia/Shanghai。作业 38830193，COMPLETED 0:0，1:14:32，m3cd0608，v6_384，2×12 核、UNLIMITED。源码脚本 commit `67e0d9afb58301a919d8e0fc37ec5650e71839e4`；服务器目录 `R/operator-capture-02/run-38830193`，R 定义见公共算术接续。原冻结基线位置、plan SHA、源文件 SHA 见 provenance/acceptance。

prefill 26 组、decode 48 组，共 74 组算子输入/输出精确复算通过；每阶段记录 147,712 次服务调用。两阶段完整结果和数值文件与冻结基线一致，DDR 终态、SRAM 观察对账通过。服务器 results.sha256 全部核验；本地仅保存小回执，原 operator-observation.json 及其 capture SHA 位于服务器。绑定审计不是 RTL 或模型精度验收。

6 个 conv4 样本每组含 141–144 个超出 S16 Q14 的系数，实际系数约 -14.94 至 16.88；6 个 Mamba 状态样本的 key/query 每组有 27–63 个越界，最大约 12.86。保留 16-bit 有符号存储时，当前卷积样本需最少降到 10 个小数位，key/query 需降到 11 个小数位，才满足当前样本范围。`coefficient-range.json` 逐样本记录未舍入范围、可容纳的小数位和捕获 SHA。

范围检查方法：从 f=14 向下尝试，使用 ties-to-even 的 round(value*2**f)，要求所有量化系数均在 [-32768,32767]。此检查仅诊断范围，没有修改冻结数值或 RTL；改变格式必须同时改变 RTL 乘积右移/舍入、预测/读出流程并复核误差和所有中间溢出。直接降小数位但继续用固定 shift=14 会产生错误结果。扩宽系数是另一候选，需要重新综合标定，不能沿用旧 R 的能耗当成实测。

下一步：根据样本范围明确可配置小数位或扩宽系数合同；复算分阶段定点误差，再做真实 R 指令加载/执行/状态/提交的 RTL 检查和功耗。Softplus/EXP/norm-gate 仍未绑定。公共 softmax/RoPE 已在 38832101/38832112 的输入中，等待其他三模型采样成功后运行。

`archive.sha256` 只核验本地小归档；原 `results.sha256` 需在服务器原目录执行。此采样不改变整模型能耗/PDF 小计。
