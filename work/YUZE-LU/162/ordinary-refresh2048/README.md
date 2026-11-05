# 默认关闭的普通树周期重布搜索候选

Issue #162 / Draft PR #163。真实全网在约55万冲突附近波动。代码会保留当前clean树，这可能固定占据绕行空间；这里只提出可验证的软件搜索候选，不认定它是全部失败主因。

新增ordinary_refresh=8/16，默认0完全走原搜索分支。只在完整全网阶段的周期边界同时撤除全部ordinary树，沿用撤除前的dirty-first顺序重新搜索；此前clean和dirty计数先共同快照。保留native树、实际landing固定所有权、历史成本、全部有限标签/物理线长预算，以及所有最终门。与其他batch或present-growth调度组合明确拒绝。没有新增硬件、状态宿主、宏、die或互联层。

本地6项Python上下文拒绝、3项CLI拒绝、3文件语法及12份native/最终文件逐字不变检查通过；最初参数草稿的一些拒绝先触及前置条件，正式v2合同使用完整合法基准参数后单独破坏条件。真实CPP编译与回归尚未执行，不能称已验收。

计划在原16CPU空槽运行18份关闭选项的旧路径/native/日志逐字回放，20个实际小图尝试（含已证明超容量负例与可进入后续轮次的pressure例），独立flood/预算/零冲突、实际clean/dirty树共同释放和非法CPP/CLI拒绝。未知失败继续定位，不删检查。测试通过之前不得投入完整组合；小图通过也不替代完整M11/M12/native-XOR/PG/low-base-high 300MHz联合验收。

现有完整候选继续运行。main六宏、S驱动、R及并行修改保留，不合并。规则rayggxia-project-collab1.0.0；登记PR5 pending；看板unverified/同步pending；审查待指定；Issue in_progress / PR Draft。
