# huangpingyang04-lgtm 的进度

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。阶段一已交付；二/三未验收、四未执行；主要候选1/3，无冻结。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

- open原20例、三seed两次host任务、162 VPU/控制与120 MM/QACT有限回归及独立证据通过；LL180连续任务/540完整内存通过；不是全输入证明。
- 当前两辅助state-cone/M8/RC锚点/抽象PIN/OBS/model link资格通过；新辅助时序与VECTOR新增/恶化未解，不归继承。另一全规模LL候选布线92018继续，不重复/停止。
- 92044方向bug、92071 cut间距、92078旧图断开失败保留；92085新点集fixture/92087规划通过，没有放宽规则、移动Block或切换M11/M12。
- 新任务4核，线程匹配。92063用7:04/CPU8:31.805，均1.21核；92064用13:21/CPU13:30.398，均1.01核；92026用25:08/CPU25:11.394，均1.00核。未停止/在线切换旧作业，不称四倍提速。
- 恢复先读最新milestone与driver/submission/source_revision/spec，再核对sacct，避免重复。92026新源PG独立检查、92063全六资源held-reset、92064当前13局部接入已各自通过；核查92087完整5网原生读回和92018候选完整布线。继续active+idle任务/物理parking、时钟质量RC及新增时序问题，再冻结和两完整案例M9/M10定制。freeze/route仍未实现，无阶段二/三/四验收或新远端push。
- 远端仅阶段一，无新push；登记pending、看板unverified/同步pending、审查人待指定，不合并/关闭。

<!-- current-buffer-PG-status -->

当前检查点：2026-10-28T15:51:33.599266+00:00。整体in_progress；阶段一pass_with_inherited_issues；阶段二/三未验收；四未执行。资源并集底座主候选1/3，**未冻结**。冻结后两完整案例共享全部Block/有源资源、位置/朝向、内部和固定连接、PG/clock及M8接入点；现行主方案M1–M8固定，仅M9/M10和真实via8_0/via9_0定制，M11/M12后备未启用。openTPU保留otpu_asic_top全部33内部SRAM；llaccel保持EPILOGUE_FUSION=0、DMA_MAX_OUTSTANDING=16，外16SRAM bank/DRAM/主机参与功能测试但不算core面积。没有缩减硬件或放宽3ns时钟。

**新增实测结论：两个M7上方候选均物理通过，但电气质量恶化，拒绝。**
92850/92852真实ODB及读回、92856/92857独立完整来源资格通过：全部41相关网/3边界、全部八类资源与非目标、原27条native DRC逐条保持且新增0，M9/M10为空。不是零DRC或制造签核。9600候选ODB SHA=27fc135711941bc7f8c3eef66fb47431296ca79ebfa8193f4acfca6f98ddb5f0；11200候选SHA=fc3af6c4b890aeae317fd190e96094a487eff7a462d29675a9f2a93b01b50e08。

92858/92860在原3ns、同Lib/SDC/RC/frame上完成真实OpenRCX/STA，92862/92863完成全部原始/e238负端点和逐PIN电气比较。9600/11200的setup WNS分别−4.173064234508419/−4.173064678597641ns，TNS均−1057.709398893041ns、287负端点；hold +0.02439915005763723ns/负端点0，cap56、slew0。fanout无有限限制，不算覆盖通过。
相对紧邻保留e238：**分别29/83个既有setup负端点恶化，各1个既有cap项恶化**；最大额外0.0950350936/0.1199040901ps，新增/消除负端点仍0。相对真正原始，两候选均200setup/26cap项恶化，最差额外3.2267522900/3.2516212865ps。因此拒绝两候选，不按WNS/计数相同或差异很小豁免；有限M7上方轨道族停止，不宣称整体不可行。之前54形状路线同样因10setup/3cap退化拒绝，错误证据保留。
92870一个4核作业串行完成两份真实SPEF/native诊断，严格复用兼容原始/preM8视图而不重扫参照。相对e238，9600/11200的net83203总电容分别+0.1987/+0.2452fF；ground−0.905280/−0.807880fF、coupling+1.103940/+1.0530114fF。诊断只分析同一已实测选定内部网，不作排他因果或功能证明。

