# Issue33辅助证据

目标、验收和状态见[Issue33](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/33)。
定向参考源码身份、规范缺口、本机失败/独立审阅与交接保存在本目录；正式工具位于
project/experiments/integer_precision，合同位于docs/。不修改ref-project或其他成员记录。
GitHub身份Liangruizhi / 2663955430@qq.com / 182389313已核验。

本机阶段报告：docs/experiments/issue-33-integer-precision.md；交接：
docs/handoffs/2026-10-23-issue-33-integer-precision.md。正式源码03be2050，结果按各自commit绑定。
manifest.json索引所有原始科学归档成员及日志/报告，`python -B work/Liangruizhi/33/verify_evidence.py --extract`
核所有SHA并安全展开。inputs/results/results-v2原字节在project/experiments/integer_precision/evidence/issue-33-local.zip，
未下载/提交模型权重；只有34个有选择的实际层0数组及小样例/结果。

dev-checks、rtl-dev（首轮语法失败）、rtl-dev02为开发记录；checks/v2/v3/v4和rtl为正式结果。
audit-v4.json为最终审计；audit.json为v3，未包括随后补齐的32KiB状态工作区约束。
初版results/placement.json明确superseded，正式图results-v2/placement-v4.json。
所有数据是本机结果，不是兄方GPU或INT8设备性能；PR待审查，登记/看板缺项见交接。
