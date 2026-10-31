# 407固定队列准入实际部署

Refs #121 / PR #122。PID3668320；代码d1aadb3ed41a1f6fe9c79280c6f0358c358dec0d、配置72a26b71（完整SHA见launch-readback.json），配置SHA3121ba019094f81c4792b7baca4475fc46ecd59fec0fd3a045e4a77bbcfb554b。24远端文件及六归档与原Git blobs核验，正反控制、实际UID/cmdline/start ticks、两轮状态读回通过。

仅替换403控制PID3589806，退休未分配345/346；不取消或重启任何EDA。R404/93555/node21已实际运行，405/406待真实前置；V400/93529/node23保持，401/402待真实前置。所有pending/unknown/旧运行及其他本Issue分配计入最大8节点；c96默认6×16独立动态补位，真实依赖或RAM预测×1.2+16GiB guard/liveRSS限制按实降并发。此为控制与实际提交证据，不是最终资格。
