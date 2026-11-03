# Issue151 QUALITY首切片交接

仓库rayggxia-workspace/LLMHardwareDesign，Issue151/PR152，Melodydt，task/151-six-connection-study→task/143-seven-block-v2。输入77b47e389a0aa3f6d775ea00b7870e9c7c4a573e，实跑源b18e8a5fd6f678fd3d395bedf3ff1cb5320bb737，最终资料commit按PR回执。工作D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/quality-77b47e3/integrated为隔离API部分包，无.git/HEAD/index/暂存；原54runtime和旧锁不改，不推main/不自合并。

server yuzelu@10.129.166.172，/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/quality-77b47e3-20261103。95979/zenanyan-quality/node1/c64/8CPU/r02 COMPLETED0:0/00:02:55，28官方参考/8fixture56CASE/8actualSHA。input-r02/runs/r02；日志slurm/zenanyan-quality-95979.out/.err及runs/r02/logs，结果runs/r02/results/run-receipt.json。恢复先sacct -j95979、cat结果，不覆盖旧输入/输出。95978/r01 FAILED8秒闭包错误保留；只contract补列wheel-lock，无算术/阈值/RTL变更。无本任务在跑作业，无自动监测。

54轻量原文/两轮56源出现/28当前源/55data/206generated/246outputs核验，rawbinary/weights/wheels/build只在本人服务器；证据work/Melodydt/151/quality/evidence。environment/deps是本任务离线Python target，不是系统安装。当前旧4prefix回归/FP32 A→整数F，非trained整数A→F或模型质量，旧24GAP不变。

下一Melodydt从L4-QUALITY-AF开始：先核最新PR/main/本报告，建立真实参数完整Sq2整数A及两F oracle，显式Q/K轴映射、Fin/RNE/epsilon/sat来源，比较4种误差切口；新代表性cal/holdout和产品门在结果前冻结，不复用已见eval当未见。L4未整体退出，L5通用控制/端点、D/H、MoE、MEM及共同底座物理分别验收。

用户要求每步完成后同名覆盖：D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/local-share-2026-11-02-v2/output/pdf/七宏功能岛方案交流_2026-11-02_更新版.pdf。本轮10页/14links/全页视觉QA，SHA7d00cf632e252f12d089ed63a22dc6a823ee513a548bab4b38c4e7f1fc10cbe8，索引quality/local-PDF-index.json。继续用现有refresh_share.py/current-update.json更新实际数据再同名生成/全页核验；不新建PDF版本，不推Git/发送他人。

PR开放未合并/外部审查与优先级待指定，Issue交付回in_review/非done。登记management-hub PR5 pending，实际看板unverified/同步pending（远端无board.json、无Projects item/field工具，非已证实权限拒绝）；所需配置、条目与Project ID/Status/Priority读回由待指定处理人完成。
