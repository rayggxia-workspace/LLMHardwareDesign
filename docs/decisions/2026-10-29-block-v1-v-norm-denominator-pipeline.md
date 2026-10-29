# V：归一化分母流水

Issue #121 / PR #122；2026-10-29。仍只有 M/V/R/S/T 各一个基础实现。

316 的实际 global-place 和 resizer 报告共同给出 cmd_data[13] 到 `$auto$ff.cc:337:slice$599370` 的 setup 约 −1.75 ns；网表 Q 对应 `group_unit.denominator[79]`，即顶层 group_d。输入含 epsilon 与统计计数乘法及平方和相加。报告是 ideal-clock/placement-RC 中间诊断，不能代表最终 STA；316 继续正常运行，未取消。

将本地和全组 RMSNorm/L2Norm 的分母生成统一拆成：已寄存 epsilon/count → U64×U16 的完整 U80 乘积 → 与已寄存平方和做 U128 grouped add → 原组级单元。统计数最大65535，本地长度最大256，完整乘积严格小于2^80，没有截掉有效位。新增 norm_count16、norm_product80、norm_square128，共224个载荷位；相位27/28复用既有5位phase。载荷在控制相位保证先写后读，无新增复位依赖。add128_grouped/rne 函数不变；整宏仍需新源验证和全新布局布线。

RMSNorm/L2Norm 相对315增加两拍；逐元素、统计、函数、TopK、外部 reciprocal/rsqrt及Softmax控制顺序不改。不能以旧315/319周期代表新归一化延迟，后续必须重测有限S/V工作空间和预算。旧完整函数数学证明只覆盖字节相同函数，不授予新整宏资格。

新增组合边界测试：最终统计数65535、epsilon=2^64−1；本地256个INT32_MIN、epsilon为0/1/2^64−1，两种norm均对独立U128参考校验，共8例。保留原320 RoPE、65535统计元素、非法命令拒绝与三初态验证。321拟执行六个独立16CPU任务，尚未执行/通过；物理候选仍316，最终317/318不因本决定获得资格。

真实中间报告、端点映射、输入网表SHA及捕获时间见 `work/YUZE-LU/121/review-20261028/v-global-316-0826/index.json`。目录名称不是实验时间；实际捕获2026-10-29T00:24:52.740516+00:00。
