# Issue74独立数学及有限服务接收合同

主任务由Liangruizhi在本人服务器执行；本机仅写独立接收工具和运行小型合成边界测试。接收器不导入producer。当前文件是接收条件，不表示真实实验已经执行或通过。

## A：Granite完整整数MoE消费者

最小任务为layer0/13、calibration/evaluation各72token、R8/R16共8条件。每个条件必须从同一真实norm前residual开始，完整H1536 norm→全部40router logits→实际top8→Q15 gate→实际选中的全部8专家gate/up/整数SiLU/down→共同Q12宽merge→固定0.22系数与真实residual→完整nextnorm。cal/eval源、权重revision和源码SHA独立绑定，不将旧native32失败升级为PASS。

- 捕获必须提供norm前residual、当前与nextnorm gamma、router和全部40专家的真实权重、实际层的残差系数；原Issue70 FP32输入不能无桥接到Issue72 model64路由。router与expert必须消费同一当前整数norm输出。
- compiler可用cal/static数据生成固定W8、Q31/exp、LUT和常数。运行时只能用当前整数输入/状态选择activation scale，不读FP参考、未来token或eval误差；SiLU、中间乘法和A8编码不得保留旧FP64桥。
- 所有完整K dot、RQ前后、LUT索引/值、activation exponent、实际ID/Q15 gate、专家输出、对齐/每个merge prefix、最终Q12和完整norm须有可复算整数码。观察数组不得作为隐含硬件库存。
- 逐输出/逐专家单位必须唯一。先对齐完整和后RQ与逐专家先RQ是不同数值函数，必须提前冻结；RNE、饱和、全码域溢出guard与失败发布语义明确。R16不能只验证少数witness却称全部真实S8 lowering。
- 独立接收全量重算完整被选专家；用Python int/Fraction和位算法核验宽乘、除法、开方及边界，不用producer的函数自证。LUT/compiler编码与运行时整数链分开核验。至少三个实际artifact修改并重写SHA的负例，需到数学层拒绝。
- 原生/条件高精度误差只在整数链完成后离线诊断，不以局部误差代替全模型质量门槛。

## B：Falcon grouped A8同精度同资源部署

g0/K512/K256各自绑定既有PASS数值manifest、数学receipt及固定gatednorm/W8/Q31/exponent/轨迹。每个数值函数分别配对M/V归属和两种标签，共12条件；不同G之间是误差/成本取舍，不能称placement收益。

- group0必须逐码复现旧whole-row；G8/G16每个完整Kgroup INT32 partial用当前group最小RNE右移编码，再按d0=min(delta)对齐并形成完整K I64和，最后仅一次64×32→128 Q31/RNE。不得逐group先RQ改变函数。
- 给出真实Otile生命周期和依赖：A8/delta扫描、weight rowpack/transpose/K微流、partial、I64 prefix、I128 hi/lo、输出、静态scale和descriptor。不能在V16KiB免费物化G×O partial，不能漏S/backing spill、metadata或重复读取。
- 配对总库存、bank容量/1RW、128bit BUS、FIFO、M256有效B1 16PE、VR8、单SFU和ROM完全相同，只变合法部署/服务安排。每次packet header/16B pad与源/目的leading beat分别计；实际loop offset余数和容量/lifetime必须可证。
- 接收器核验event依赖、完整K/完整norm及最终发布顺序、每个资源区间、真实读写对象和字节范围、算术lowering与元数据计数；保留group0标签零差控制与各G配对的数值不变证明。
- 泛用S32×C32经N256求和需要72个signed bits；实际I64路径依赖guard，不能声称通用I64保证。VR factor同时缩放copy/reorder/guard/control，不能称孤立宽乘消融。
- 服务为未RTL校准的条件串行策略；不能由旧whole-row时间推导grouped部署收益，也不能报告PPA、最优调度或整模型端到端性能。

## 测试命令与状态

```text
python -B -m unittest discover -s project/experiments/moe_grouped -p test_audit_io74.py -v
```

实际服务器数据接收：未执行，等待producer冻结schema与capture。仓库/Issue/PR/看板由root核验与同步；本子任务未进行远端读写。
