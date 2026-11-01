# 六配置大Block采用局部端点适配与分层同步（候选）

状态：研究候选，待独立审查；Issue151/PR152，输入051fddb9a3d2cecd4b76c43d07ec8581db9402ce。

目标是同一预制有源底座支持有限产品，由M11/M12永久绑定现成程序和跨岛端点。把宏封入大Block不能消除原生命令/流/回放/状态/ACK差异。母控不逐拍调叶宏，本地控制器负责原生端点和资源生命周期。

先选择S物化/回放＋有限capture/gather/serializer，保留Sloader→M快路；按已证明数值/生命周期增加局部bypass。无需先制造49直连交叉网络。适配器先做可综合模块并单测，是否独立硬bridge宏待物理证据，不认定已存在独立bridge。

实现按W0–W11拆分原P1–P7：共同壳、双岛/MEM边界、E/G与N并行，再完整A/F；NUM提前，R与动态MoE分支分别闭合。完整F不能由无N的FFN8核替代，X不必依赖R。

代价是S访问/回放与有限holding预算，S16KiB/T6KiB不涵盖大模型工作集，实际MEM/NUM和地址/数值/状态版本必须独立接收；同资源等待图还需实际验证。本轮不改RTL、不运行仿真、不更改原阶段状态，无PPA/活性/完整profile通过声明。

依据：[连接主报告](../COARSE_BLOCK_CONNECTION_IMPLEMENTATION.md)、[实现包](../COARSE_BLOCK_SYNC_WORKPACKAGES.md)、[源码证据](../COARSE_BLOCK_EXISTING_CONNECTION_EVIDENCE.md)。
