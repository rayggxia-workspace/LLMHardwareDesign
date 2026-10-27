# 实际最终叶网表与真实 glue 的完整四 profile 组合

对应[Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)与草稿[PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)。这是最终功能验证的一部分，不能替代独立物理接收、完整恢复/终止epoch、宏边界或共同底座。

`native_composed.py`读取128的实际C8/S16K与133的实际T6K候选，A/C分别组合。必须有成功生产者回执、原最终ODB/Verilog/SDC/SPEF精确SHA、严格零未匹配LEC与所有生产RTL版本一致；从实际ODB导出所有信号单元，保留保护单元、真实存储和全部物理修复。父层使用137实际映射的shared121 glue（32单元、23.674um²），不再以wrapper RTL或免费连线替代它。编译输入只有两份实际最终叶信号视图、真实映射glue及同一Liberty导出的单元行为，禁止重新综合叶块或替换行为RAM。

数学接收继续使用原`receive121.py`的完整混合M/V、Attention、Falcon与GDN整数oracle、全state/输出/中间阶段、owner/registry、真实T6K逐beat消费和提前ACK检查，pilot固定0。新增物理来源分支只扩展源绑定与初始化参数，旧分支的精确命令检查和全部数学条件保留。完整恢复driver中的输出epoch Q注入明确是RTL专用，未将它直接当作物理门级测试；此门槛另行补齐，不能宣称由本混合组合覆盖。

每个A/C候选构建一次模型，然后三个初态（全1、随机seed121/122）乘两种背压模式，共六个完整运行，每个模型最多4线程。必须先解析Verilator运行参数再构造DUT；原mixed driver的全局静态DUT会过早构造，故只精确转换构造顺序及argc，所有运算/协议代码不变。依据[官方运行参数](https://verilator.org/guide/latest/exe_sim.html)与[上下文说明](https://verilator.org/guide/latest/connecting.html)，先以安装版工具/实际Liberty的128个DFF实测全1和两种不同随机初态；该探针不证明完整组合。138入口`native-composed-init-control`尚未实际运行。

正式组合通过`native-composed-group`在同一48CPU allocation组织A/C两个24CPU子任务；每子任务最多六个4线程模型。组以每子任务128GiB、子任务内部每模型16GiB并加20%余量作调度估计，依据实际MemAvailable降并发，绝不把估计称为实测峰值；保留独立子回执，一路失败其他继续。完整组合依赖128两路、133整组、137 glue与138初始化控制成功，尚未部署或运行。所有源码/命令/视图/驱动/库和科学输入由独立接收再次绑定。

138/92221实际严格失败13秒：全1为四个FFFFFFFF，但seed121/122分别成为全0/全1，未通过随机多样性门槛。只读检查生成C++发现128个同clock/同D的探针DFF被工具合并为一个状态，故这不是128个独立初态的实测证据。新140控制对128个DFF给出不同真实D输入位，再在测试时全置0，保留原随机多样性门槛；未改Liberty或预期数据。138失败和139旧依赖部署原样保留，139无job并停用，141组合将依赖140成功。当前140尚未部署/运行。

133/92206两候选实际route/final均成功，整组32:34、TotalCPU7:56:02、MaxRSS41902304K；135四路物理/最终功能资格已由统一dispatcher提交92222，尚未通过。两个普通生产者成功不能替代完整DRC/STA接收。

下一步是实际执行140初始化控制、等待完整候选后执行141组合，再将glue纳入父层物理实现/成本/冻结，补齐恢复与epoch物理或严格状态对应验证、宏Lib/LEF边界、一般多网分布RC及两产品仅新增层互联。保持完整批准计划，不以本项通过收缩验收范围。
