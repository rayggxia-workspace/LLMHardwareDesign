Refs #289

将 A/B 两套布线所用的 340 个非 P 输出升级到 X8 驱动，覆盖 C153、U153、G33、S1。本轮验收使用实际叶宏和父 block，保持原名义频率、信号端口形状、宏位置和逐周期可见行为。

G 和 S 两个叶宏已验收。集成新版 S 的 F 在 Nangate45 TT、名义 300 MHz 和 0.1 ns 时钟不确定度下，setup 裕量 +0.221605405 ns，hold 裕量 +0.002453537 ns。原版全量 FreePDK45 DRC、时序和电气检查零违例，PG、功能、状态和接口几何通过。F 的 native checker 中有 40 个原样历史标记和 4 个经过逐项验证的同网宏端口接触标记。回执位于 `work/YUZE-LU/289/audit/evidence/F/accepted-parent.json`。

U 已通过 block 后端验收。153 个目标输出逐个核对为 `BUF_X8`。在 Nangate45 TT、250 MHz、0.1 ns 时钟不确定度和目标输出 50 fF 下，setup 裕量 +0.078050904 ns，hold 裕量 +0.003471112 ns。setup、hold、电容、slew、fanout 和原版全量 FreePDK45 DRC 均为零违例。两条电源轨连通，功能等价、状态和控制、信号端口和宏几何、Liberty/LEF 重载以及父级抽象的实际 cut 覆盖均已验证。SPEF 从等形 DEF 副本提取，117,231 条信号网通过提取前后的材料比较。签收 GDS 与全量规则验证输入逐字节一致。回执位于 `work/YUZE-LU/289/audit/evidence/U/accepted-parent.json`。

C 仍在收敛。缓存地址在原分配边沿生成，保持原逐周期接口行为。两态归纳、实际综合映射、综合到 CTS 的数据/状态及独立控制证明已通过。119845 两个详细布线候选运行中，119879 验证共享算术能否降低分配地址网的扇出和布线压力。最终物理网表、提取时序、电学和完整规则仍待验收。

大文件保存在 `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117`，源哈希、脚本、失败记录和验收回执在 `work/YUZE-LU/289/`。交付范围为 TT 单角的叶宏和 block 后端，A/B 顶层实际 RC/STA 另行验证。PR 保持草稿，Issue 保持 in_progress。

项目协作规则版本为 rayggxia-project-collab 1.0.0。负责人 YUZE-LU，审查人待指定。管理登记 PR5 待处理，Projects 缺少 board 配置，状态待同步。项目结构检查 `python scripts/check_project.py` 已通过。
