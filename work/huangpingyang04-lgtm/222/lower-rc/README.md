# 原 Qwen3.5：加入上层后，下层参数变化

**计算与独立核验已完成，提交审查；未授予原宏模型直接复用资格。** 沿用已连好的旧 #206 版图，没有重新布线，也没有切换到 #213/#214 的新版底座。

## 通俗结论

大多数下层连线的电容变化很小，但少数靠近上层的线路变化明显，不能统一认为下层参数都可以照搬原值。

本轮覆盖 **2,252,983 条已识别的下层非边界网络**，前后比较全部达到本轮数值精度检查；另 **2,491 条上下连接线**的下层贡献对照也已补齐。

| 下层电容变化的点估计绝对值 | 线路数量 | 占比 |
| --- | ---: | ---: |
| 不超过 1% | 2,247,800 | 99.77% |
| 1%–5% | 3,125 | 0.139% |
| 超过 5% | 2,058 | 0.091% |

主表最大增幅约 **81.9%**，对应 U1 的 cmd_store[0]。独立完整场景复核得到 **9.505 → 17.313 fF，约 +82.2%**，与主表在各自不确定范围内一致。变化最大的10条线路已全部通过独立完整场景检查；已有12条有效全场对照沿用。

这些百分比表示线路金属电容变化，宏的速度还需要用更新参数另外检查。本轮1%指计算精度目标，不是用户已接受的宏误差门槛。主表点估计为0也不代表已经证明影响严格为0。

## 对原宏模型意味着什么

可以保留多数已有成果；变化明显的线路需要更新对应参数，再看实际路径的速度。**不能仅凭多数线路变化小，就认定整个旧宏模型可以直接照用。** 原参数下已有的时序误判独立保留，不全部归因于本轮上下层影响。

原软件参数另外列在表中；判断上层影响时，使用同一套电场设置分别计算加入上层前后，避免把算法或介质口径的差别算作上层影响。原DC电阻段沿用。输出是逐网金属电容对照及数值不确定范围；节点级新RC文件、新宏时序库和更新后的速度检查属于后续步骤。

## 结果入口

- [完整统计](results/final-summary.json)、[全量数值精度和输入索引](results/all-final-summary.json)。2,252,983/2,252,983 达本轮数值门槛，未解决条目0。
- [变化最大20条线路](results/largest-changes.tsv)、[前100条完整记录](results/all-final-largest-increases.json)、[10条独立完整场景复核](results/independent-extremes-summary.json)。
- [2,491条上下连接线对照](results/interface-corrected-interface-comparison.tsv)、[接口摘要](results/interface-corrected-summary.json)、[17条重点接口精细复核](results/interface-surface-checks.json)。分摊是金属电荷投影，不是宏输入电容/延迟；共享M10不能在上下两份里重复相加。
- [服务器中文报告](results/final-README.md)、[交付证据](results/delivery.json)、[大文件位置及SHA](results/artifacts-index.json)。
- [方法、历史尝试及数值范围](METHODS_AND_RUNS.md)、[完整运行与依赖](complete-workflow.json)、[复用与恢复审计](results/reuse-audit.json)。

全量逐网表保留在授权服务器，大小116,419,804字节，不重复上传GitHub：

`/public/home/yuzelu/PingyangHuang/issue-222-lower-all-final-FLQ2O4kz/job-100865-0/result/comparison.tsv.gz`

SHA-256：`d3fbfcdc0bd8c9b61776929763d9c52b86069546031a367a98bb35c837c39c5b`。

## 已有结果如何沿用

原GDS/ODB/SPEF及有效场解保留；2,491条接口的1,295条有效原基线直接沿用，只补1,196条缺项。来源分摊错误修正后，2,491条完整总矩阵与旧有效结果逐行一致。旧来源百分比及依赖它的物理资格结论撤回。

只替换未启动的排队任务，已完成或正在运行的有效场解保留。两项被15分钟回填时限截断后，原样保留12,882条完整结果，仅续算4,504条缺项；输入、全局ID、随机流和数值二进制均保持一致。后续未启动任务恢复完整30分钟时限，相关记录见partial-recovery-dispatch-128-129.json及backfill-pending-minimum-30.json。原始文件未覆盖。

## 适用范围与审查状态

固定 #206 `179ca76ff35673dcb47986e3d873fc2a87dbabbb`、#216 `5f055f6cd1349174ecb71ea55bc48e9acd6a618d`，仅原数据/握手布线范围；父层时钟、复位、控制的补线未纳入。采用既有均匀介质、其他信号静止的金属场比较，不涵盖器件重表征、一般切换/PVT、工艺标定或全库同时误差保证。

Issue #222 提交in_review，PR #225 保持Draft、未合并；负责人/独立审查人待指定。规则[rayggxia-project-collab 1.0.0](../../../../.agents/skills/rayggxia-project-collab/SKILL.md)。登记PR5 pending；缺board配置，Projects unverified/同步pending。结构CI此前两次无步骤失败，原因待确认；本地等价结构检查与实际Slurm数值核验分别记录，不冒称GitHub CI通过。
