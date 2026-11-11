# Issue247：大容量 SRAM 条件结果与面积预算

负责人 Melodydt；2026-11-10（Asia/Shanghai）。[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)，复用 task/242-r-load-bounds，in_review、未合并。本目录供统一汇总报告第7至9节复核；没有新增 RTL、服务器作业、EDA 或第五轮优化。

## 来源与复核

- `extract_capacity_results.py` 从固定 SHA 的 run04/run05/run09 原始冻结结果提取完整四场景、默认负例、端口占用敏感性与融合参考；输入及源码 commit、工具版本、日志 SHA 均在 `capacity-results.json`。旧 SystemC 3.0.2 / GCC 11.4.0 / Python 3.10.12；本次只用本地 Python 标准库解码复核。共109条完整 trace（57＋30＋22，含重复回放）及6条小 trace，不与之前93条求和作为独立配置数。
- `estimate_capacity_area.py` 锁定8个已提交来源的 SHA，按 Issue200 归档 ODB bank 矩形总面积做条件复制预算。核对快照9925300dc32c18b786bff7a3fe14a2c07ce5746f；`area-summary.json` 含精确数值、公式、宏视图预期 SHA、未知项和额外存储预算。
- `notes.md` / `area-notes.md` 是可读派生表，不替代原结果；没有重新读取服务器原 LEF/ODB，也没有对参考包进行维护。

从仓库根目录复核：

```powershell
python -B -X utf8 work/Melodydt/247/optimization-summary/capacity/extract_capacity_results.py --repo . --output tmp/issue247-capacity-results
python -B -X utf8 work/Melodydt/247/optimization-summary/capacity/estimate_capacity_area.py --repo . --output tmp/issue247-capacity-area
```

主代理与独立子代理分别执行，结果 JSON 逐字节相同，均 exit 0；固定来源 SHA、配置唯一匹配、12项默认回放、policy工作守恒和融合摘要匹配通过。实际本地主复核目录为工作区外层 `work/Melodydt/247/summary-research/capacity-root-verify/`。Python 与脚本 SHA 在各 JSON 内记录。

## 证据边界

性能为历史 S32/S96、300MHz、理想独立64B读＋64B写的条件模型；容量未生产 RTL 化，不能与最新 R4 叠加。4.675512 是已运行 SystemC，4.733478 是固定阶段费用的有限 FIFO 事件回放预测。

面积1.1095446003 / 2.5889374007 / 3.3286338009 mm²只代表2P＋U复制现有1RW bank外框之和，不是 bitcell、真实1R1W、新布局或整芯片面积。bank数量不保证模型端口带宽；q溢价、外围/布线/时序与系统基准面积待测。额外FIFO与部分和预算不跨数值合同相抵。生产参数与服务器状态均未修改。

## 派生结果 SHA-256

- `capacity-results.json`：5f8e2e6b77ccecb96ab3cf8d456922a05d92ca2f9b2c30ac8b953b9824accdbb
- `area-summary.json`：6812b9e5f3d49a782a8b6fd3140585881dff7dffef16e963f219a9853e99b8d4
