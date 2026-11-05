# P16 / J16 独立 Block 验收与交付

[Issue #187](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/187) · [PR #190](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/190)

| Block | 硬宏与局部 SRAM | 版图尺寸 | 最差 setup | 最差 hold | 独立原生 DRC | 原版完整 GDS DRC |
| --- | --- | --- | --- | --- | --- | --- |
| P16 | M、G、P4 16 KiB | 3100 × 3100 µm | +10.617 ps | +17.720 ps | 0 | 0 |
| J16 | E、T、N4 16 KiB | 2600 × 2600 µm | +81.222 ps | +6.066 ps | 0 | 0 |

两块均采用 Nangate45 M1–M10，TT 1.1 V、25 °C、300 MHz。在同一块的最终物理文件上通过实际寄生和展开电气、PG、M10 端点、逐导体连通、最终 ODB 网表三初态回归以及原版完整 GDS 规则。验收覆盖独立 Block，九实例底座、M11/M12 定制与系统时序属于后续集成范围。

归档位于项目服务器 `$HOME/project-circuit/LLMHardwareDesign/issue-187-p16-j16/144-release-preflight`。每包包括 DEF、GDS、ODB、SPEF、V、SDC，另含 LEF、Liberty、完整规则原始报告、回执和执行源。当前状态为工程验收通过，PR 独立审查待完成。

| 远端相对路径 | 大小（字节） | SHA-256 |
| --- | ---: | --- |
| `P/accepted-p16.tar.gz` | 166288747 | `5f7de8fd080e159f044127f18673cb590137487068fdf6cdfad80a18cb411fab` |
| `J/accepted-j16.tar.gz` | 119968506 | `c6f013868f857e202391a4931b41485f3121fc937ce4705dc75ec02f6782282e` |

两目录中的 `acceptance.json` 绑定各块原件与门限，`archive-list.txt` 是包内索引，`release.sha256` 供交付复核。97695 在 node17 以 2×12 并行核对输入及生成归档，12 秒自然完成。两个目录的 `sha256sum -c release.sha256` 均通过。完整 GDS 规则证据见 [J 145](145-j-full-deck-pass.md) 和 [P 146](146-p-full-deck-pass.md)。