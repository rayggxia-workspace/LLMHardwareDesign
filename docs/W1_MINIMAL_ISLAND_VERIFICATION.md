# W1 fixed-DOT8 independent testbench

输入研究提交：`bfe62ad179af72aef591622aa5c7a000f5d8b681`；原生叶源：`707878621b2add4ed218b8c43df2e95c9a56e2ba`。本目录仅交付测试台，正式集成与实际ModelSim执行由根任务统一完成。

`block_w1_mst_tb.sv`实例化公共接口`block_w1_mst_top`。五组输入和字节顺序来自冻结的`work/Melodydt/151/w0-evidence-gates.json`中`W1_minimal_contract`。TB自有整数A/B数组独立执行八项signed-S8点积，逐结果与五组literal预期交叉核对；DUT的RAM、寄存器或内部运算不参与期望生成。输出按低64为偶数列、高64为奇数列拼接。

28个`CASE_PASS W1_*`标签覆盖：五向量（literal、zero、最大正、最小负、各列不同）、脏RAM和输入非零padding实际清零、八次入口接受及八次真实S ACK之后方可start、early pulse不排队、held start在ready后仅接受一次、公开入口/输出/DONE及native S ACK背压、不同帧与分阶段事务计数；部分输入、已native接受但ACK未消费、完整未RUN、RUN、已消费输出前缀和已有DONE的abort/reset与新帧恢复。另以一次真实M EXEC握手上的非法保留位验证原生错误传播及恢复。

正常帧分别检查：入口S写8/ACK8；RUN结果S写4/ACK4和回读4/ACK4；全帧普通S请求16/应答16；M命令7/应答7；loader一次完成及A/B各一拍；T BEGIN一次、四次顺序写、COMMIT一次、四次真实输出take及独立RELEASE一次。`input_stored`、loader done、T last及JOB DONE互不等同。中止/reset用例允许已接受请求未消费的应答被协调复位丢弃，不能用全程累计请求/ACK差额否定正常帧局部守恒。

层级只用于观察真实事务、RAM预脏和明确的有限故障注入：`u_s.storage.bank0..3[112]`为S448..451；`permit_s_req`阻止helper接单，`permit_s_rsp`阻止真实native S ACK消费；`permit_m_rsp`用于RUN reset位置；`m_cmd_data=64'h988c`仅在一次EXEC握手注入错误。所有许可在RTL固定为1，不新增产品运行时配置。预脏不宣称RAM reset会清payload。

成功判据是28个唯一CASE标签和最终`PASS_W1_MST`，没有`FAIL_W1`/`$fatal`且实际仿真进程退出码为0；只有源码存在或管理结构检查通过不能作为RTL通过证据。实际工具/命令/日志/源码SHA由统一runner记录。

范围限制：固定B1/row1/tile1/K8/N8、S8×S8、factor1/left0、op3原始S64输出；未测S16、可变尺寸/地址/尺度、op5量化、M溢出、全opcode/全协议非法组合、随机穷举、跨岛/MEM/NUM/N/E/G/R、物理实现及完整模型。公共DONE消费边沿检查`in_ready=0`；没有把测试台变成多帧并发源。前缀已被外部take后，abort/reset只验证不新增/不重放前缀，不宣称外部回滚。

本目录实际检查：UTF8 LF；`python -B -X utf8 scripts/check_project.py`在冻结integrated根实际PASS（仅项目管理结构）。根任务实际执行ModelSim SE-64 2020.4；本子任务随后只读核验`runs/w1-r03/run-receipt.json`及日志：compile exit0、simulation exit0、28个唯一CASE、4422周期、`PASS_W1_MST`，TB源SHA为`178318886fe1b91d8fed13c6b6870663a77dc057b6ace8b1b531c0fa9799daac`，与本目录相同。该版本包含只受hard reset屏蔽的public DONE握手计数，abort+ready仍须恰好一次；每次公开输入接受后检查busy，完整未RUN继续busy。

运行回执SHA：`614b5513966449a5129367eb07cb742aaabc9f37563bc9e87762dbaf6cd00152`；compile.log：`552daa76b5cb2ce834e509dc8570d517ead21e11b59f3f9043fec7e455b2f75e`；simulation日志：`e634abc7662737167635fac53cd6bc1fc61b90c022a584fe5e0b9dcb4be39d4a`。旧r01编译失败和r02旧计数门PASS由根保留，r03是本TB最终版本依据。

全程累计为inputAccept240/ingressReq239/ingressACK237、resultReq97/resultACK96、readReq96/readACK96、Mcmd176/Mrsp175、Ttake92。差额具有明确用例来源：capture后尚未native请求即abort为1；已native接受的input pending ACK分别abort/reset共2；RUN结果pending ACK abort为1；M响应pending hard reset为1。它们均不构成全程守恒声明；正常帧的分阶段16/16检查已分别执行。
