2026-10-28 22:48 CST：M236/239的新源封存、最终网表三初态、严格LEC（31296输入/31287输出全匹配）及完整原生/未修改FreePDK45 GDS DRC0均已通过；独立240物理实际失败于919项setup（最小−0.677508ns），hold最小+0.017685ns、电气/PG/连接/真实2µm M10接点/RC覆盖通过，不能接收。已将scale_lane→129位合并/溢出路径拆分，d2acc49的op4为33拍；241/92836三初态与综合通过、正在重做P&R，旧证据不转移。240原生10/3ns精度fixture及三个实际负例通过；242/92843两项只读诊断自然完成，T在原20%缓冲上限下hold−0.236655ns/setup+0.913322ns，S修复前hold−0.534386ns/setup+1.061465ns。原记录−6.088已更正为hold TNS，不是setup。45份实际小回执/报告/Slurm快照见review-20261028/checkpoint-2245/index.json。当前4个本任务allocation为旧92045/92046、236/92811（V物理/R综合）、241/92836（M修复）；完成的诊断与验收自然释放，真实就绪任务不足36槽，未造占位任务或取消EDA。五块新版整体、完整实际引出/预连及性能/资源预算仍未完成，目标active、Issue121=in_progress、PR122=draft；登记pending、看板unverified/同步pending、管理员和审查人待指定。

2026-10-28 22:27 CST：新版M/run236原生六阶段全流程实际通过，外框730µm；run239/92828已提交，M新源封存通过，完整未修改GDS/原生DRC和最终网表三初态回归正在并行，严格LEC依功能补位，尚未独立接收。S/T/run234分别在CTS hold修复90992/41060缓冲上限失败，保留源；T237保存修复前快照但相对输出路径失败，238只读报告已通过，最差输入短路径约0.30ns到达/0.65ns要求。V物理与R综合继续。新增精度参照采用同一工具对批准10/3ns预算的小电路实际读写，精确比分token而不扩大时序容差；本地真实12位读回加六负例通过。239小电路首次漏读技术LEF而失败，已修复待新240队列接续物理门；不重跑通过的源封存/在跑验收。资料见review-20261028/checkpoint-2230与修订合同。Issue121=in_progress、PR122=draft；旧100MHz不转移资格，五块新版整体未完成，目标保持active。登记pending、看板unverified/同步pending、管理员与审查人待指定。

2026-10-28 22:05 CST：五宏修订RTL已落实：M驻留双银行/共享64个S8乘法/归约累加流水，V双统计上下文/长函数/RoPE/全组分块归一化，R同阶段row流水/原子银行切换，S/T连续传输。run234 S/T、run236 M/V/R均通过三初态独立RTL回归，M/V/S/T综合通过；新版尚未最终接收。92804/node13运行S物理，92811/node16运行R综合及M/V物理；T在CTS hold修复41060缓冲后仍负余量而失败，保留源布局及失败回执，准备新副本CTS诊断，不提高上限或放松检查。新版合同docs/BLOCK_V1_REVIEW_CONTRACT.md；29份真实小回执/报告及队列快照见work/YUZE-LU/121/review-20261028/checkpoint-2200/index.json，旧100MHz资格不转移。236为真实六项16CPU起跑、按依赖即时补位；当前仅真实前置任务就绪，后继四门/接口/有限预连/吞吐与模型资源预算仍待完成。Issue121=in_progress、PR122=draft；登记pending、看板unverified/同步pending、管理员和独立审查人待指定。

# 300MHz与粗金属接口审阅修订

Refs [Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121) / [PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)。用户要求实施两份审阅建议并完成新版五块最终布局布线。

- [原件身份和归档副本](source-manifest.json)，外部原件未改；副本仅统一UTF-8/LF。
- [逐项实施/验收计划](../../../../docs/plans/block-v1-review-300mhz.md)。
- [演示几何规则](../../../../docs/technology/M11_M12_DEMO_RULES.md)。
- 原100MHz最终包固定在ad3c2b3，不回写服务器封存物；本目录新run与后续交付保存新版证据。

当前新版合同及真实进展见[22:00快照](checkpoint-2200/README.md)和[修订合同](../../../../docs/BLOCK_V1_REVIEW_CONTRACT.md)。下方初期检查点保留当时状态；新版RTL回归均已通过，但最终物理未接收。诊断结果不是新版验收。最终交付仍须五块各一个实现，真实300MHz最终物理、同源四门、完整端口引出与有限预连检查、周期/流量及面积/接口前后对比。

## 2026-10-28 implementation checkpoint

Initial remote run233 job92802/node13 completed six independently claimed measurements, receipt/report SHA verified in [run233](run233/README.md). P1 independent GDS passed; all five old final timing diagnostics retain negative checks and never qualify revised leaves.

| Old macro at new budget | setup ns | cap violations | slew violations |
| --- | ---: | ---: | ---: |
| M | -3.729412 | 6 | 0 |
| V | -4.868114 | 77 | 1 |
| R | -3.310902 | 3 | 1 |
| S | 0.528991 | 3 | 0 |
| T | 0.710807 | 26 | 0 |

S revised RTL now permits retiring/refilling its one response register on the same edge, still exactly16KiB standard-cell1RW payload. T revised RTL refills the held committed word on each take edge, still one6KiB complete-batch lease, no producer/consumer double-buffer overlap. Fresh independent burst/backpressure/reset tests and fresh mapping/native300MHz flow are prepared but not yet run at this checkpoint. Shared store82 used by historical experiments is unchanged.

The candidate coarse layout distributes every actual port (including clock/control/observations) into <=16-bit directional strips, with2x2 realM10 pins. Horizontal routes avoid vertical-source M11 landing rows. Native footprint may grow only if complete mapped port track capacity cannot fit; outer32um receiver endpoints and40um test halo are charged separately. This is a planned geometry until actual native reconnect/readback and fullDRC pass.
