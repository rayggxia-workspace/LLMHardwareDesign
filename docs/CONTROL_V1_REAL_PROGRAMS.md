# 当前真实程序证据：453接线、473事件与480独立审计

更新：2026-11-04T07:48:21+08:00。当前采用453图/345物理实例/23类完整最终PG单元，独立源绑定见[472实际审计](../work/YUZE-LU/162/continuation-proof-55/final-program-supplement/r256-padding-final-function-audit-472/receipt.json)。[当前13文件交付索引](../work/YUZE-LU/162/program-event-delivery-padding453-current536/index.json)绑定473实际三初态事件执行与480独立重放/六项篡改拒绝：每次8程序、680884检查、217396周期、CPU张量搬运0，9318外部握手/主机程序事件、18调用、14案例。事件标记范围与原编译资产绑定限制见该索引及[Checkpoint57](../work/YUZE-LU/162/continuation-checkpoint-57.md)。不是逐周期波形，也不是八个完整模型的端到端执行。

下表八程序的功能及预期数值不变；其早期359/392和422链接仅保留历史，当前验收采用上述472/473/480绑定，不从旧图继承。所有状态宿主见[当前453归属绑定](../work/YUZE-LU/162/state-ownership-candidate453-binding.json)。程序通过不替代仍在执行的M11/M12、几何/PG/三档RC/300MHz/联合物理验收；最新进度见[Checkpoint63](../work/YUZE-LU/162/continuation-checkpoint-63.md)。

# 八个真实组合程序与执行证据

Refs #162 / PR #163，2026-11-04，中国标准时间。当前reset53场景359使用23类最终PG单元视图、345个固定物理实例，包含实际R256。当前完成情况见[八程序独立源绑定复核](../work/YUZE-LU/162/continuation-proof-48/r256-reset53-final-function-audit-392/receipt.json)及[原始最终功能回执](../work/YUZE-LU/162/continuation-proof-48/r256-composition-359/function/receipt.json)，三初态原始结果在同一目录。旧317摘要及Checkpoint45对应reset28，保留为历史，未用来替代当前连接验收。

| 程序 | 硬件执行的代表路径及顺序 | 实际检查 |
|---|---|---|
| GEMM | 外存→D→S；S供给M，M计算、结果写S，再由D写外存 | 8×8×8输入单位值，64个S32输出均8；S读16/写12 |
| 多遍Softmax | D/S装载，N对三个4096元素分块做统计与回放，D/S保存并重读临时结果 | 所有实际外存S16结果为1，跨块和多遍握手完整排空 |
| E/G/T尾包 | 外存→D/S→E→G→T，结果保持、提交、排空、释放，再由D写外存 | 257元素尾包，输出均8192 |
| R双状态bank | D/S装载2048字节；R完整两bank写入、读回；D/S结果写外存 | 全部512个S32值与确定性输入模式一致，覆盖所有合法状态包地址 |
| GDN→E→G→T | D/S装载R数据；R衰减、点积、误差、外积更新与读出；打包→E转换→G→T→外存 | 两个16字节包，每包前四lane10198，后四lane8192 |
| SSM | R逐元素衰减、注入更新、C点积读出及skip；D/S结果写外存 | 八个S32结果均57344 |
| 四抽头卷积 | D/S装载参数和历史；R四抽头卷积、有限输出缓冲；D/S结果写外存 | 八个S32结果均10240 |
| M/N→S→R | M格式化S32结果成为R状态；N Softmax的Q1.14结果成为R query，再执行R更新/读出 | 八个外存S32结果均8，计算与搬运均由实际RTL/最终单元完成 |

三次实际初始化（initial1/seed162、initial2/seed162、initial2/seed163）均通过，每次680,884项检查、217,396周期、8个真实组合，CPU张量搬运0。另验证5种R描述符错误及endpoint8拒绝，必须向C返回错误而不发起外存传输。硬件程序与描述符顺序由实际test_system.cpp给出，SHA绑定于运行回执；主机仅准备外存初值、配置程序/参数及检查最终外存，执行期间没有用测试软件替代D/S/R搬运或算术。

当前三初态另已完成实际事件执行及[422独立审计](../work/YUZE-LU/162/continuation-proof-51/r256-current-program-event-audit-422/receipt.json)：每次9318事件、18程序调用、14案例，原数值检查与周期不变；49152已知读字节、52098写字节逐项核对，六份完整篡改轨迹全部拒绝。[完整三份JSONL及13文件交付索引](../work/YUZE-LU/162/program-event-delivery-current433/index.json)绑定原完整最终功能视图与状态归属。记录实际外部AR/R/AW/W/B、主机计划和排空完成/错误状态；program_started是主机启动寄存器写返回，program_end是排空后状态采样，不是内部指令/完成边沿。原复用编译资产当前SHA已记录，未宣称原编译时资产预绑定。这些是实际程序及外部事件证据，不是逐周期波形文件。已有test_traces.cpp中的八模型profile仅验证C指令/描述符容量和任务传输，使用oracle完成返回；不能把它描述为八个整模型端到端数值执行。上表八程序与八模型profile的范围分别保留。

全部有状态逻辑物理宿主见[345实例逐项索引](../work/YUZE-LU/162/state-ownership-current396.json)及[CONTROL_R256_INTEGRATION](CONTROL_R256_INTEGRATION.md)。本轮完整原生RC诊断setup +0.010286ns、hold +0.000194ns，实际端点/注释覆盖、setup/hold/电气计数均通过；这仍是零上层RC诊断。实际M11/M12完整几何、PG及low/base/high分布RC/300MHz和联合交付仍单独验收，不能从程序通过或原生诊断通过授予物理系统资格。
