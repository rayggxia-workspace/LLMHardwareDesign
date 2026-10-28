# 完整案例共同底座集成

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。正式[入口](../../../project/experiments/block_full_integration/README.md)、[阶段](../../../docs/experiments/issue-55-full-block-integration.md)、[方法](../../../docs/experiments/issue-55-block-integration-methods.md)。

唯一服务器目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

新源码/配置用新commit与独立driver/output；原始文件/封存结果只读，大数据库/trace/编译产物/缓存全留服务器，无安装或大文件下载。GitHub仅阶段一PR58草稿未合并，登记/看板缺项不伪称完成。

<!-- current-buffer-PG-status -->

当前检查点：2026-10-28T09:25:46.704869+00:00。阶段一已交付；阶段二/三未验收、四未执行；主要共同底座候选1/3未冻结。M1–M8固定、M9/M10与via8_0/via9_0定制，M11/M12后备未启用。这里的内部迁线均在冻结前本人派生副本进行。

新增真实物理结果：AUX92704只将_269733_完整线路恢复为绑定的保存路线，保存后独立native读回；全部八类资源表/非目标导体保持、精确29条候选形状、全部61相关网络连通和异网接触0、M8访问与M9/M10预留检查通过；全M1–M10原生DRC保持0。92709独立来源检查与11个真实报告破坏负例通过，physical_check_result=pass，仅覆盖该宏来源。原53处via修复和9条clock线路保持，不是共同底座或两整机最终验收。

新寄生/3ns时序与按引脚电气已实际完成（92710/92711）：setup WNS=−1.5094725896ns、TNS=−6735.3168646546ns，5635个失败端点；hold WNS=−0.2393047495ns、TNS=−4.0301105815ns，30个失败端点；电容1087、slew0、fanout无有限限制不算覆盖通过。相对同一自建AUX的f739修复前参考，最大额外setup恶化6.255441ps→0.420997ps，仍439个setup、3个hold、31个电容项数值变差，无新增/解决失败身份。92718新增“相邻两个已测检查点”适配器，精确绑定两份实际测量配置、原SDC/RC/参考census/坐标框架；3个真实上下文负例及既有同数异名负例通过。与紧邻e2b6上一版对照，仍1555setup/3hold/9cap数值变差，最差setup额外0.810463ps、hold0.00383027ps；不能仅因WNS改善约3.398171ps就接受该候选。没有放宽时钟或忽略小负数。

0.420997ps只描述相对本任务旧AUX的增量，不能当作相对原项目的完整质量差异。原完整llaccel匹配RC参考92556和跨边界命名对照92558已存在且本次只读复核：原设计也有时序失败，但边界/clock/状态命名尚未完整归一化，旧对照133个D名称未匹配、3397组非D边界未解决；故新AUX的5635setup/30hold/1087cap未得到输入继承豁免。完整质量仍失败，尚未接纳进底座。

VECTOR当前已合格物理宏仍为271069...（92668/92670）：全40目标/两M8接入与八表保持通过，真正原始27条native记录精确保留、新增0；实际质量仍191setup/26cap恶化。后续候选均未写ODB：92712两网完整旧路线恢复有9处外部冲突；92715一次全源空间索引构建阻挡图，复现此前750形状/9冲突并推导7网闭包，但触碰已修好且受保护的_133774_，拒绝。92717只替换旧网7条M3线，使用真实M3接入/via3_2/M4轨道spoke/via4_0/M5轨道trunk，9项均冲突，最好一项485形状、1处M5垂直线相交。92723三项局部M6桥均被固定net83368长线挡住，493形状每项，拒绝。92725依据这两个真实平面阻挡，尝试有限M6垂直接入/M7水平桥，结果以execution和调度终态为准，不能称布线通过。原受保护网络、PG、位置和逻辑从未为此改变。

92538仍运行，当前2080/4096区闭合只是部分覆盖；92547/92548依赖等待。14,059条固定连接仍为方案，未完成实际导线；每案例841闲置扇出也未完成。原外部时钟rise/fall和openTPU37常量输出负载用户确认未确定，保持null而非0。旧有限完整功能回归仍只证明相应版本，不能替代新宏或最终物理回归。

所有新作业4核。AUX92704 wall2260s/CPU3180.264s约1.407核（4核容量35.18%），MaxRSS54667708KiB；92710 wall399s/CPU489.185s约1.226核（30.65%）。VECTOR92715 wall439s/CPU438.012s，92717 wall460s/CPU458.060s，主要单线程约1核，未声称4倍提速。没有停止或重复提交仍运行实验。

服务器根目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z；归档源码：609af5ea1d00fc9378680ab7e000bc3e5164fd9e。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261028T092546Z/milestone.json；SHA-256=4b986059bdcc9150541f05ccc00ae1afeab9d2420f8670095f9254d1a54ce349。AUX新DB SHA=1c26855fa682765ce26e42b84d93b10d8977035e47da0add609249059c222040；新SPEF833714310字节，SHA=8c6cee97b42347676a1cc18c7804035e6c8eec62c85948c33f8c903cf930de23。上次远端精选提交8ddf87b2f1d15671ee523cac07bea213dc0d794c已精确读回；本次上传以独立交付回执为准。只上传六份既有摘要/方法/进度入口，不上传大型DB/日志/工艺。PR58草稿/Issue55进行中，登记沿用PR5 pending（未重核）、看板unverified/同步pending（无board配置/验证接入）、审查人待指定，不合并/关闭。
