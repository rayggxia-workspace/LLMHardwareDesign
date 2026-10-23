# Issue37静态架构筛查记录（不是神经推理实验）

2026-10-23，Liangruizhi。源代码946281b9a90dd36b130e691c60667b9f7d1e4d32，干净源码。
正式论证在[全候选架构审查](../MODEL_ARCHITECTURE_REVIEW.md)。

| 实际步骤 | 输入/范围 | 观察 |
| --- | --- | --- |
| 公开模型元数据/配置 | 17个变体，固定官方revision/URL；原字节SHA在catalog | 12份config取得，Gemma/Meta5份HTTP401；没有权重/许可绕过 |
| 本地已安装框架静态审读 | Transformers4.57.6 Qwen2/Gemma3/Phi3 | Qwen2 QKV bias；Gemma有效gamma/默认窗口与论文不同；Phi融合投影/部分旋转；框架文件SHA在framework-evidence.json |
| 管理/协议检查 | scripts/check_project.py；test_catalog.py；git diff --check | 结构、8协议测试、whitespace通过；raw log及SHA在checks/ |
| 架构覆盖与容量公式 | catalog17行，plan拟议要求；不构造模型 | 最小声明覆盖选gemma4/qwen25/qwen35，追加工作优先成本1；仍含门控条件，不是可立即启动标志 |
| 独立版本绑定 | screen.source_sha256与Git commit原字节，checks原始日志 | 17源绑定、3日志SHA通过，audit.json |

来源/配置/脚本/结果/日志SHA逐文件记录在work/Liangruizhi/37/manifest.json。
恢复命令见project/experiments/model_selection/README.md；本轮结果没有第三方依赖。
源码文件和配置均经实际Git原字节关联，外部框架仅记录安装版本与文件摘要，未冒充目标checkpoint逐位复现。

用户追加架构先行后，没有执行原拟小型模型数值微测、没有GPU任务或大权重下载。
小模型KV反例、Qwen3.5候选状态48MiB等都是明确公式与格式/布局假设；没有将它们作为实际分配或端到端收益。
正式实验必须通过接入/正确性/量化质量/同资源划分与物理可行性门槛；本报告不保证所选模型已验证没问题。
