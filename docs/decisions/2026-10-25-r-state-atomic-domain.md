# Issue99：R 状态的数值域与物理存储边界

决定：将完整head的状态单位、range guard、统一重编码、N归约和原子发布保留为R同一逻辑责任域；实现可以Dtile，但tile不能独立重标/发布。以本轮真实D128×N256/S32、72连续RTL与2真实checkpoint rawgate证据支持，详见[报告](../experiments/issue-99-r-state.md)。

第一版使用单16KiB128bit1RW、一个共享S32服务和显式1MiB外部窗口；Dtile1便于验收，不作为吞吐最优策略。完整head128KiB状态以及trial/proposal/shadow绝不免费归入M/V512B帧或既有16KiB。复位前已接受写必须排空，consumer accept后不可取消，恢复实际descriptor。128bit外部原子写是fabric义务，若不能满足需shadow descriptor+最终pointer另计成本。

尚未决定：R/S物理合并、与M/V同时执行的容量/仲裁、32head共同提交域、完整4096norm接入和目标工艺时序。优先以同精度/资源比较重复读与state流量优化，再做整合。现有41,708.534µm²仅研究库logic面积，不是最终R宏面积或可用时序。
