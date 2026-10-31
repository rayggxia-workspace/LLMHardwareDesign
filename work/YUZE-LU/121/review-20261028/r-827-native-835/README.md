# R 827 原生六阶段布局布线证据（835）

Refs #121 / PR #122。源 commit `747d700e8136a93788eb6eaa28c83c11302c9c71`。

作业 `94320` 在 node15 自然 COMPLETED/0:0，耗时 6:06:16；综合、floorplan、placement、CTS、route、finish 六阶段全部重新执行。外框 2330 × 2330 µm；原生最终报告 setup/hold 最差裕量 +0.0611884/+0.0135687 ns，TNS、setup/hold、电容/slew 违规计数均为 0。流程内最终网表 LEC 为 UNSAT/IDENTICAL，详细路由末次违规数 0。

采集脚本见 [collector.py](collector.py)，完整来源和实际服务器文件 SHA/大小见 [index.json](index.json)，本地原始文件重新核验及原生指标摘要见 [native-summary.json](native-summary.json)。122 份原始文件已逐字节 SHA/大小核对；34 个大文件留在授权服务器并记录实际 SHA/大小；148 项 receipt 输出与 365 个归档 Git 源文件均已核对。V/SDC/DEF/ODB/SPEF 五种原生最终文件已索引，尚不包含独立导出的最终 GDS。

**本记录不授予 R 最终宏资格。** 独立同源最终验收 828（RCX/STA/覆盖、电源与信号连通、完整未改 GDS DRC、三初态最终功能、严格 LEC、六文件与完整实际几何）及接口/有限 RC 829 仍待完成。原 404 自然拥塞失败保留，不能继承旧 405/406 资格。默认流程自动生成的 power/IR 报告仅保留原始工程观测，不能据此宣称工作负载功耗或供电验收。
