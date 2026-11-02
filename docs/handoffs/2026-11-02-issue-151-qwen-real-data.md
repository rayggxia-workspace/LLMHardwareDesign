# Issue151真实Qwen层数据、数值和RTL接续

rayggxia-workspace/LLMHardwareDesign；负责人Melodydt；Issue151/PR152，task/151-six-connection-study→task/143-seven-block-v2。输入71c819c2，取数源92989582，数值源d0c40f57，RTL源f7fc7614；最终资料commit由PR头/本地delivery-receipt读取。新资料待审查、未合main、不done。

本地隔离API包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/qwen-numeric-71c819c/integrated，无.git/HEAD/index/暂存；原44RTL/TB/include字节不变，原根/其他会话未覆盖。源码已在任务远端，未合并。PDF在local-share-2026-11-02-v2本地另存、不上传Git。

服务器yuzelu@10.129.166.172，仅本人/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/qwen-numeric-71c819c-20261102：data01含官方11tensor/14embed和实际SHA；n01/95247（1:02）与q02/95248（1:49）均COMPLETED0:0/node1/c64/8CPU，无在跑作业。数值源input-n01，RTL input-q02，日志slurm及runs各目录；原始参数/流/构建留服务器，39文本SHA和全部输出重核见work/Melodydt/151/qnum/evidence-index.json。完整模型文件SHA未实算，不能把expected写成verified。

实际结果：4固定piece前缀小诊断，cal/eval各8192元素；RTL4个完整F行×7标记、4×9MiBactual SHA。独立checker8fixture全N/G/E、全参数量化与192sampled fullK dots。旧回归/官方框架/代表性质量/完整A/MEM/永久金属绑定/物理未执行；W9的平均误差改善伴随更大max与82weightclip，不接受产品精度。

恢复第一步：重新读最新Issue/PR/本交接，核验本人身份/lease、server两job终态与SHA，读docs/QWEN_LAYER0_NUMERIC_RTL_REPORT.md。优先约定代表性cal/eval和多目标误差门、同revision官方框架校对；复核无clip W8。并按docs/QWEN3_SQ2_ATTENTION_PLAN.md实现真实A的Tspool/原残差lineage、split-half重排、head循环、context/Wo及参数/系数端点，先验证再L5。维护原24GAP，不扩称28层模型通过。

登记PR5待合并；无board.json/Projects条目工具，看板unverified/同步pending，需要确认看板/受众、添加/复用Issue151、Project ID/Status/Priority并读回，处理人待指定。外部审查待指定，非已证实权限拒绝。纯本地PDF更新不等于新增线上文件上传。
