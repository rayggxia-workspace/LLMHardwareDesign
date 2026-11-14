# Melodydt 的进度

## 2026-11-14（Asia/Shanghai）Qwen2.5-3B ATT1 存储流水

- [Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) 由 Melodydt 在 [task/270-qwen-rtl-throughput](https://github.com/rayggxia-workspace/LLMHardwareDesign/tree/task/270-qwen-rtl-throughput) 推进，通过 [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272) 交付，叠加在 [PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260) 的 `55620f17`。首轮实现 AV 每行只取所需 V beat，并减少 RTL 的逐行控制交接。
- C380 Verilator 原生对照 112602/112603 均完成 0:0。两模式数值与参考逐字相符，KV 回包 15,200→9,120，正常/背压周期分别下降 28.13%/14.94%。项目管理检查通过，300 MHz 物理验收未执行。
- 512-bit 基础流水下，前四层外推两步 Decode 2.455394 tok/s，短 Prefill 5.507167 输入 tok/s。112559/112560 仍在 `/public/home/yuzelu/Melodydt/runs/issue-270/att1-selected-01/tlm` 保存全过程。下一步读回完整审计和散列，对照预测误差，随后做 ATT1 回填/读出流水。复现及追踪见 [#270 ATT1 回执](../../work/Melodydt/270/README.md)。
- 任务处于进行中，独立审查人待指定。项目登记 PR #5 待合并，Projects 配置缺失，条目和同步待具权限维护者核验。

## 2026-11-14（Asia/Shanghai）ATT1 回包与 S 写确认解耦

- [Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) / [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)。C380 同流量原生回归 112668/112669 均完成 0:0，正常 163,454→85,495 拍，背压 371,268→271,308 拍，读回逐字匹配。
- 512-bit 两步 Decode、短 Prefill 前四层外推为 2.455394664 tok/s 和 5.507166863 输入 tok/s，上一轮基线外推 2.455393940 / 5.507166863。112637、112638 在 `/public/home/yuzelu/Melodydt/runs/issue-270/att1-response-02/tlm` 持久运行。恢复与原始散列见 [第二轮回执](../../work/Melodydt/270/response-02/README.md)。
- Melodydt 后续读回四个作业终态及输出散列，再评估同流量的多回填窗口和共享 S 读出。物理 STA/完整 P512/D128 未执行。独立审查人待指定，登记 PR #5 待合并，Projects 待具权限维护者核验。

## 2026-11-14（Asia/Shanghai）ATT1 SRAM 多块回填

- [Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) / [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)。上两轮 582/578 页完整对账，回包解耦轮 2.455286 tok/s / 5.502012 输入 tok/s。
- C380 原生 A/B 112990/112991 数值与流量一致，正常 85,495→67,242 拍、背压 271,308 拍持平。113009 正常及两个错误标签排空用例通过。多块回填前四层外推 2.609134 tok/s / 5.502848 输入 tok/s。
- 112976/112977 在 `/public/home/yuzelu/Melodydt/runs/issue-270/att1-refill-03/tlm-final` 持久运行。Melodydt 后续核对完整吞吐，再测共享 S 读写重叠。复现与散列见 [第三轮回执](../../work/Melodydt/270/refill-03/README.md)。登记 PR #5 待合并，看板待核验，物理时序未执行。

## 2026-11-14（Asia/Shanghai）ATT1 双窗口回填与 Dot 读出

- [Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) / [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)。C380 固定半窗口 A/B 113104/113105 均完成，正常 75,877→65,932 拍、背压 282,528→279,968 拍。同流量及逐字读回通过。相对第三轮大分片，正常减少 1.95%，背压增加 3.19%。
- 512-bit TLM 同流量前四层外推 2.739536 tok/s / 5.504623 输入 tok/s。112976/112977 及 113070/113071 持久运行，恢复见 [第四轮回执](../../work/Melodydt/270/dot-read-04/README.md)。Melodydt 对账完整短程吞吐和误差后衔接 FFN 权重取数。新增共享端口故障注入、物理 STA 和 P512/D128 待执行。
- 登记 PR #5 待合并，Projects 无配置，具权限维护者待核验和同步，独立审查人待指定。

## 2026-11-14（Asia/Shanghai）FFN 权重供数

- [Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) / [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272) 由 Melodydt 接续。本轮在冻结 ATT1 的 512-bit 方案上做 FFN 四权重 bank A/B。前四层同程序、同流量及 Down 散列对照通过。两步 Decode 外推 2.931091 tok/s，短 Prefill 外推 6.327444 输入 tok/s，后者按 113071 的完整 ATT1 5.511216 输入 tok/s 重定基。
- TLM 113164–113167 持久运行，原生归档 DDR 113181 完成 0:0，回包 2,245,632、在途峰值 63。原生 C639 三路 P 监测 113199 已进入回放，113195 的归档入口失败已修复。下一步根据原生每个 M bank 的填充与 EXEC 边沿定位 Gate/Up 尾延迟，并对账四项完整同比。见 [第五轮回执](../../work/Melodydt/270/ffn-weight-05/README.md) 和 [恢复交接](../../docs/handoffs/2026-11-14-issue-270-ffn-weight.md)。
- 完整 P512/D128 与物理 STA 未执行，任务进行中，独立审查人待指定。登记 PR #5 待合并，Projects 缺配置待具权限维护者核验和同步。

## 2026-11-14（Asia/Shanghai）FFN 三路 P 与母控 WAIT 对账

- [Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) / [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)。113287 原生 C639 两模式完成 0:0，各 128 波次/384 scope，源、输出与探针散列核验，与 113199 的功能级回执和 DDR 事务逐字相同。正常/背压 Gate/Up 最慢一路的配对准备平均 1,204/1,043 拍，单独等权重 268/105 拍。优先做局控可执行老记录与后续配对准备解耦的单项 A/B。
- ATT1 第四轮完整基线 2.739056 tok/s / 5.511216 输入 tok/s。短 Prefill 113166/113167 完整为 6.316164 输入 tok/s，逐页与 Down 通过。FFN Decode 第二步前四层外推 2.926561 tok/s，完整 113164/113165 对账为 2.925996 tok/s（+6.82%），582 页和 72 个 Down 散列一致。保留词表 86.827619 ms 的基线页时间。
- 后续逐步汇报两项速度、验证限制和剩余全部步骤。详见 [第六轮回执](../../work/Melodydt/270/ffn-wait-06/README.md) 和 [恢复交接](../../docs/handoffs/2026-11-14-issue-270-ffn-wait.md)。审查人待指定，登记 PR #5 待合并，Projects 缺配置待具权限维护者核验。物理 STA 与 P512/D128 未执行。

## 2026-11-14（Asia/Shanghai）FFN EXEC 提前发出消融

- [Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) / [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)。单变量局控候选通过 54 项定向回归，C639 113742 完成 0:0。Gate/Up 和 Down 的两模式 WAIT 总周期增约 11%。提前发出先吃掉了年轻权重的重叠时间。
- 当前完整短程 TLM 基线为 Decode 2.925996 tok/s、短 Prefill 6.316164 输入 tok/s。该候选依据正常、背压 C639 和前四层窗口的敏感性分别为 2.840833/5.931992 和 2.838812/5.923231。疑似退化候选暂不进入速度基线。
- 113850 正常和背压均完成 0:0，前序一致，Gate/Up 增 11.06%/11.20%、Down 增 10.96%/11.54%。提前执行候选淘汰。当前保留基线的 HEAD16 为 86.828 ms，占第二步 25.41%。下一步进行词表细分。恢复见 [交接](../../docs/handoffs/2026-11-14-issue-270-ffn-exec.md)。后续每步报告当前两项速度和剩余全部步骤。STA、正式 P512/D128 未执行；独立审查人待指定，登记 PR #5 待合并，Projects 待具权限维护者核验。

## 2026-11-14（Asia/Shanghai）HEAD16 词表阶段拆分

- [#270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) / [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)。原生权重配对完整背压对照 14,109,900 周期持平。原生读回应答同拍发下一请求，正常读回每 tile 97→66 周期、整表仅省 22 周期，背压省 0 周期。全部 logits、embedding、选中 token、DDR 数和 SRAM 索引核验通过。两个 RTL 实验均关闭，归档失败与独立修复见 [实验报告](../../work/Melodydt/270/head16-08/README.md)。
- 最近完整速度 Decode 2.925996 tok/s，短 Prefill 6.316164 输入 tok/s。前四层逐页相同。48-tile TLM WeightFetch 抽样外推 Decode 2.933969 tok/s，短 Prefill 端点在 HEAD16 之前。114107/114108/114109 持久运行，启动及对账见 [交接](../../docs/handoffs/2026-11-14-issue-270-head16.md)。
- Melodydt 读回完整两步/短 Prefill，再定位 HEAD16 激活/局控及 QKV/O 的关键路径，补 ATT1 故障与分片验收后执行组合 300 MHz STA 和 #234 正式 B1/P512/D128。独立审查人待指定，登记 PR #5 待合并，Projects 缺配置待具权限维护者核验。
