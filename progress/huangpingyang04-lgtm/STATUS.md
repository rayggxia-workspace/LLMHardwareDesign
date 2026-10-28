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

当前检查点：2026-10-28T14:54:42.612268+00:00。整体in_progress：阶段一pass_with_inherited_issues；阶段二/三未验收；四未执行。资源并集底座主候选1/3，**未冻结**。冻结后两完整案例共享全部Block/有源资源、位置/朝向、低层内部/固定连接、PG/clock和M8接入点；主方案M1–M8固定、只M9/M10及真实via8_0/via9_0定制，M11/M12后备未启用。openTPU保持otpu_asic_top全部33内部SRAM；llaccel配置EPILOGUE_FUSION=0、DMA_MAX_OUTSTANDING=16，外16SRAM bank/DRAM/主机参加功能测试但不计core面积。

**最新实际失败结论：较短的54形状路线物理通过，电气/时序变差，拒绝采用。**
92818有限9项预筛后，92819实际DEF读入因末行via合并丢失NETS分号而失败，在生成ODB之前退出，不是物理不可行；原失败保留。509e425修正结束符/完整record后置条件，92821实际格式回归及完整导体/cut预筛通过。

92823实际ODB及新进程读回：net83203 54形状，完整41相关网/3处边界端口连通，异网接触0；八类全量资源/端点表和全部非目标保持，已改善的M3输出接线保持，M9/M10为空。**原27条native DRC逐条保持、新增0/遗漏0，不是零DRC或制造签核。** 92826独立original_route_reuse来源资格及11实际报告破坏负例通过。ODB 585047369字节，SHA-256=3f795732af6e48adfd2e076a0263f8794bd3e8e1ca9ae4e893c96013855e2010。

92827真实OpenRCX/原3ns/同Lib、SDC、RC、提取frame和完整端点清单已完成：setup WNS−4.173063790419197ns、TNS−1057.7092852062ns、287负端点；hold WNS+0.02439915005763723ns、负端点0；cap56、slew0，fanout无有限约束不算通过。92829与紧邻保留e238版严格比较：新增/消除负端点0，但10个既有setup端点数值恶化，最大额外0.0257571749ps；3个既有cap项恶化。与真正原始相比仍200个setup/27个cap项恶化，最差额外3.157474371ps。**因此拒绝54形状候选，保留e238（原来200setup/26cap仍未通过），不能用WNS/计数相同或很小的数值差异豁免。** 新SPEF 426150417字节，SHA-256=7927f52f53ecafc12f15f84f4bf872d07f0474d5138441cf95cc79bebe589449。

92839实际缓存适配首次通过：原始/preM8两份参照的native/SPEF/源ODB/parser/helper SHA精确一致，各4项真实缓存破坏负例检出，没有重扫两份参照；只对新候选读取8896892行/54形状及真实SPEF。相对e238，net83203总电容+0.1771fF，ground+0.673863fF、coupling−0.4967918fF；M8普通矩形长轴累计8.0→4.4um、实际via16→15。该长度是矩形统计，不是完整中心线长/电阻；较短与较少via未保证较低电容。旧92807不兼容缓存失败保留，现仅兼容的内部net/两参照分支得到实证，不推广任意Block。

路径诊断92840因我在launch spec填错已有脚本名而退出2，在EDA/解析输入之前；失败源码/命令/日志保留。已从成功92801的真实spec核实report_selected_endpoint_paths.py，92842新目录实际通过，只测新候选，复用原始/preM8报告。92849同序列297个pin/edge arc及4实际报告破坏负例通过：net83203自身延迟相对原始多1.451969ps，驱动BUF_X8延迟多1.102924ps、负载38.344829559→44.768875122fF；仍有其他门/时钟变化，不作排他单网因果。路径/缓存诊断不是新功能或物理验收。

**后续有限动作已实际运行。** 基于上述失败，只预筛保留e238之上相邻3条M7轨道：92845的offset8000因4项导体冲突拒绝，无ODB试改；9600/11200两项通过标量筛选，实际物理试验92850（RUNNING）/92852（RUNNING）分别4CPU。只改变同一内部网络的必要迁线，完整41目标/3边界/所有资源与非目标/原27记录仍须通过，尚无RC收益结论。共同资源、Block数量/布局、位宽/容量/流水未改，主要底座仍候选1/3；不是新增两个主要底座。

