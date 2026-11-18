Refs #289

将 A/B 两套布线所用的 340 个非 P 输出升级到 X8 驱动，覆盖 C153、U153、G33、S1。本轮验收使用实际叶宏和父 block，保持原名义频率、信号端口形状、宏位置和逐周期可见行为。

G 和 S 两个叶宏已验收。集成新版 S 的 F 在 Nangate45 TT、名义 300 MHz 和 0.1 ns 时钟不确定度下，setup 裕量 +0.221605405 ns，hold 裕量 +0.002453537 ns。原版全量 FreePDK45 DRC、时序和电气检查零违例，PG、功能、状态和接口几何通过。F 的 native checker 中有 40 个原样历史标记和 4 个经过逐项验证的同网宏端口接触标记。回执位于 `work/YUZE-LU/289/audit/evidence/F/accepted-parent.json`。

U 已通过 block 后端验收。153 个目标输出逐个核对为 `BUF_X8`。在 Nangate45 TT、250 MHz、0.1 ns 时钟不确定度和目标输出 50 fF 下，setup 裕量 +0.078050904 ns，hold 裕量 +0.003471112 ns。setup、hold、电容、slew、fanout 和原版全量 FreePDK45 DRC 均为零违例。两条电源轨连通，功能等价、状态和控制、信号端口和宏几何、Liberty/LEF 重载以及父级抽象的实际 cut 覆盖均已验证。SPEF 从等形 DEF 副本提取，117,231 条信号网通过提取前后的材料比较。签收 GDS 与全量规则验证输入逐字节一致。回执位于 `work/YUZE-LU/289/audit/evidence/U/accepted-parent.json`。

C35六个合并版本均完成实际详细布线（120194及两路AP恢复120199）。当前独立核验i8/h100/pnone：153个BUF_X8，信号端口、宏位置与die固定；原生路由报告0，实际setup90项/−105.212286ps、hold19项/−20.839553ps、电容1项、slew0，尚未通过后端。独立120216证明278621条网络提取前后的金属与过孔材料一致；原规则天线120215为0，上层仍有3项对应两处几何位置，正在修复。

C35的230个旧PG形状移除/140个新增形状已追溯至v16实际PDN。260354条完整电源材料与140个BPin跨v16、归一化源和C35完全相同，同名材料/实际GDS全覆盖、反rail隔离及两轨无缓存连通均通过。root仅批准该PG工程基线，整体后端仍待验收。证据位于audit/C-v35-independent-v1、C-v35-pg-boundary-v3和C-v35-pg-origin-v1。

缓存主版本523/523通用分区证明通过；实际i8h100/pmid200 legalized网表的21095状态、数据和控制严格等价120196通过。最终候选仍需逐字节绑定或重新证明。mem_wr_address[63]37项组合尺寸、cache19项尺寸和局部中继已形成限定范围规划证据，正在合入实际ECO；剩余19项hold及1项电容一并修复。独立测试真实时钟长线换层布线，不改变名义频率、SDC预算或添加例外。最终完整原规则及模型/STA验收仍待完成。U/F已签收源保持冻结，PR仍草稿、Issue仍in_progress。

大文件保存在 `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117`，源哈希、脚本、失败记录和验收回执在 `work/YUZE-LU/289/`。交付范围为 TT 单角的叶宏和 block 后端，A/B 顶层实际 RC/STA 另行验证。PR 保持草稿，Issue 保持 in_progress。

项目协作规则版本为 rayggxia-project-collab 1.0.0。负责人 YUZE-LU，审查人待指定。管理登记 PR5 待处理，Projects 缺少 board 配置，状态待同步。项目结构检查 `python scripts/check_project.py` 已通过。
