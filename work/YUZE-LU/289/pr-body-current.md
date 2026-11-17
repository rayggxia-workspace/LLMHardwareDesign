Refs #289

将 A/B 两套布线所用的非 P 输出升级为 X8 或更强，并完成叶宏及父 block 后端验证。实际范围为 C153、U153、G33、S1，共340个输出；保持原名义频率、信号端口形状、宏位置及逐周期可见行为。A/B 实际 C/U 源是尚未完成后端的 overlay CTS，本任务同时补全其后端。

已通过：G hold03、S minimal-localv4 叶宏，以及集成新 S 的 F 父 block。F 在 Nangate45 TT、名义300MHz、原0.1ns uncertainty下，setup +0.221605405ns、hold +0.002453537ns；完整原版 GDS DRC、setup/hold及电气违例均为0，PG、天线、功能等价及状态/控制保持通过。F native checker含40个历史原样标记及4个逐项验证为同网宏端口接触的标记，不能称native报告为空。证据：`work/YUZE-LU/289/audit/evidence/F/accepted-parent.json`。hold仅2.454ps，不代表其他PVT角裕量。

C、U尚未验收，最新进展：

- C 在原分配边沿缓存地址，未增加可见周期。已有绑定到确切源文件的两态归纳与逐周期等价论证；实际综合映射与最终网表证明仍在运行。定点接收D分支修复的独立4CTS重载检查已达hold违例0、setup剩1条约-49ps，使用布局估算RC，不能替代最终提取结果。119751为单节点6×8核实际布线候选。
- U 的前一独立电气闭合版本通过原频率、153个X8、信号几何、PG和功能检查，但完整GDS检查仍发现天线及父层/宏邻近间距问题。已加入1897个真实宏cut障碍并修正10个冗余PG栈，实际天线诊断从1293项降至15项。119747的NDR遗漏非目标层spacing，实际读回为0并导致PG短路，该轮已拒绝。v2显式保留每层原线宽/间距并逐层断言；119754从前一PG检查通过的数据库重新以单节点6×8核合并布线，保留全部15个二极管及电气/hold修复。最终仍须完整原版规则、fresh STA和功能门全部通过。

C/U 的4ns、0.1ns uncertainty及所选输出50fF使用明确的新独立接口测试契约，未用false/multicycle例外放宽验收。这不是 A/B 顶层实际提取RC，也不证明毫米长线的系统时序。

大文件保存在 `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117`；源哈希、脚本、失败记录及验收回执在 `work/YUZE-LU/289/`。当前在线head以GitHub实际ref为准，后续本地检查点待传输核验后追加。任务未完成，PR保持草稿、Issue保持in_progress。

规则版本：rayggxia-project-collab 1.0.0。负责人YUZE-LU，审查人待指定；登记management-hub PR5 pending；缺少board配置，Projects unverified/同步pending。`python scripts/check_project.py`通过，仅检查管理结构。下一步由YUZE-LU继续C/U完整后端验证、同源宏视图导出及冻结交付。
