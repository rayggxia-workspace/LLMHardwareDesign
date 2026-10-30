# V 基础版的实测驱动修复

2026-10-28 02:31 CST, Refs #121 / PR #122。只修同一基础版，不新增裕量变体。

原203完成P&R后的独立210物理检查发现7处max-cap、1处max-slew违规；setup/hold、精确接点、RC、PG、连通均通过。不能通过改阈值、删端点或复用旧源资格消除问题。

212只读诊断证明七个缓冲器都存在于封存GRT和final。214在可丢弃GRT副本验证原生`swapMaster`，逐实例核所有ITerm名称/连接不变，原源SHA不变，并从真实Liberty核目标BUF容量至少为原实测负载1.2倍：BUF_X1→X4/X2，BUF_X2→X4，BUF_X4→X8。此比例只用于此次驱动选择，不构成新裕量宏。

214实际修复在合法化后追加`repair_timing_helper`时被GRT-0232拥塞拒绝，没有进入详细布线；失败不覆盖。215去掉额外时序优化和重复合法化，执行原生替换→详细合法化/check→增量GRT→详细布线→普通final/RCX。原RTL、1210µm外框、M10接点、10ns/I/O/负载/不确定度和所有最终验收限制不变；不能把不再追加一次优化解释为跳过最终时序检查。

215/92511在node17实际进入详细布线。新receiver默认V源215，原203显式original只用于诊断/历史；新ODB必须通过全部时序/电气/RC/PG/连接、完整原生/GDS DRC、三初态最终网表功能和严格LEC，formal必须绑定确切function回执，然后才生成交付。当前还未通过这些最终门。

证据：[214探针/真实失败和215运行实录](../../work/YUZE-LU/121/results/v-drive-repair-023019/index.json)、[215同源队列](../../work/YUZE-LU/121/node-queue-215.json)、[提交清单](../../work/YUZE-LU/121/stage211-manifest.json)。所有原始大数据仍位于授权服务器Issue121目录，仓库仅保存源码与小型回执。
