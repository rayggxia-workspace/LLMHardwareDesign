# V401 对旧 V400 最终网表的三初态功能证据

Refs #121 / PR #122。401/93578/node23 对 V400 实际最终网表的 all-ones、random121、random122 三初态测试均 PASSED，各 566999 检查、414906 拍。零延迟功能测试不能替代 STA、DRC 或严格 LEC。

源 62e3e5776c891a83f8665d0b86a99fb6aa36f188，归档 d3ee6032b6124a089b825cacedeb5ce863beaf038cafa8c12a7ccbcf389a17e3。11 份原始文件见 index.json；核对 308 个源 Git blobs、回执输入和收录输出的 SHA/字节。source-binding 保存另 2 份原始最终来源文件，验证实际 V400 最终 V/ODB 与测试输入 SHA 一致。大网表留服务器，实际最终信号视图的摘要、结构和输入绑定见功能报告。

V400 因最终负 setup/hold 未通过 300MHz，并已发现独立原生全芯片 DRC 违规，不能接收。本次功能资格仅属于旧 V400，不转移给新 V410。捕获时完整 GDS DRC 与严格 LEC 仍运行；其最终结果另存。
