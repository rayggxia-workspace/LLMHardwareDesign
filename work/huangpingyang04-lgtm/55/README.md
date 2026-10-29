# 完整案例共同底座集成

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。正式[入口](../../../project/experiments/block_full_integration/README.md)、[阶段](../../../docs/experiments/issue-55-full-block-integration.md)、[方法](../../../docs/experiments/issue-55-block-integration-methods.md)。

唯一服务器目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

新源码/配置用新commit与独立driver/output；原始文件/封存结果只读，大数据库/trace/编译产物/缓存全留服务器，无安装或大文件下载。GitHub仅阶段一PR58草稿未合并，登记/看板缺项不伪称完成。

<!-- current-buffer-PG-status -->

更新时间 2026-10-29T15:36:10.759324+00:00。限时北京时间 **2026-10-29 21:19:06 至 2026-10-30 09:19:06**。候选1/3 **UNFROZEN**；阶段一pass_with_inherited_issues，二/三未验收，四NOTRUN。主方案 **M1–M8固定，M9/M10及via8_0/via9_0定制**；M11/M12未启用。两个完整案例/6资源规模不变。

已闭合的局部实际证据：
- VECTOR完整733599实例、26BUF_X4/52目标网实际DRT、真实引脚恢复、非目标/原几何保持、连通与PG通过。93443同原GCell上下文完整native DRC恰为原27记录，无新增/改变；不称零DRC。93445来源资格及4117状态/10973锥与完整实际网表字节绑定通过。93446实际RC覆盖376331活动网/1073722端点、2246个M8锚点及正电阻图。
- AUX完整546459实例。93447只恢复祖先锁定的精确GCell网格，其余完整DEF字节相同，整片native0；93458独立新进程13张native表逐字节相同，93459完整源原位置及扩展die四角5组故意短路全检出（12Short）。93461完整新鲜网表与65545状态/168074锥证据字节绑定；93468组合来源资格通过。原45条失败回执保留、不豁免，具体C++机制仍未确定。
- AUX93473实际提取SPEF与原3ns时序测量完成；93483精确覆盖558017活动网/1771925端点、13507个M8锚点及正电阻图。**测量/覆盖通过不代表质量通过。**

未通过/新失败：
- VECTOR setup WNS **−4.178061570528197ns**、287负端点；相对原输入230持续负端点恶化，最差5.546230298676ps at wr_data_r[224]$_DFFE_PN0P_/D。hold +0.02445144156357598ns/0负端点、slew0。cap从59降至30，但 _318176_/ZN（NOR2_X2，net _182649_）与 place148481/Z（BUF_X1，net148463）分别恶化0.004136920/0.003090143fF。93476实际SPEF分解确认这两网寄生变化，责任邻网/具体物理根因未证实；不能按继承问题放行。
- AUX setup WNS **−1.5718480295594668ns**/5694负端点；hold **−0.24845443072813203ns**/36负端点；cap1047、slew0。最坏setup路径 u_attn.og[0]$_DFFE_PN0P_ → u_attn.wdata_acc[933]$_DFFE_PN0P_；最坏hold bit_1352205 → u_xbar.rstart[33]$_DFF_PN0_。当前派生AUX质量未达标，非原输入继承豁免。外部bit语义待核对，不编造。
- **93130完整父层191实例/14059固定网DRT已于14:26:01 UTC失败结束**：程序自身43200s超时，Slurm FAILED1:0、wall12:02:12、CPU1-23:06:46（均3.914核）。末次第0轮50%/3332037是中间违规数，无最终布线DB/DRC结论。原GRT也报GRT-0116 congestion；737455 guide矩形是规划，绝非14059网已布通。不原样重复12h试验、不手动停止。正在只读测量保存的拥堵网格以定位；具体拥堵网络/根因尚未定位，不凭超时断定硬件不可实现。

正在运行/最小行动：
- 93485全规模52网新试验只将M2/M3/M4的GRT容量成本减少95%以偏好M5–M8；原层范围M2–M8、位置、几何、逻辑、3ns不变。旧RC残差给出此假设，未证明有效、不缩硬件。
- 4核后继链 **93488引脚恢复 → 93490整片DRC → 93491来源资格 → 93492实际RC/时序**，成功状态、实际调度/精确SHA前置门槛不变；任何前置失败拒绝继续。Python比较多为1核，未宣称四倍提速。
- 继续当前新源完整功能回归接入、AUX具名时序/负载定位及父层拥堵定位。共同PG/clock/idle整合、冻结、两版完整定制布线及最终功能/物理总验收仍未完成。外部clock rise/fall与open37常量负载用户未定，保持null。

本轮目录 /public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/convergence-12h-20261029T131906Z。服务器工程版本 **8fc21453e09fd4add179b0fe9ae3e0905b7e1782**；不可变最新索引 /public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/convergence-12h-20261029T131906Z/records/milestone-20261029T153610Z.json，SHA-256 **43c9665c227852fa0b852f7770ab05765dd7ce564381864354899b11310e96fa**。大ODB/DEF/SPEF/PDK/完整日志不入库。沿用Issue55、task/55-full-block-integration和草稿PR58，不合并/关闭。登记PR5 pending、Projects unverified/sync pending、审查人待指定；管理结构检查通过不等于硬件验收。
