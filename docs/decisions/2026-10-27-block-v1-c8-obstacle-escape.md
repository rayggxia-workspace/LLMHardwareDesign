# C8预制前上层接入的有限障碍事件布线

来源仍为128实际最终C8、162原生全片49/37项失败、163全部标记/网络只读定位。134完整物理组已在严格LEC门失败，A/C虽有UNSAT/IDENTICAL，但输入共同289078、diff0=1004/diff1=1032，PI为290082/290110；完整正向对应不满足，保留失败，尚未进入独立全版GDS/DRC。不能放松对应门或把“IDENTICAL”单行视为完整接收。

163所有实际M9/M10/via9普通导体与过孔矩形保留，全部其他网、PG、BPin、selected网完整低层/库端点也保留。native_c8_geometry只接受已封存源中逐形状Counter匹配的1600DBU宽原生upper线及via9_0模型；删旧路径时按计数逐个删除，不因via8/via9相同M9 enclosure而把固定via8一起删去。索引仅筛选候选，精确整数距离最终判定，metal基础spacing1600DBU/cut1760DBU；完整原生规则仍另验。

先对95个报告网络生成有限固定via文本提案。若仍与任何实际异网upper矩形冲突，仅将这些网的M9/M10/via9路径同时暂撤；固定via8 enclosure、M10 BPin和其他实际形状仍作障碍。再按网名固定顺序单via9布线：候选落点限制为原pin/via9范围各外扩12800DBU（6.4um），按实际die边缘缩限；这只是算法候选区域，不裁剪障碍。候选来自原坐标、障碍spacing边界及圆角整数距离事件，向外取整到10DBU制造网格，固定线长/距pin/坐标顺序；对M9/M10的两种L方向确定顺序尝试。每个候选须不增加原M9+M10总线长，保留M1–M8与其他所有via的路径身份、固定pin和完整逻辑端点。找不到就保留失败，无随机种子/PPA参数扫描，无自动增补有源资源。

实际163几何离线控制：全部95条源路由矩形逐项匹配；A45网/C29网文本有变，其中15/4网需落点合法化；完整upper异网接触0、报告网对所有异网的基础spacing预检0，两次重放完全一致。12个声明随机/负坐标/跨bucket场景与独立穷举spacing对Counter完全相同；缺真实源矩形及未报告异网障碍控制均拒绝。仅证明预检，没有实际ODB或原生规则资格。

165实际探针将重载原128 ODB，完整重导出DEF/V/几何并与163 SHA严格相同，执行有限新DEF导入后核验全部NETS/端点身份、其他section、full V、其他网/固定低层及预测矩形逐项一致。全部上层跨网接触、selected完整端点连通、断via反例必须通过。由完整实际upper矩形产生GDS union，读回XOR须0，再执行固定原生完整deck中的原样M9/via9/M10规则段，after需0；此union**没有与完整库GDS作比较**，原标记计数可能因merge合并，不伪称重现原raw item数。

实际probe仍明确full_native_drc_qualified/regenerated_rc_sta_qualified/exact_final_function_qualified/qualified_hard_macro=false。下一步依次是新的原生最终输出、全片DRT、新RCX、严格LEC对应、独立完整GDS/DRC/全部端点STA电气/PG与精确最终功能；134对应问题另需定位，不被几何通过覆盖。165在同一c96 allocation内两路各2CPU，24GiB/路估计加20%内存余量，2/1并行，peer失败互不取消。此源码提交时165尚未部署/运行。


## 2026-10-27 17:28 CST 实际终态与后继入口

165/92314实际C8 A/C探针全部11门通过，4:36、TotalCPU7:29.230、MaxRSS4128260K，node25同allocation双2CPU。A45/C29网改动，其中15/4处via9落点；原生upper诊断合并标记A37/C25降至0，完整upper接触0、固定低层/其他网/完整V及源SHA保持。这不是162原raw49/37项的完整GDS接收。166/92326只读严格LEC诊断双1CPU实际通过，0:50、CPU1:20.266、MaxRSS71428K；A/C时序实例143988逐名相同，无新增/删除，A501/C277处DFF_X1变DFF_X2，无字面x/z输入，但尚未证明原生未匹配PI对应，不豁免严格门。141/92256实际FAILED/1:40:06/CPU3:20:52/MaxRSS358556384K，同样被严格C8 LEC拒绝，未完成组合功能。新167准备从实际165接受ODB重新原生最终输出/默认flow LEC/RCX及全片DRT，c96双8CPU，200GiB/路加20%余量；本次提交时尚未运行。T6K161完整接收和164视图通过仍不等于宏边界资格；164 Liberty PG及完整flat timing源另以新版本修正。17:25本任务4个RUNNING allocation（057三路、067）；统一预算基础6/上限8，含PENDING/未知；其他成员未操作。完整P0–P6未完成。

证据：results/run165-group-terminal、run165a/c-terminal、run166-group-terminal、run166a/c-terminal和run141-group/a/c-terminal（均位于work/YUZE-LU/121/）。167采用native_pipeline_c8_escape.json、native-c8-finish-group / native-c8-run-shared109-a/c，保持严格状态边界LEC未通过标志；不启动已知依赖失败的完整接收。
