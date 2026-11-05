# Issue162 continuation checkpoint15

2026-11-02 21:32:15 CST；YUZE-LU；[Issue162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162) / [PR163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)，in_progress / Draft，继续执行，不合并。rayggxia-project-collab1.0.0；登记management-hub PR5 pending；缺config/board.json，看板unverified/同步pending，处理人待指定。

[207项源绑定证据](continuation-proof-15/index.json)，206项原文件逐字节复制且已本地复算SHA。228271993字节的完整native-cap-residual报告留获授权远程目录，索引路径/大小/SHA；不可把其摘要当完整报告。运行中的日志/queue-state为此时刻快照，本地字节冻结；其远程可变路径之后可以更新。

## 用户的S物理边界决定及实现

用户明确选择“在 S 内补驱动，重新验收 S 版图”。[决策记录](../../../docs/decisions/2026-11-02-issue162-s-internal-drive.md)。旧S/外置驱动工程基线和其他五宏保留；S RTL三文件SHA完全保持，R保留并由并行任务修改。新增788个BUF_X32归属S内部M1–M10，无新增寄存器或协议拍，最后必须从实际最终ODB重新核对，不能假定脚本插入就会保留。

source117 (a9863af6244ab671821683a78ea13ef4d97faee3)四次尝试因无连接的$scopeinfo被误计为未映射逻辑，在任何物理命令前失败。source118 (c3aa022605996cec2c514fb2ddeda491df2b9425)只忽略经核对无连接的层次注释，任何实际未映射逻辑仍拒绝。1180–1183四个候选实际进入placement及时序修复，密度/hold修复裕量分别0.42/0、0.40/0.005、0.45/0、0.42/0.015，各16核/128GiB预测；捕获时均未完成最终P&R，不宣布300MHz通过。

source119 (0a5f2bb4ca916ed9a55cbd2f471bb5f132a649dc)增加独立S公开端口oracle及seal/physical/drc/function/formal/deliver入口。source120 (cd3c892430d1630fb7042860fd403c602492aa83)将新版S的全部新四门、788个实际最终输出级证明绑定进S替换/固定PG/实际拓扑链。S输出旁Link8不再作为最终方案，其他来源必要Link8保留；新图重抽取实际移除数。原图重新核对S旁实际100个Link8，不能用ceil(787/8)=99估计代替实际分组。当前尚未生成新合格图，235实例仅是若其他分组完全保持时的算术预测，不能宣布实际实例数或资格。

## 独立RTL预检已经执行

source120 s-internal-rtl-smoke-02在Slurm job95204运行。三个初态全部通过且结果相同：124440检查、46581周期、523描述符、9545窄口请求、内部RAM访问0。完整1024地址通过公开窄口初始化/随机顺序读取及复位保留检查；512合法参数组合、边界/非法尺寸/地址/对齐、复用B、A/B独立背压、真实共享端口竞争、完成保持和活动供数复位中断。lint严格通过。编译输入0.066MB/4modules，生成0.133MB C++，Verilator报告分配48.504MB，这不是全进程峰值RSS。

独立实际最终单元功能仍须重跑同oracle，严格LEC依赖同一个通过功能门的完整物理导出视图。四个候选的全部原生四门/交付已追加不可变规格，source120另接S原生交付、显式替换、固定PG/全DRC、独立物理与新鲜RC/时序及PG交付；排队不等于完成。

## 内存与动态补位

原128GiB预检在node25被现有内存准入挡住：已有任务加待执行任务合计预测480GiB，乘1.2加16GiB保护量为592GiB，超过约466GiB可用内存；不是单个预检预测480GiB。所有旧pending/active/completed规格保留。额外单独的小RTL预检仅处理三份紧凑RTL，不处理59MB/约48万cell映射网表、不综合/P&R，16GiB预测加同一保护规则实际准入并通过；与大网表门保持不同资源依据。原128GiB预检仍在原队列中等待，未被伪造成功或改写。

只取消新增已核验本人的step95204.107，为S预检释放槽；同摆放保留95099.53/95155.74/95119.42实际运行搜索，UID/父任务名/完整命令/ready替代规格和取消回执已保存。它是未完成的旧外置S驱动搜索，不叫物理失败；未改父分配、原日志/规格或其他任务。四个之前为S P&R释放的step同样保留证据。八自有节点继续c96 6×16、c64 4×16动态补位；具体内存/依赖准入据实记录。

## 旧组合工程基线的新增证据

source114的router-weight-regression-09实际120例及密集pin/有限预算/48边紧预算与拒绝对照通过。source115的实际native SPEF ground-cap+乐观上层线长必要界审计40摆放完成：281(3)、302(1)、305(1)、308(1)、312(1)、1062(1)、1063(1)在high失败，其余low/base均0；1060/1061/1064–1067三角点均0。已独立核对当时所有活跃路由无被拒绝父摆放；这些通过只是未触犯必要条件，不能转成实际路由/RC/时序通过。source116只准备坐标平移与外围留白软件/测试，未启动halo实验，新用户S决定后未扩展此方向。

旧335实例实际最终单元三程序/原生RC和21类叶六文件证据保留。新S及新组合仍需最终P&R、全部门、实际最终单元三程序、M11/M12完整几何/PG/low-base-high分布RC/300MHz和源绑定六文件/版图；本checkpoint不是任务完成或系统验收声明。
