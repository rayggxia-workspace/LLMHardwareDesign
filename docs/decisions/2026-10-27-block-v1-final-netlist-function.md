# 最终物理T6K网表功能接收

Refs #121。最终物理库需要行为和reset/初态证据；原生LEC只证明正向完整的输入/输出与状态边界对应，不能单独代替该义务。

`native_final_function.py`将cap40封存源093的实际`6_final.v`直接交给Verilator，先用既有严格原生LEC接收器核对它与正式LEC网表同一字节、完整状态/数据/时钟边界和077源输入。Liberty单元行为单独用Yosys导出；最终网表不重综合、不替换真实存储、不改物理结果。

复用独立队列scoreboard的242事务、全容量/非法index、commit/revoke、背压、旧引用/最后一拍与协调reset；同一binary执行全1初态以及随机种子121/122。三个结果必须完整、非零检查并完全一致。配置`--x-initial unique --x-assign unique`及`+verilator+rand+reset+1/2`、`+verilator+seed+...`的语义参见[官方编译参数](https://verilator.org/guide/latest/exe_verilator.html)和[运行参数](https://verilator.org/guide/latest/exe_sim.html)。官方在线文档并非安装版执行证明；实际5.042工具仍须运行。

16CPU allocation内构建使用16线程，运行阶段三实例各最多4线程；不同时编译和模拟。输出绑定源/回执/网表/Liberty/单元模型/driver/binary及日志SHA，检查前后源网表哈希不变。功能依赖该候选源运行完成，可与独立DRC/PG/电气并行；合格硬宏仍须所有门槛同时通过。

当前仅代码和解析器合成正例/六负例（缺失、重复、失败、缩减事务、零检查、错误计数类型）通过，实际最终网表尚未编译运行。它不能证明四态、延迟时序、全部C8最终功能、Lib/LEF边界或十二层互联回装。


08:25更新：101已实际部署并启动T6KC作业92144，node20/16CPU，实际映射网表构建完成，三初态并行模拟中，无最终回执。源A/92135完成，但报告hold count=4，功能与时序资格继续分开记录。
