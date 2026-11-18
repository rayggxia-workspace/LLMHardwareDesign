Refs #289

将 A/B 两套布线所用的 340 个非 P 输出升级到 X8 驱动，覆盖 C153、U153、G33、S1。本轮验收使用实际叶宏和父 block，保持原名义频率、信号端口形状、宏位置和逐周期可见行为。

G 和 S 两个叶宏已验收。集成新版 S 的 F 在 Nangate45 TT、名义 300 MHz 和 0.1 ns 时钟不确定度下，setup 裕量 +0.221605405 ns，hold 裕量 +0.002453537 ns。原版全量 FreePDK45 DRC、时序和电气检查零违例，PG、功能、状态和接口几何通过。F 的 native checker 中有 40 个原样历史标记和 4 个经过逐项验证的同网宏端口接触标记。回执位于 `work/YUZE-LU/289/audit/evidence/F/accepted-parent.json`。

U 已通过 block 后端验收。153 个目标输出逐个核对为 `BUF_X8`。在 Nangate45 TT、250 MHz、0.1 ns 时钟不确定度和目标输出 50 fF 下，setup 裕量 +0.078050904 ns，hold 裕量 +0.003471112 ns。setup、hold、电容、slew、fanout 和原版全量 FreePDK45 DRC 均为零违例。两条电源轨连通，功能等价、状态和控制、信号端口和宏几何、Liberty/LEF 重载以及父级抽象的实际 cut 覆盖均已验证。SPEF 从等形 DEF 副本提取，117,231 条信号网通过提取前后的材料比较。签收 GDS 与全量规则验证输入逐字节一致。回执位于 `work/YUZE-LU/289/audit/evidence/U/accepted-parent.json`。

C40六路实际详细布线120273全部完成，最终原生路由报告0，ODB/DEF/V/SDC逐字节相同，因此只对seed0作独立后续评估。只移植一条已有实际M9时钟线net73798并重新提取RC的120281结果：setup7、WNS−43.646421ps；hold/电容/slew/fanout均0、WHS+1.400824ps，两条PG无缓存连通通过。其余网络、实例、信号/电源引脚及逻辑保持精确一致。C尚未后端验收，不能据此签收250MHz或A/B实际顶层长线。

余下7条均为C内部loader路径：两条pd、五条cached_addr，与排除的P block无关。实际C40 common的21095状态、数据及控制完整等价证明120275通过；实际最终ODB新导出的V与保存V逐字节相同120280，因不同于common V，120282正在单独重证明。120277已完成显式or_k=1的六路实际布线对照；120279继续31条实际冲突信号网的邻域重布。120283/120286仅在完成提取的实际C40 RC上作限定组合尺寸规划，其结果必须实际合法化、重布、重新提取并复验。完整原版最终GDS检查、最终视图和冻结release仍待，不放松原频率、负载、IO/uncertainty或加入时序例外。

PG边界的230旧形状移除/140新增形状已由v16实际PDN谱系、260354条电源材料、实际GDS全覆盖和双轨检查独立核实；这一工程基线批准不替代最终候选PG/GDS检查。当前证据与脚本见 `work/YUZE-LU/289/audit/C40-ACTUAL-STATUS.md`，已推送commit `0f814e89b1a6a105b0f7dd201070548d2bad25ac`。U/F已签收源保持冻结，PR草稿、Issue in_progress。

大文件保存在 `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117`，源哈希、脚本、失败记录和验收回执在 `work/YUZE-LU/289/`。交付范围为 TT 单角的叶宏和 block 后端，A/B 顶层实际 RC/STA 另行验证。PR 保持草稿，Issue 保持 in_progress。

项目协作规则版本为 rayggxia-project-collab 1.0.0。负责人 YUZE-LU，审查人待指定。管理登记 PR5 待处理，Projects 缺少 board 配置，状态待同步。项目结构检查 `python scripts/check_project.py` 已通过。
