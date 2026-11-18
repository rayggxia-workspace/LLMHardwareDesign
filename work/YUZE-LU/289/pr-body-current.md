Refs #289

将 A/B 两套布线所用的 340 个非 P 输出升级到 X8 驱动，覆盖 C153、U153、G33、S1。本轮验收使用实际叶宏和父 block，保持原名义频率、信号端口形状、宏位置和逐周期可见行为。

G 和 S 两个叶宏已验收。集成新版 S 的 F 在 Nangate45 TT、名义 300 MHz 和 0.1 ns 时钟不确定度下，setup 裕量 +0.221605405 ns，hold 裕量 +0.002453537 ns。原版全量 FreePDK45 DRC、时序和电气检查零违例，PG、功能、状态和接口几何通过。F 的 native checker 中有 40 个原样历史标记和 4 个经过逐项验证的同网宏端口接触标记。回执位于 `work/YUZE-LU/289/audit/evidence/F/accepted-parent.json`。

U 已通过 block 后端验收。153 个目标输出逐个核对为 `BUF_X8`。在 Nangate45 TT、250 MHz、0.1 ns 时钟不确定度和目标输出 50 fF 下，setup 裕量 +0.078050904 ns，hold 裕量 +0.003471112 ns。setup、hold、电容、slew、fanout 和原版全量 FreePDK45 DRC 均为零违例。两条电源轨连通，功能等价、状态和控制、信号端口和宏几何、Liberty/LEF 重载以及父级抽象的实际 cut 覆盖均已验证。SPEF 从等形 DEF 副本提取，117,231 条信号网通过提取前后的材料比较。签收 GDS 与全量规则验证输入逐字节一致。回执位于 `work/YUZE-LU/289/audit/evidence/U/accepted-parent.json`。

C 已完成六路实际详细布线对照中的五路，当前选用 i8/h50。153 个目标输出均为 BUF_X8，信号端口、宏位置和 die 固定。实际提取后的 setup/hold 为 100/117 项违例，最差 −116.966/−48.911 ps，电容27项、slew0；原生路由报告4项，独立原规则上层24项、天线1项，尚未验收。静态59项尺寸合并重测为 setup97、hold141、电容2项，但尚未将该结果计作实际重布线通过。正在修复宏边界、定向 hold 和绕 R 宏的毫米级长线（单节点6×8CPU局部中继对照120144）。S4局部补片和34种新增/替换标准单元的隔离全规则 fixture已通过各自限定范围验证；完整最终 C 规则仍待验收。

缓存地址优化的523/523分区通用等价证明通过；实际综合到 i8/h50 legalized 数据/21095状态/控制证明120098通过，无未匹配边界。最终路由功能绑定、时序、电气、完整原规则及视图仍待验收。失败试验保留，不更改时钟/IO预算或引入例外路径。最新中间证据见 `work/YUZE-LU/289/audit/C-v28-ACTUAL-STATUS.md`。

大文件保存在 `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117`，源哈希、脚本、失败记录和验收回执在 `work/YUZE-LU/289/`。交付范围为 TT 单角的叶宏和 block 后端，A/B 顶层实际 RC/STA 另行验证。PR 保持草稿，Issue 保持 in_progress。

项目协作规则版本为 rayggxia-project-collab 1.0.0。负责人 YUZE-LU，审查人待指定。管理登记 PR5 待处理，Projects 缺少 board 配置，状态待同步。项目结构检查 `python scripts/check_project.py` 已通过。
