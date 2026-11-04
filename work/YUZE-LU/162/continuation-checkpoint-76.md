# Issue162 continuation checkpoint76

更新时间：2026-11-04T18:36:54+08:00。YUZE-LU；Issue [#162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162)、Draft PR [#163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)；承接[Checkpoint75](continuation-checkpoint-75.md)。

**完整组合仍未通过，任务继续，不合并。** 保留M/N/E/G/S/T六宏、R256、S1350内部驱动、23种原生类型/138份六文件及345状态宿主。规范交付入口仍为[current363](block-delivery-r256-current363/index.json)。三初态八程序及473/480外部AXI/host/结束故障事件继续绑定，不冒称内部dispatch波形。所有新增有状态逻辑位于已列出的M1–M10宏，M11/M12仅被动互联；外部R及其他任务不动。[CONTROL_V1](../../../docs/CONTROL_V1.md)顶部补充当前边界，避免旧235实例/七端点/未接R文字被当作现状。

SSH已恢复。12100/12101复用已实际回归的source1184，分别方向代价2/8、stride16/8，加法历史、global batch关闭。1211严格核对14份原七阶段规格、六键验收/当前453函数与事件及各自未来几何/PG/三RC/交付路径；1213实核32进程、实际输入体和导入9060 trial0前缀逐字相同、header/实际相邻尝试/CLI、node3/node6各4个16CPU掩码互斥与实际内存。1212只核验后替换本人11700/95098.185和11701/97097.75；原失败及部分结果保留。乘法历史触及原label上限，不据此称物理不可行，原上限未改。

1215同trial/同轮比较11400/1与11920/1，没有显示新增相邻候选线在早期全图上明显受益。cost8第7轮16对平均excess为992853.9375→1015379.3125；cost32为987476.125→991735.25。只代表已读前缀，不能推成最终收敛或普遍速度结论。原对照保留。

1216只对本人node24/96222中11205 trial0实际进程3351258，确认原始输入/二进制/冻结source1104/当前453图SHA并确认处于第64轮后，做5秒99Hz用户CPU-clock采样，未暂停或改亲和。494样本，无丢样；std pop48.58%、push_heap7.49%，合计56.07%。只是该时段的软件采样，不是电路结果或全局瓶颈证明。perf.data 4265776字节留服务器，SHA256 `44e6be3594ec83b3d2da45295e4d3126d0ef5fb98642ae7ddd36f05981f29a71`；小报告及采样前原日志尾已逐SHA实收。

source1218为`16169058c4edc5e09b859c0a1a4e85f8baa0160e`，1020文件，归档SHA256 `b4a62c42851c22837ccdb72fdc81a5874b349839b1dc3a428ff8930d860859a3`；1016项旧源只读硬链接、5项复制含manifest。新增`--route-ordinary-coarse-rounds`，默认64，可选8/16/32，只提前普通粗候选转原完整网格的轮次。原权重退火公式、exact双向类、native有限资源分支、真实网格/pitch/die、M1–M10、pin/via和全部最终物理门不变。每次先上传归档、冻结、完整源/归档SHA校验再排队。

实际1219通过：原1185默认64的两条完整路线主/native日志、路径及第8轮快照逐字一致，全部嵌套旧实际回归仍通过；新增两个实际提前切换后的完整40×40合成路线独立检查全部树洪泛、单位边/via、有限线长与全图零冲突。两项为 `[{'cutoff': 8, 'seed': 972, 'final_round': 24}, {'cutoff': 16, 'seed': 972, 'final_round': 33}]`。另外两次在切换前已完成的合法尝试同样保留，不拿它们充当切换覆盖。四项非法上下文/重复/值/尾缀拒绝；真实仅一轮仍有冲突的尝试无最终输出。实际1221核对1020源、1016未变项、三生产文件仅在自有scratch精确回退至1184、31项native/resource/最终门/helper不变量及exact双向类/native有限分支字节完全一致。小例通过不是完整系统通过。

12220/12221以当前453/S5380/R256/9060 trial0前缀进入原完整七阶段链，cutoff8/16、stride16、方向代价8、拥塞比例1、加法历史、global batch及neighbors关闭，其余对照11400。1223严格核验14份规格和六键原联合配置，各自几何/PG/low-base-high时序及交付路径，不继承任何系统物理资格。1229实核32进程、32对输入体/前缀逐字、真实8/16日程/CLI及仅trial0诊断参数、node5四组及node7三组实际router掩码互斥（不把CUGR进程冒充router）、内存准入。该活动审计未宣称32次都已进入切换轮次；需继续核对实际过渡与最终结果。

1226仅核验后替换本人11600/95155.190以运行1219；12220在1219结束且1221/1223依赖通过后自然补位。1224在实际1219/1221/1223全部通过，并重新核对1220原规格SHA、UID10011/job/node/PID/cmd/source/out/当前图、所有日志、无最终/获胜输出和内存后，仅替换本人11601/96297.88，全部旧源/规格/日志/部分产物保留。其他候选、独立CUGR3751、父作业和外部R未动。8父节点/36×16=576CPU，c64每节点4×16，c96每节点6×16动态补位。node5未来256GiB预测需323.2GiB可用，node7未来224GiB需284.8GiB，实际准入通过，未降低并发。

[远程索引](continuation-proof-76/index.json)绑定571项SHA，[原字节ZIP](continuation-proof-76/selected-originals.zip)含158项，逐entry SHA/CRC通过。14个运行日志是不可变读取前缀，未称最终输出。大路径及原perf数据留授权服务器并绑定。[本地索引](continuation-proof-76/local-index.json)/[ZIP](continuation-proof-76/local-helpers.zip)保存69项编排与实际报告；提交时另核对实际Git blob。继续完整零冲突全图、真实M11/M12几何、PG、三档分布RC下300MHz setup/hold/电气及全部声明组合联合验收，再交最终六文件、版图和源索引。

规则rayggxia-project-collab1.0.0；project_id llm-hardware-design；负责人YUZE-LU。管理结构检查PASS；物理业务验收未完成。登记management-hub PR5 pending；缺board.json，看板unverified/同步pending，处理人待指定；审查人待指定；Issue in_progress，PR Draft/open/未合并。