**AUX与整片主线。** 新AUX基线92750完整详细布线/fresh native DRC0/放置0/PG/接口资源通过；92796全部620686信号网/1832001必要端点连通；92797最终.v字节及完整八表与CTS精确相同，5身份破坏负例通过，因此限定复用65545状态/168074锥证书。92805实际原3ns仍失败：setup6100、hold8673负端点、cap1317；92809全部555400 active SPEF网/1766715端点精确覆盖。这些不是新AUX质量或上游RTL/完整case通过，旧严格状态3696图差异保留。

92810为RUNNING，已经实际执行repair_design、repair_timing与阻值感知reroute，GRT阶段结束但仍警告无法修复全部setup；**已进入详细布线，最终native/真实RC/质量未闭合**。实际DRT读取5_1_grt.sdc，create_clock仍3.0000ns；updated_clks.sdc4.2480只是诊断，未用于放宽约束。新buffer/尺寸变化只在本人未冻结辅助内，旧92797字节身份不能自动沿用。已排队92832新完整状态锥/92833全网检查：existing continue_after先验证精确92810实际COMPLETED0/固定提交/正确receipt再运行原检查器；前驱失败则不运行。它们仍未执行，不是新证明；严格锥若失败应保留，再依据完整状态骨架决定是否可用已资格化的库对称性方法。

92538为RUNNING，本次3216/4096区进度闭合，仅部分覆盖；92793条件续查等待自然终态，92547/48原来源/固定路线依赖保留。**14059固定连接仍是方案，尚未完成实际固定导线；每案例841闲置扇出未完成。** 共同PG/clock/固定线/全局几何/新物理网表完整功能与质量、冻结、两个完整case定制仍待完成。旧92508 open20例/87160行/2317514字段、92505 llaccel六组180任务/243883行/17769493字段仅绑定当时版本；原始/后续变更不能混作最终验收。外部clock rise/fall及open37常量输出负载用户确认未确定，保持null而非0。

**可追溯性与资源。** 新作业均4CPU、native≤4、BLAS1；物理92823 wall1398s/CPU2092.257s（平均1.497核），RC92827 wall208s/CPU260.946s（1.255核），缓存92839 wall50s/CPU48.511s（0.970核），新路径92842 wall55s/CPU70.480s（1.281核）。单线程不声称4倍提速；未停止其他或本任务已有进程，不重复活跃实验。实际4核allocation/affinity、source/config/tool/输入及结果SHA分别由driver/索引绑定。OpenROAD版本字符串unknown，以二进制SHA 0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53锁定。共享磁盘本次只读核查剩余约9.9TiB，不复制原整套资料。

服务器根目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z。本轮源码b9d0ef37836c13c20003a8b6737873fbf58d2af1；最新索引/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261028T145442Z/milestone.json，SHA-256=beaf536af4c766b8e8873533ec0ce058906c7da891aa590ce28d612182c3f380。54形状ODB路径/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/vector-wr95-coincident-projection-physical-r02-4c-01/patch/patched.odb；SPEF路径/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/vector-wr95-coincident-RC-r01-4c-01/extraction/extracted_coordinates.spef。大ODB/DEF/SPEF/全量日志/PDK均留服务器。只更新原六份进展/方法/README/个人记录与结果索引；本次运行源码快照仍在服务器，不声称全部Stage2/3算法源码已入库。

GitHub继续Issue55/task分支/草稿PR58；上一汇总8f8f312已验证，当前远端另有6f553c6六Block内部图，非新物理验收，保留并行成果。新的精选上传以本轮交付回执为准。登记沿用管理中心PR5 pending（未重核）；看板unverified/同步pending（无board配置/已验证Projects接入），待有权限维护者；审查人待指定。整体in_progress，不合并、关闭或标done。

下一步：读取两个有限上方候选的真实完整物理终态，只有来源核查通过后才真实提取并比较完整原始/e238质量；继续92810详细布线及其新状态/全网验证，保持整片/固定预连线主线。全部必需条件闭合后才冻结并验证两个完整案例。
