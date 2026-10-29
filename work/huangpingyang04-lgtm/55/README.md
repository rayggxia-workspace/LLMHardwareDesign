# 完整案例共同底座集成

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。正式[入口](../../../project/experiments/block_full_integration/README.md)、[阶段](../../../docs/experiments/issue-55-full-block-integration.md)、[方法](../../../docs/experiments/issue-55-block-integration-methods.md)。

唯一服务器目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

新源码/配置用新commit与独立driver/output；原始文件/封存结果只读，大数据库/trace/编译产物/缓存全留服务器，无安装或大文件下载。GitHub仅阶段一PR58草稿未合并，登记/看板缺项不伪称完成。

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
