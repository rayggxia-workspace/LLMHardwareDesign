# Issue98：完整电气上限检查，不能把工具过滤容差当设计裕量

Issue: https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/98 。负责人 Liangruizhi。

93 `detail9302` 的实际详细布线 RCX 与 97 `caprepair9702` 的 GRT 完整电容表各有 20 个非时钟内部 driver 的 actual cap > max cap。此前 `-violators` 表分别仅列 7、3 个。这些旧表和失败保留，不能据其“零条”结论宣称严格 maxcap 闭合。

精确安装 OpenSTA commit `83e1f9b77f35a953dbd3c01dba431a789a981803` 的 `search/CheckCapacitances.cc` 在 `violators` 过滤时调用 `fuzzyLess(slack, 0)`，`util/Fuzzy.cc` 对零采用 1e-15 的绝对比较容差。电容内部 SI 单位为 F，等于 1 fF；因此低于 1 fF 的负电容 slack 可以不进入摘要。完整非过滤表仍会显示这些行的 `VIOLATED`。

已核官方 Git blob：CheckCapacitances.cc `c084ca8c33e99dc5e9b23b03d1fd70d90b97a7ba`，SHA-256 `a76f048d489b6dcf0465b7c1a7bfe06c34c5bab300c97c350ad09b69a5236693`；Fuzzy.cc `bd055f1d6ed98e858537313e164f8f4750bcb46a`，SHA-256 `c3a6583aadf183091e7ae8bbcae213cf23686c8c2e8795ca35ee7530701d1e76`。这是同版本工具行为解释，不是修改工具或放宽器件限制。

决策：最终接收除原始 native counts 和全 setup/hold endpoints 外，必须读取不加 `-violators` 的完整 max slew/cap/fanout 表，使用有限数值的 actual > limit 逐行判断，保留真实完整报告与 SHA。报告最多 1,000,000 行，实际必须严格小于上限；无 fanout 约束必须明确为无约束，不编造约束通过。cap driver 覆盖与 Liberty 定义另由完整 driver 清单核验。独立检查仍受工具计算模型和输出精度限制，不声称独立物理求解。

冻结修复须以真实全部接近上限的网清单设计一次有界候选，保留所有端口、原 10 ns/min0 和面积预算，计价新增 buffer/输入负载/真实重布线，不能按摘要逐条追补。当前只读阈值 0.75/0.80/0.85/0.90 的数量与成本已完成；新候选尚待根任务统一冻结，不因本文件自动启动。
