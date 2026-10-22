# Issue #7 并发实验阶段总结与验收边界

- 核验日期：2026-10-22，中国标准时间（UTC+08:00）。Refs [Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)，沿用[草稿PR #10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)。
- 结论：**原并发批次可进行阶段性实验总结和送审；通过列出工具预算的候选可进入宏资格检查。完整硬宏、系统和H2预制底座仍不可验收。** 失败结果也是本阶段交付的一部分，不要求把所有参数点改成成功。
- 本页只维护并行工作线的结果。主线PR #8、VECTOR／PG、工作树及89448形式验证作业均未修改。

## 完成度和结果

第二轮基线物理流程7/7结束；另外2次定向接续完成最终布线、提取与宏视图导出，合计9份可审读的终态物理结果。严格工具预算通过4份、未通过5份。该计数不包含此前3次名称／生成器校验失败；其非零退出和冻结产物继续保留，不能把它们改写为完成布线。

| 对象 | 终态电容计数 | 最差电容余量 fF | 本次工具预算 | 阶段处理 |
| --- | ---: | ---: | --- | --- |
| ACT／0 | 2 | −2.653673 | 未通过 | 保留基线 |
| ACT／10 | 0 | −0.776201 | 未通过 | 保留零计数负余量反例 |
| ACT／20 | 0 | +2.441659 | 通过 | 余量较充足的ACT候选 |
| GEMM／10 | 8 | −5.769668 | 未通过 | 保留失败，不重复运行 |
| GEMM／20 | 0 | +0.221413 | 通过 | GEMM候选，余量较小 |
| MXU／20 | 0 | +0.842449 | 通过 | MXU候选 |
| ACT＋MXU／20 | 4 | −6.343030 | 未通过 | 保留合并基线 |
| ACT／10定向修复 | 0 | +1.218952 | 通过 | 较小面积的ACT备选 |
| 合并／20定向接续 | 4 | −5.886479 | 未通过 | 四处升级不足以全块收敛 |

上述9份结果均DRC／天线0、setup／hold TNS0、slew／fanout计数0；是否通过仍逐路结合最差电容余量判断。ACT定向修复仅MUX2_X1→X2，面积约+0.5µm²；最终540,904字节Verilog在唯一型号替换后全文一致，两个型号的Liberty逻辑签名相同。独立审计已经核对相应源和输出manifest。详细物理指标、容差原因与失败历史见[定向修复记录](issue-7-parallel-blocks-repair.md)。

[轻量验收索引](../../project/experiments/parallel_blocks/results/parallel-blocks-acceptance-20261022.json)从11／12／15／16的冻结终态派生，先逐份核对预期SHA，再汇总各路门槛与来源。只对已核验记录做派生摘要，不覆盖历史终态或其当时的单位说明。

## 可以验收什么

| 验收内容 | 当前证据 | 判断 |
| --- | --- | --- |
| 实验可追溯、独立保存、结束状态明确 | 固定RTL／镜像／runner、检查点及输出manifest，独立终态审计 | 可阶段验收，补充实验另列状态 |
| 参考工程的有限功能验证 | openTPU RAM12组周期对照、实际包装逐bit／资源核对；GEMM两种fusion各500例 | 可验收这些已执行检查，非完整MXU或物理网表等价 |
| 块内实现和预算结果 | 七路基线、两次完成的定向接续、明确成功及失败 | 可按表总结；4份预算通过只是3种块类型的候选 |
| 宏接口／时序模型资格 | LEF、Liberty、详细OBS和pin／timing数量已核对 | 未完成；minimum_period、完整arc、边界驱动负载及PG仍有缺口 |
| openTPU两宏顶层 | 40端口／1662bit接线检查、684bit地址数据＋1bit反馈、共同外边界方案 | 接线准备可总结，正式顶层PNR未执行 |
| 源RTL到最终物理网表等价 | ACT局部型号替换证据；主线形式验证仍运行 | 未完成完整证明，不借用原功能回归代替 |
| H2固定资源、受限定制和多计算图 | 尚无冻结资源与限定金属／通孔的完整实验 | 不可验收为预制底座 |
| 协作流程 | PR10草稿、Issue仍in_review；登记PR5未合并、看板无法核验 | 已提交供审查，未审查合并，不自标done |

本次只读核验主线PR8仍待审查：VECTOR与单宏顶层已有实际路由／PG工程结果，但保留setup、电容、模型及等价限制；队列89448仍RUNNING。它们是主线的独立交付，不并入本页的4份预算通过计数。

## 自主补充的必要实验

已在新根 `yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-17/` 提交并观察到运行：

- **89558／node8／32CPU**：两个exclusive step，各16CPU，分别为 `merged-cap30-repair` 和 `merged-cap40-repair`。
- **89559／1CPU**：afterany:89558一次性产物及严格门槛审计；不是定时助手通知。
- 实际runner `7ffd04d1f5b076f3826067fa17644327fe7abccd`，镜像仍为SHA `49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a`。作业提交后读回UNLIMITED，不设墙钟截止。
- 两路都先核对原06／merged-cap20的CTS检查点和输入manifest，在新目录复制；放置和CTS保持原20阶段结果，保留与根15相同的1个DFF和3个BUF升级，**仅把路由阶段CAP_MARGIN改为30／40**。这不是从综合开始的全流程30／40扫描。
- 新配置生成器要求原配置恰有一个CAP_MARGIN，记录原值和请求值；实际审计同时核对配置和全局布线日志里的 `repair_design -verbose -cap_margin 30/40`，缺失即拒绝。仍要求最终提取后计数0、最差／归一化余量非负、setup／hold及TNS、DRC／天线等全部门槛。
- 两路尚无终态结果，不先假定裕量更大一定改善。无论成功或失败都封存；不会因为耗时取消，不重跑已经通过的ACT／GEMM／MXU。

[17提交回执](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-17-submission.json)和[最近实际阶段](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-17-latest.json)分别记录冻结身份与观察状态。恢复命令：

```powershell
python project/experiments/parallel_blocks/wave2/monitor.py --attempt parallel-blocks-wave2-17
python project/experiments/parallel_blocks/wave2/check_resume_config.py
python project/experiments/parallel_blocks/wave2/check_quality_gates.py
python project/experiments/parallel_blocks/wave2/check_repair_hook.py
python scripts/check_project.py
```

先读取89559的冻结终态和SHA，再更新矩阵；不要只以sbatch成功、COMPLETED或产物哈希通过判定电气合格。该补充能回答合并块的局部名单修复是否应改为全块路由裕量对照，不能补齐所有硬宏资格。之后优先补齐候选宏的时序／边界／PG证据，再开展同资源顶层对照；不以无限参数扫描替代研究结论。

## 检查及协作回执

- `python scripts/check_project.py`、Python编译、原电气门槛回归、Tcl生成器回归和新路由配置回归通过；部署前在服务器对上传Bash逐文件执行 `bash -n` 通过。这些检查不替代运行中物理实验的终态验收。
- 规则rayggxia-project-collab1.0.0；project_id=llm-hardware-design；负责人／实际账号YUZE-LU；Refs #7，延续草稿PR10。当前代码head与实际执行runner分别记录，不倒填后续提交为运行版本。
- 管理中心登记PR5本次再次读回OPEN／未合并，登记pending；本仓库无board.json，已知缺read:project及Projects工具，看板unverified、同步pending，具权限管理员待指定。
- 审查人／优先级待指定；整体Issue仍由主线协调in_review。是否合并、最终验收由项目审查完成，本并行线不自合并或关闭Issue。
