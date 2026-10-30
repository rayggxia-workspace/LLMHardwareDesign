# R311 placement路径诊断

Refs #121 / PR #122。2026-10-29 12:45:45 CST实际捕获8份原始小文件，含311源manifest/queue/dispatch、原生阶段、resizer/detailed-place报告和341状态。最差路径分别product_row[3]/[1]→failed；setup−1.66/−1.49ns。源网表SHA与原单元Q信号映射见index.json/path-source-mapping.json。

仅解析完成阶段的原文件，不修改布局、不新跑EDA、不把中间报告当最终STA。原311继续CTS。针对动态旧状态选择路径的预取修正尚待新源验证，不能继承311或309资格。
