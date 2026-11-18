Refs #289

将 A/B 两套布线所用的 340 个非 P 输出升级到 X8 驱动，覆盖 C153、U153、G33、S1。本轮验收使用实际叶宏和父 block，保持原名义频率、信号端口形状、宏位置和逐周期可见行为。

G 和 S 两个叶宏已验收。集成新版 S 的 F 在 Nangate45 TT、名义 300 MHz 和 0.1 ns 时钟不确定度下，setup 裕量 +0.221605405 ns，hold 裕量 +0.002453537 ns。原版全量 FreePDK45 DRC、时序和电气检查零违例，PG、功能、状态和接口几何通过。F 的 native checker 中有 40 个原样历史标记和 4 个经过逐项验证的同网宏端口接触标记。回执位于 `work/YUZE-LU/289/audit/evidence/F/accepted-parent.json`。

U 已通过 block 后端验收。153 个目标输出逐个核对为 `BUF_X8`。在 Nangate45 TT、250 MHz、0.1 ns 时钟不确定度和目标输出 50 fF 下，setup 裕量 +0.078050904 ns，hold 裕量 +0.003471112 ns。setup、hold、电容、slew、fanout 和原版全量 FreePDK45 DRC 均为零违例。两条电源轨连通，功能等价、状态和控制、信号端口和宏几何、Liberty/LEF 重载以及父级抽象的实际 cut 覆盖均已验证。SPEF 从等形 DEF 副本提取，117,231 条信号网通过提取前后的材料比较。签收 GDS 与全量规则验证输入逐字节一致。回执位于 `work/YUZE-LU/289/audit/evidence/U/accepted-parent.json`。

C43实际四个不同方案120292已全部完成详细布线，各自setup/hold/电容/slew/fanout均零违例。选用实际setup裕量最大的plan0：TT250MHz、0.1ns uncertainty、153个目标输出50fF条件下setup +6.340040ps、hold +1.990130ps，原约束未放松。最终GDS SHA256为11ed17a55e077a71217667ae6f7e2bb7dbb07d5af22e52450d159d1de4b0bbe9。

该最终源的278701条网络提取前后全层材料一致、153个C驱动BUF_X8、固定信号引脚/宏/外形、无缓存PG双轨、聚焦上层金属与天线、Liberty/LEF及父级cut覆盖均通过。实际ODB导出的最终网表2b74fbc9…与保存文件逐字节一致，120296完成该实际网表的数据/21095状态及clock/reset/control证明；原RTL至综合边界采用机器核验的有限/通用证明和明确列出的人工组合证明，不声称全模块RTL SAT。两方案340/340目标输出已独立逐端口确认唯一BUF_X8（C153/U153/G33/S1；A306/B340）。

C尚未最终后端验收。120303正在对同一个最终GDS执行完整未修改原版FreePDK45规则；原生checker有222个逐项证明为同网连续材料的M2/M3 spacing标记，并非空报告。还须完整原版报告实际零项、root精确native/PG裁定及最终冻结release。PG相对原CTS的230旧记录移除/140新增已追溯至合格v16/C35基线，当前最终边界复核通过。U/G/S/F已验收源保持冻结。

当前证据见work/YUZE-LU/289/audit/C43-ACTUAL-STATUS.md及C43-pending-evidence/，已推送commit80da921f8。PR保持草稿，Issue in_progress；A/B实际顶层RC/STA和多PVT仍在后续范围。

大文件保存在 `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117`，源哈希、脚本、失败记录和验收回执在 `work/YUZE-LU/289/`。交付范围为 TT 单角的叶宏和 block 后端，A/B 顶层实际 RC/STA 另行验证。PR 保持草稿，Issue 保持 in_progress。

项目协作规则版本为 rayggxia-project-collab 1.0.0。负责人 YUZE-LU，审查人待指定。管理登记 PR5 待处理，Projects 缺少 board 配置，状态待同步。项目结构检查 `python scripts/check_project.py` 已通过。
