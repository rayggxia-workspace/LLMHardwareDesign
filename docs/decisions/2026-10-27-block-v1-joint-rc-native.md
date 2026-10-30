# 实测节点耦合的分布式RC组装与原生读回

Refs #121；原生M1–M10预制与M11/M12后定制边界保持。当前是已有科学场数据到原生电气视图的接续，不是完整提取器或冻结资格。

100已实际通过branch/via两种真实物理绝缘双导体、双向实际终点节点的FV网格/远边界/offset/统计/逐节点耦合和保边际重连负例。102仅验证过单隔离网的节点ground和R。新增链条读取100封存输出，逐节点ground直接取原始场估计的ground列负值；节点对C来自双向真实起点/捕获位置，不按长度分摊或相乘边际。两方向先有独立科学互易门，才取算术均值形成唯一物理电容；原方向、标准误和对称化差异均保留。

组装器检查每个节点的ground+所有相邻网节点对C是否仍符合原实测self电荷。标准误按绝对和保守传递，不假定独立；不靠重写ground或缩放C强行守恒。DC图逐边正R且连通。SPEF中同一物理耦合在各自D_NET中对称出现，原生数据库必须只保留一个正确值的CCSeg，不能因为表示重复而双计。

新增`joint_rc_native.py`以原生OpenROAD/OpenDB独立导入，再逐节点/边/节点对读取。仅检查总C不足，故包含错单位、遗漏耦合、交换节点ground、交换R，以及保持每节点耦合边际/总量/物理正号的错误重连。组装纯控制使用100真实场输出，两正例、14结构破坏例已通过；实际原生import在本说明提交时尚未执行。

参考接口：[OpenRCX bench_read_spef](https://openroad.readthedocs.io/en/latest/main/src/rcx/README.html)、[dbBlock.getCCSegs](https://openroad.readthedocs.io/en/latest/doxygen_output/html/classodb_1_1dbBlock.html)、[dbCCSeg端点及fF电容](https://openroad.readthedocs.io/en/latest/doxygen_output/html/classodb_1_1dbCCSeg.html)。文档不是安装版能力证明，必须通过实际执行。

读回使用极小无源LEF锚绑定每个电气节点的ITerm身份；其ODB没有将场景导体重建成真实布线，不将这些锚当作计算资源或父层实体。DC采用明确小例假设：0.03ohm/square、0.8um线宽；via场例的0.8um方柱取0.5ohm，它不同于生产overlay的0.6um via10，不能据此签发生产via10/11电阻资格。

即使原生读回通过，仍缺真实多网布线几何与图对应、任意网络局部科学验证、窗口所有权、原生/新增层寄生拼接、完整STA/宏/父层与产品资格。各缺项独立保留，不以该链条替代。


## 2026-10-27 19:49 CST 实际终态

180/92385已完成，源码f5cc2a89cde2aa67617e179b45069b5581962ce9，archive2952b09630f21b6283eac82065fc5a80fc7a8c79aa1191ee7006bede99bec87c，199成员/1331200字节。两fixture各六种SPEF实际同时原生读回：正例逐节点ground、逐R边、逐耦合节点对严格相符；错单位、漏耦合、交换ground、交换电阻、保留每节点边际的耦合重连均拒绝。最后一项的ground/R及每节点耦合和仍相符，证明接收器不只核对总量或边际。13节点、18耦合对、9电阻共计；这两份锚点ODB只绑定电气ID，没有routed几何与原生/新增层拼接资格。三份实际终态索引在work/YUZE-LU/121/results/run180-*。

完整allocation57秒，TotalCPU6.379秒，Slurm组MaxRSS11092K；500ms进程树RSS采样branch168992768 bytes、via61820928 bytes，而via进程VmHWM169091072 bytes，表明短峰可能漏采。不能将Slurm采样或分组峰值当作单项精确峰值，亦不称6×16重型EDA加速。当前两个真实科学fixture均已就绪，16CPU额度/项，六个单线程原生变体按就绪立即并行；没有以RAM削减并发。没有更多同合同科学fixture时结束释放节点，不新增无研究目的变体。
