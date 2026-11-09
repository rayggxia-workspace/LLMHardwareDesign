# Issue247第三轮：大矩阵候选独立备份

2026-11-10，Asia/Shanghai；Melodydt；Refs Issue247 / PR243。本决策仅记录候选范围和备份，不表示服务器验证或性能已经通过。

第二轮主条件结果3.66958239533 token/s，共享口3.37834376557；Dot224.101536667ms，占82.2359%。下一步检验PR241的S32/S96 K16算术候选与真实四bank供数，而不能把叶核II1当整个P服务。原评价条件300MHz、2P/1U、17.1GB/s、16KiB及共享/理想端口两层保留。

候选复用PR241@189e43c77a6277955c1be54281b0d6b0b0d55c1f的K16/N8/ROWS8叶核，新增有限供数wrapper。它含128个32×9乘法器、8棵16输入归约树、八组八列S96部分和。源码声明口径下，leaf加单buffer wrapper为16,748bit（2,093.5B），双buffer为18,906bit（2,363.25B）；新增一个packet buffer为2,158bit（269.75B），包含256B数据及元数据。组合算术、转置、选择、SRAM及物理辅助不含于位数。

这属于明显增加算术资源的候选，按用户要求额外备份：

- 完整第二轮远端基线分支task/247-pre-m-area-r2-ed9f5ee6，固定ed9f5ee63ceaeb260eb611f10d569ec8904a81c6，已读回核验。
- 初版候选独立归档包含七文件及其SHA，位于work/Melodydt/247/speed-iterations/backups/round3-initial-candidate.tar.gz.b64。原tar.gz SHA为9150111291360ce468c336549a70c4a4b9b3eb901fa33a4fce302bd0ef1137e2；旁边round3-index.json列出成员。该初版不可变，后续缺陷修复不能覆盖它。
- 正式冻结测试源码提交后再创建候选远端分支，实际分支/commit和读回证据记入第三轮实施报告；在尚未完成之前不称已创建。

独立实现保留于project/experiments/rtl_iterations/round3，生产P16及第一、二轮生产源不改变。新wrapper接真实block_feed_s16k_sram，仍四个256×128 1RW宏、16KiB；每拍至多一次wide64B读或narrow16B写，两条读metadata、八条completion预约。单/双buffer同FSM比较；source在leaf接受后立即释放，不能人为减慢单buffer。reserved K允许有界预取，committed K只在真实计算提交推进；最终两次写ACK及完成退休前不释放context/output租约。

尚非完整pu_p_group原生ABI/DMA/DDR集成。旧模型接入必须逐请求占用S日历，移除被替换的完整旧本地服务及重复结果store，保留外层DDR、两A bank/引用、输出DMA和写合并。合格范围为staticW8/r1/S32/N8/K16 packet、旧K256对应16包；其他格式和prefill明确回退。模型控制需先用实际RTL输入逐周期复核，不猜费用。

综合面积、STA、P&R和功耗未执行，位数不能冒充mm²，也不继承300MHz物理资格。若新服务在旧体系中退化，则保留独立方案并继续使用第二轮较快版本。R3完成后根据实际瓶颈再选R4，不提前实施1KiB A缓存或其他方案。

GitHub第二轮head ed9f5ee6的CI run42679340867为failure；validate job129369322196无steps且runner_id=0，日志读取404 BlobNotFound，具体原因待管理员核实。未改workflow绕过；服务器验证与线上CI分别记录。
