# 原生十层候选的结构、IO 与单位边界

Refs #121，2026-10-27 04:17 CST。原生 M1–M10 预制、新增 M11/M12 定制的授权计划不变。

## 导入必须保持精确映射逻辑

run048 的实际四节点探针拒绝了两项工具不兼容：OpenSTA 结构网表读入器不能读取 `input signed` 声明；当前 SDC 解释器没有 `remove_from_collection`。不能以重新综合或删端口绕开。run052 只清除 Yosys JSON 的 port/netname signed 元数据，保留所有单元、参数、引脚连接；结构 Verilog 重读后逐模块/逐单元检查位 ID 双射，并检出单 pin 位篡改负例。转义内部标识符做无碰撞规范化，run050 的原失败不覆盖。

## 2 fF 负载使用实际命令单位

run053 实测 Nangate45 Liberty 的 OpenSTA 命令单位为 ns/fF/kOhm/μm；`set_units` 只检查，不转换。历史准备文件的 `set_load 0.002` 实际是 0.002 fF，不能当作预算的 0.002 pF。此前没有接收任何物理 PPA。统一由 `constraints.py` 显式设置/核验原生命令单位，输出 `set_load 2`，避免改变 ORFS 原生 setRC 的单位解释。旧输入文件和失败保留。

run054 使用 run052 结构证明绑定的网表，重新生成完整 SDC。run055 四种实际 OpenROAD 导入、行/轨道与 M10 pin 坐标全部通过；单元仍未放置。C8 为493654个单元/1155430.318 μm²，T6K 为148581个/382896.360 μm²，均是真实映射面积。run056 对 STA 写回 SDC 独立接收：每个输出 2 fF，全部数据/控制输入均有驱动及 max/min 延迟，时钟/不确定度完整；C8 为1101个非时钟输入、3287个输出，T6K 为189/196。错误负载和漏输入约束的内存负例均被拒。

## 原生候选 P&R 与完整验收分离

run057 四任务为 C8/T6K × A边缘/C内部数据窗口，实际 node14–node17，各32CPU、UNLIMITED。与 node13 的映射门级并行，共五个 allocation；其余资源留给独立验收/提取资格。跨 run 共用八节点上限与提交锁，重文件复制/哈希全任务最多两个并发槽，防止并行计算挤爆共享存储。

读取固定映射结构文件，先调用 ORFS `do-1_synth` 的 OpenROAD 数据库导入，再依序 `do-floorplan/do-place/do-cts/do-route/do-finish`。不调用会触发 RTL 再综合的普通依赖链；输入独立只读复制，逐阶段核对 SHA。平台实际 TECH_LEF/RCX_RULES 必须是原生十层，布线范围实际 metal1–metal10；不关闭默认 LEC/SEC 检查。`KEEP_VARS=1` 保持手动 FOOTPRINT_TCL 在后续 IO 步骤生效。

运行成功不等于接收。还须逐个实际最终 ODB/网表/SPEF 完成全部端点 setup/hold、电气 actual≤limit、PG/连接/DRC/RC覆盖、原生层与 pin 清单、资源预算及最终网表功能验证。面积必须分别记录逻辑与 CTS/修复单元、物理填充/供电相关实体和完整 die 成本，不能用单一映射面积代替物理成本。十二层分布式提取、共同底座冻结及两产品新层互联仍未验收。

输入及历史证据位于 `work/YUZE-LU/121/results/run048`、`run050`、`run052`–`run056`；run057 的不可变提交清单为 `stage53-manifest.json`。完整原始文件留在本 Issue 获授权服务器目录，以回执 SHA 绑定。


## 04:59 CST：独立接收器与运行快照

run060/061 的 SPEF 头缺项、单位浮点表示和未使用 QN 端点失败保留。run062/063/066 在真实 DFF、Liberty、SDC、SPEF 上通过正例，并拒绝实际过载/过快时钟、连接输入缺 RC，以及四种端点报告故障。单位身份比较仅容许原生 float32 表示误差；setup/hold 仍严格非负，极小负 slack 不能四舍五入通过。只有实际连接时钟已证实、内部输出双 INF 且完整 flat/all-arcs fanout=0 时，才单独列作未使用输出；端口或寄存器输入不可豁免。

`native-receive` 另读封存最终 ODB/SDC/SPEF、完整端点与电气原生计数、每个未注释驱动的实际扇出、逐实例/PG/信号连接、原生十层、M10 pin、die 和成本。GDS 在接收器自己的输出树从最终 DEF 生成，再运行原生独立 KLayout DRC；不修改原始候选。run066 的真实未放置 DFF/断开 PG 负例已拒绝。完整候选接收器尚未运行，最终网表功能、宏模型及十二层资格仍分别必需。

原生两个 T6K 候选已进入 DRT，两个 C8 在布局优化，尚无最终结果。run067/92062 在 node18/32CPU/UNLIMITED 编译同一完整映射网表的多线程模型，两个背压模型各16线程，总预算32；没有更换 RAM 或缩减13命令回归。原 run008/91903 保留，其最初6小时时限的延长被 Slurm 拒绝，记录位于本 Issue `scheduling-amendments/job91903-unlimited-20261027.json`。新任务不继承该人工时限。本任务当前6个节点，不改变其他成员任务。
