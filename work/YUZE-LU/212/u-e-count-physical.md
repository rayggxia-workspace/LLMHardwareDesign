# 修复版 U 的物理重验收

任务：[Issue #212](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/212) · [PR #214](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/214)。负责人 YUZE-LU。日期 2026-11-07 CST。

当前状态（2026-11-07 13:03 CST）：修复版 U 已通过物理工程验收，完整原版 GDS DRC 为 0；交付包已回收并逐项核验。独立 PR 审查与合并另行完成。

## 实现与溯源

功能修复为 `33821f73c601ddec81a53264b8c62008fc665aff`，对应本地 `90d7ace4dd837c84e033dd63de524e8af174d558`，两者 tree 均为 `a106560ce0923d83a052dfbccea7f797854ae46f`。物理构建的全部 11 份硬件源文件经 CRLF/LF 归一后逐项与该提交核对一致，原始字节另由源码归档哈希绑定。

服务器任务根目录：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-212-pu-leaf-base`。本轮物理源码为 `smoke-i9tfJN/source.tar.gz`，SHA-256 为 `e0be9041b6cb63f52617623889d6fa0ff4e683e699f50e51e44b7653ed5976d6`。三初态程序回放源码为 `smoke-ngC12q/source.tar.gz`，SHA-256 为 `a0cf71d9b47dfa133b2f8fd29b805cca77291f691739f88ae4e89a6e9bbf33c2`。

最终候选为 `smoke-i9tfJN/resume-99465`。构建链为 `result-45 → resume-99424 → resume-99443 → resume-99465`，均从本轮修复 RTL 的综合、布局和时钟树出发，没有使用旧 U 的物理检查点。N、紧凑 E、16 KiB S_base 三颗叶宏的版图和 Liberty 不变。局控、服务适配器、仲裁、时钟树和修复缓冲均纳入父层实现。

样片范围为 1034 × 1214 µm；S 位于 (48,48)，E 位于 (48,656)，N 位于 (476,656)，均为 R0，坐标单位 µm。该范围用于局部接入试验，三个叶宏保持独立实例，不导出一个新的组合硬宏。

## 物理修复过程

- 初始 99404_45/47 的默认优化在少数端点反复插入缓冲，停止这两个分支，保留其新设计 CTS 检查点。
- 99424/99425 比较路由设置。选择紧凑候选 99424；其原生提取 setup +341.457 ps、hold −19.760 ps，按真实接收端点补延迟，得到 99443。
- 99443 的原生时序转正，但上层检查发现 `incoming_data[105] → _68640_/D` 的 hold 为 −43.366 ps。按上层实际报告，为 `_68640_/D`、`_68576_/D`、`datapath.normalize/cmd_data[29]`、`_68537_/D` 四个端点补延迟，得到 99465。
- 修改的是实际 BUF 单元和布线。最终判定保留原 Liberty、电气上限、3.333333333333 ns 时钟、100 ps 不确定度及原输入输出约束。优化过程的停止裕量不替代验收约束；未通过新增 false path 或放宽频率解决违规。

## 最终验证

| 项目 | 结果与证据 |
| --- | --- |
| Nangate45 M1–M10，TT 300 MHz 原生提取 | setup +334.870 ps，hold +3.787 ps；99466 的 `audit-native.log` |
| 电气、信号与供电 | 独立 max slew/cap/fanout、完整信号路由及 VDD/VSS 连通检查通过 |
| 定向几何诊断 | M9/M10、VIA7/VIA9 间距及 WELL 原规则子集 0；只用于诊断，不代替完整 DRC |
| 完整原版 GDS DRC | 99466 完成，违规数 0；使用未经修改的 `FreePDK45.lydrc`，无规则豁免，独立 `check_native.py` 判定通过 |
| 代表 M11/M12 接入 | 130 根实际 M10 端点绑定的 8 µm 连接，逐网 GDS 回读、隔离和接入几何检查通过 |
| 上层 low/base/high RC | 三档均 setup +340.956 ps、hold +3.787 ps；130 根均标注寄生，每档报告 20 条穿越上层的时序路径，电气通过 |
| 正常程序最终网表 | 99467_3；正常、背压、故障、背压伴故障、复位，各三种初态，共 15 次通过 |
| 两操作数 FMA 最终网表 | 99468_3；同五场景、三初态，共 15 次通过；S[0]=5，A=2，B=3，正确写回并传输结果 6 |

最终网表回归分别位于 `gate-e-final-normal-X96Zy9/fixture-3` 和 `gate-e-final-fma-u76GdI/fixture-3`。两者均核对最终 `6_final.v` 的 SHA-256，使用真实 SRAM bank 和原叶宏功能模型。对端 C 使用 #195 参考实现，本次不构成 C 的物理验收。功能网表仿真未回标 SDF；时序由对应最终 ODB/SPEF 的独立 STA 判定。三初态为 `1:143`、`2:143`、`2:144`，编译启用 `--x-initial unique --x-assign unique`。

验收范围是本地 U 接入样片及上述研究上层 RC 连接；不扩展为九实例共同底座、产品级长线、其他 PVT 或整模型系统验收。P 的既有工程包不变。布局布线、最终回归和物理检查每作业 10 核；归档使用 2 核。

共享回放脚本的 P 兼容性另由 99526_2 检查：使用既有合格 P 的最终网表，原母局控程序在三种初态全部通过。目录为 `gate-p-replay-check-2vY7k0/fixture-2`；该检查不替换 P 的物理交付包。

## 交付归档

最终服务器目录为 `receipt-e-qualified-vatxlG`，打包作业 99527 完成。打包前重新校验完整原生回执、最终网表哈希、30 次程序测试、上层几何和三档 RC。原六文件、各叶宏时序/几何视图、完整规则原文及报告、功能测试、物理修复链和两份执行源码归档均纳入包内。

文件：`u-e-fixed-accepted.tar.gz`，105842083 字节。SHA-256：`a1f35c0d6910bd006b8be8ef15bda563eb5ddc1c82312afab207e1bcf6ae2f3a`。

本机回收目录：`C:\Users\wine10\AppData\Local\Codex\issue-212-u-e-qualified-vatxlG`。归档整体哈希和包内 82 个文件的 SHA-256 全部一致，本地再次解析完整 DRC 报告确认 0 条，并重新核对 30 次最终网表测试通过。核验回执为该目录的 `local-verification.json`。本次新包取代旧 U 包的当前交付地位，旧包保留作历史溯源。