**新有限候选：在M8保持原接点，不再继续扩大M7轨道搜索。**
fa8ea6b新增显式same_plane_upper_projection_v1：把原M9水平段移到相邻M8的非首选水平线，保留原M8两端导体，只移除两个旧via8_0；其余原目标几何精确保持，无单元/状态/流水/clock/内存/Block布局变化，仍是冻结前原资源的必要迁线。
92871已实际通过合成拓扑/准入/分号/破坏测试、原58形状DEF/native精确往返、当前8896896行导体/cut完整预筛；仅1个候选，52形状，接触/冲突0。**这是预筛，不能写成真实布线/DRC通过。**
实际物理92874为RUNNING，固定源码d0da269cddbc1788de0fe447b531fe1a11ad41bc；独立来源92883为PENDING、真实RC92884为PENDING、原始/e238完整质量92885为PENDING。已实际提交四核后继，按精确submission/源码/receipt及实际COMPLETED0严格门槛顺序执行。任一前驱未通过则后继拒绝，**现在没有M8真实物理或电气通过结论**。保留e238 SHA=e23827eea06a8f74bbab2f49ed87d75d2bb83741a829b5735de0a28454f94102；其相对原始200setup/26cap仍未通过，也不是合格最终源。

**AUX与整片主线继续，不因汇总停止。**
92750新AUX基线详细布线/fresh native DRC0/PG/放置/资源通过；92796全部620686信号网/1832001必要端点连通；92797最终.v字节及八类表精确等同CTS，仅限定复用65545状态/168074锥证书。92805真实原3ns仍setup6100/hold8673负端点、cap1317；92809精确覆盖555400 active SPEF网/1766715端点，不能把覆盖通过写成质量通过。旧严格3696状态锥差异保留，旧完整core和自建AUX边界/clock不同，不全部豁免为继承。
92810为RUNNING，实际调用repair_design/repair_timing及阻值感知reroute，正在详细布线；GRT估计不当最终提取结果。DRT读取5_1_grt.sdc、clock仍3.0000ns，诊断updated_clks.sdc4.2480未用于放宽。新增buffer/resize在本人未冻结辅助内，不能继承旧字节身份；92832/92833新完整状态锥和实际全网检查仍分别PENDING/PENDING，未完成即不宣称新功能证明。
92538为RUNNING，仅3456/4096区闭合进度；92793条件恢复等待自然终态，92547/48原来源与固定线路依赖保留。**14059固定连接仍为预连线方案，尚未完成真实完整固定导线；每案例841闲置扇出未完成。** 共同PG/clock/固定连接、整片检查、新物理版完整功能和质量、冻结及两完整case定制均未验收。原open20例/87160行/2317514字段和llaccel六组180任务/243883行/17769493字段仅对应旧版本。外clock rise/fall、open37常量输出负载未确定，保留null。

**算法与记录。** 方法文档精简为13部分：分离底座生成/使用、结构/状态/布局/PG/clock/迁线/全片/真实质量/严格后继与失败反馈，并标明入口支持范围；旧232939字节方法全文存本次previous_methods.md及Git历史。当前route入口只实现固定父层连接，replay仅native清单；不声称已完成任意Block/LLM编译器或全流程重放。所有Stage2/3运行源码固定在服务器快照，精选文档更新不等于完整算法源码入库。

**资源和追溯。** 新作业均4CPU/native≤4/BLAS1，不独占节点、不停其他或本任务已有作业、不重复活跃实验。92850/52 wall1409/1408s、CPU2130.536/2128.258s，平均约1.51核；92858/60 wall211/209s、CPU264.309/262.156s，约1.25核；单线程不声称4倍提速。实际allocation/affinity、源码/配置/工具/输入/产物SHA由各driver和索引绑定。OpenROAD版本字符串unknown，二进制SHA0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53。
服务器根/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z；本轮源码5c5a68ef15d09dc0c3c57c6b149beae5a51d1c61。最新索引/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261028T155133Z/milestone.json，SHA-256=8a606cd2c624fdbf9530caebe1fab3be69a7010df24777726f39a3f8308fbbdb；历史索引、真实ODB/SPEF和完整日志均保留服务器。只更新原六份进展/方法/README/个人记录/结果摘要；不上传大数据库、全量日志或工艺。

GitHub沿用Issue55/task/55-full-block-integration/草稿PR58，原已发布44511b859c2dfa4ae5bf40e888739158cb419bef及并行图形成果保留；本次精确远端提交以交付receipt为准。登记沿用管理中心PR5 pending（未重核）；board unverified/同步pending、reviewer待指定，继续in_progress、不合并/关闭/标done。
下一步：读取M8实际物理结果，严格资格后完成真实RC/原始及e238完整质量，再决定是否采用；继续AUX详细布线/新状态/全网及整片/实际固定连线主线，所有必要条件闭合后才冻结和两完整case定制。
