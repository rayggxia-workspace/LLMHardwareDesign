# R范围协议、有限缓冲与V/R制造边界的取舍

2026-10-24，Issue68 / PR69，状态：有实证支撑的下一轮候选，待审查。承接Block v2及Issue66，不替换原失败/精度条件。

选择因果guard-rescale作为继续研究的R范围协议：当前proposal失败才重编码旧提交态，head单位逐次coarsen、逐次RNE、完整重试同token，state/output/units/epoch/version共同发布。static_guard在固定旧窗第4token停止；S32两次重定标完整256步消除193次sat，但S16误差略退化且新32步无触发。此选择不是全生命周期或模型质量验收。

保留M/V/A/R/S/D逻辑模板；R先保持逻辑owner/反馈/事务闭包，V/R算术共享或独立制造仍未定。下一轮条件服务以tile16、R24KiB活动槽、本地old/new+aux、V16KiB、相同8总S8向量lane/两context/单SFU、S8×32KiB及有限EXT为工作基线，保留tile32/S侧shadow作为对照。理由是两真实任务各56配置、双轮与224份唯一完整witness独立验算中，tile32额外占16KiB S4且增加线上流量；此比较同时改变tile与shadow归属，不独立证明其中一个因素。shared8较快来自发射/池化差异，同后缀shared/split的48轨迹对照每套均0差，不能据此发明合宏/拆宏PPA收益。

制造前至少要保留：完整K归约及宽guard/RNE能力、未发布新代页与失败试算页的有限存放、从新state读出后全V屏障、单位/epoch/version的共同发布及异常/背压路径。产品再决定R/V绑定、S页/银行归属和既有端点的互联；不得事后添加免费端口、整状态SRAM或第二SFU。原位更新没有相同abort恢复证明，排除主排名。

量化元数据不是附注：完整H2560 mixed sum+units为25.6KB；norm源打包、5120B单位预扫、二读或spill、gamma与新A8都必须经过有限端口。R两次重定标外部RW262144B之外，fulltrial clone另需外部RW524288B，失败/接受重试与各级中转还要另记。不能把外部字节、SRAM字节和线上字节相加称同一种通信量。

下一步只验证会改变结论的条件：①独立初态/校准生命周期中的反复重定标，连同q/k norm、gate、SiLU/GatedNorm真实整数后继和质量预算；②校准宽乘/checked merge、SFU与1RW/FIFO背压，并纳入同M阵列复用的合法优化基线；③固定相同发射粒度、算术、恢复语义及真实端点，比较实际布局/时序/能耗。当前norm32:R256比例是独立竞争流，不是整模型；M只执行相同有界代理，不能把本图极低M占用或R主导外推到LLM。

[完整报告](../experiments/issue-68-range-service.md)与[索引](../../project/experiments/range_service/results/issue-68/index.json)保存实际源码、命令、条件、接收和SHA。全模型质量、RTL/布线/时序/PPA及端到端收益未执行；Phi封存、无新增模型。Issue55/63由原成员负责，不接管其工程。
