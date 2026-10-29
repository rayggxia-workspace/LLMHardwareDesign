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

更新时间：2026-10-29T11:50:29.191790+00:00（UTC），Refs #55 / PR58。候选1/3 **UNFROZEN**；阶段一pass_with_inherited_issues，二/三未验收，四NOTRUN。openTPU仍为完整otpu_asic_top及33内部SRAM；LL仍为EPILOGUE_FUSION=0、DMA_MAX_OUTSTANDING=16，外16SRAM/DRAM/host在功能测试环境。冻结后M1–M8固定，M9/M10及真实via8_0/via9_0定制；M11/M12未启用。

**实际通过的有限检查：** 获批26具名CORE_SPACER已在派生副本替换为26BUF_X4+53填充；3处6个原PG矩形保留，733520受保护原实例及原导体/阻挡保持。完整733599实例的放置/PG拓扑通过（非IR/EM）。93344实际写入52个首通孔与M1短引出：26区域native DRC均0，独立52序列化路径读回、真实短接负例和全源非目标保持检查闭合。最长M1引出660DBU=0.33μm，未移动26个获批位置。仅接入资格，不是完整信号已连通。

**新失败与实际修复证据：** 93364的完整临时端口投影/还原在全部8类native资源表、所有网导体/通孔多重集合比较和真实错网/删shadow负例上闭合；但同一还原进程write_verilog残留52临时端口，整体正确记FAIL。93368、93370依赖guard拒绝，child_launched=false，没有运行信号布线。没有删文本、忽略差异或把旧失败改成通过。93376新进程只读重载同一保存ODB，再导出的完整45,635,764字节网表与原placement逐字节相同，SHA-256 **6884f81cc974d0c7d8aa48d5c64a545e2bb76d0d0e8f10c7ea0fd83a310c5702**。93379新资格记录严格绑定旧物理闭合证明、真实负例和新进程导出，状态PASS_COMPLETE_BUFFER_TERMINAL_PROJECTION_WITH_FRESH_EXPORT_ONLY；它是可追溯的布线输入检查点，不是完整物理/功能验收。原大数据库只读复用，没有重跑25分钟投影。

**正在执行/等待：** 新93383（4核）在完整源副本中仅把原普通路径ROUTED状态改为FIXED，并要求全部733599实例/端点/所有导体几何严格一致；尚无闭合结果。新93385（4核）依赖93383，只有真实COMPLETED 0:0/4核且源资格通过才允许启动完整52信号网native PA/GRT、独立AP/guide/全源保持读回，再进行实际DRT。仍不是布线通过；DRT输出明确标UNACCEPTED，原BUF端点/首通孔还原、全网连通/短路/完整DRC/PG、RC/3ns时序及完整功能仍须逐项执行。新版本23bee7b5115ffe4d943e182946e338556bebf870；每次source/config变化使用新快照/新目录，不改失败或封存运行。

**其他主线仍未闭合：** AUX93191仍FAIL45项M3间距；93336只改FIXED/ROUTED状态后45原记录完全相同。93351完整546459实例/全几何的覆盖整片coarse-GCell诊断仍运行，且其结果不能覆盖原45或直接放行RC/LL后继。93130完整191父层/14059固定网DRT仍运行；最新日志为第0轮40%、中间报告3053444违例，**非最终违例数或不可行结论**。清单/guide不是完成的预连线。没有停止或重复这些作业。

下一步：先闭合93383→93385真实结果；成功后仅在新副本移除精确临时端口/保护shadow并接回52真实BUF端点，保留全部原有及新布线几何，再执行独立全源/连通/DRC/PG和RC质量、当前版完整功能。失败先保存证据并定位，不放宽时钟、不缩规模、不删PIN/OBS。AUX继续解释并解决45项，不挑有利上下文。共同PG/clock、各841闲置sink、当前完整回归/冻结/最终两案例尚未全部完成。用户未定的clock rise/fall和open37常量输出load保持null。

服务器根：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z
工程源码：23bee7b5115ffe4d943e182946e338556bebf870
最新证据索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-projection-fresh-export-checkpoint-20261029T115028Z/milestone.json
SHA-256：3286dec9ef205564de71366a37b0def62890eba7feade95c1e45f2a3ba7c122c
资源：新作业统一4CPU/native≤4/BLAS1/实际cpuset；Python比较主要1核。93344 wall948s/CPU964.273s，平均1.017核（4核容量利用率25.4%）；93364 wall1549s/CPU1548.686s，平均1核；93379 wall7s/CPU5.419s。申请4核不等于四倍提速。大DB/工艺/全日志仅服务器，后阶段完整源码尚未全部上传。登记PR5 pending，Projects unverified/sync pending，审查人待指定；Issue55 in_progress、PR58草稿未合并。


<!-- block-layout-routing-lessons-20261029 -->

经验积累（2026-10-29，UTC+8）：补充[Block 划分后的布局布线问题与处理经验](../../docs/experiments/issue-55-block-layout-routing-lessons.md)，Refs #55 / PR58。区分受保护原单元与新增缓冲器位置、具名填充替换和 PG 金属保持；记录 AP/via/短引线预筛、实际布线、完整 DRC、RC/时序与功能的不同门槛，以及 AUX45 仍未解决的反例。文档依据18:00的只读快照，后续实验状态以主任务最新回执为准；本次仅文档/轻量索引，不启动或改动主线实验，不改变底座冻结及任务验收状态。服务器独立交付包：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/deliverables/block-layout-routing-lessons-20261029T100718184702Z；证据索引 SHA-256：96da8e3ee0c638a3ba9fddfad8399fd61334d7431dcd3255afd4a64d79955b97。
